"""
LLM response generation service for the RAG system.
"""

import logging
import re
import json
import os
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from rag.context_builder import ConstructedContext
from rag.question_processor import ConversationContext
from database.models import ChatConversation
from monitoring.metrics import observe as metrics_observe, inc as metrics_inc

# 최상단 import 근처
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=False)  # .env 자동 로드

class ResponseQuality(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"


@dataclass
class GeneratedResponse:
    content: str
    quality_score: ResponseQuality
    confidence_score: float
    processing_time: float
    retrieved_doc_ids: List[str]
    conversation_context: Optional[str] = None


@dataclass
class ConversationMemory:
    user_id: str
    conversation_history: List[ChatConversation]
    current_context: Optional[str] = None
    last_topic: Optional[str] = None
    follow_up_count: int = 0


class ResponseGenerator:
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.0-flash"):
        self.logger = logging.getLogger(__name__)
        
        api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Missing API key: set GEMINI_API_KEY or GOOGLE_API_KEY, or pass api_key param")
        genai.configure(api_key=api_key)
        self.model_name = model_name
        
        self.model = genai.GenerativeModel(
            model_name=model_name,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
        )
        
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.8,
            top_k=40,
            max_output_tokens=2048,
            candidate_count=1
        )
        
        self.conversation_memories: Dict[str, ConversationMemory] = {}
        
        self.validation_patterns = {
            "korean_content": re.compile(r'[가-힣]'),
            "inappropriate_content": re.compile(r'(부적절|위험|해로운|불법)', re.IGNORECASE),
            "incomplete_response": re.compile(r'(죄송|미안|모르겠|알 수 없)', re.IGNORECASE),
            "statistical_info": re.compile(r'(\d+%|\d+위|\d+점|백분위|순위)', re.IGNORECASE)
        }
    
    # =======================
    # Conversation memory API
    # =======================
    def get_conversation_memory(self, user_id: str) -> Optional[ConversationMemory]:
        return self.conversation_memories.get(user_id)
    
    def clear_conversation_memory(self, user_id: str) -> None:
        if user_id in self.conversation_memories:
            del self.conversation_memories[user_id]
    
    async def generate_response(self, constructed_context, user_id, conversation_context=None):
        start_time = time.time()
        
        try:
            memory = await self._update_conversation_memory(user_id, constructed_context)
            enhanced_prompt = await self._enhance_prompt_with_memory(
                constructed_context.formatted_prompt, memory
            )
            
            self.logger.info(f"Generating response for user {user_id} using model {self.model_name}")
            
            response = await self._call_gemini_api(enhanced_prompt)
            processed_response = await self._post_process_response(response, constructed_context, memory)
            quality_score = self._assess_response_quality(processed_response, constructed_context)
            confidence_score = self._calculate_confidence_score(processed_response, constructed_context, quality_score)
            
            processing_time = time.time() - start_time
            retrieved_doc_ids = [str(doc.document.doc_id) for doc in constructed_context.retrieved_documents]
            
            generated_response = GeneratedResponse(
                content=processed_response,
                quality_score=quality_score,
                confidence_score=confidence_score,
                processing_time=processing_time,
                retrieved_doc_ids=retrieved_doc_ids,
                conversation_context=memory.current_context
            )
            
            await self._store_conversation_turn(user_id, constructed_context, generated_response)
            
            self.logger.info(
                f"Generated response for user {user_id}: "
                f"quality={quality_score.value}, confidence={confidence_score:.2f}, "
                f"time={processing_time:.2f}s"
            )
            
            await metrics_observe("rag_response_seconds", processing_time)
            return generated_response
            
        except Exception as e:
            self.logger.error(f"Error generating response for user {user_id}: {e}")
            
            fallback_response = await self._generate_fallback_response(constructed_context)
            processing_time = time.time() - start_time
            
            await metrics_inc("rag_response_errors_total")
            await metrics_observe("rag_response_seconds", processing_time)
            return GeneratedResponse(
                content=fallback_response,
                quality_score=ResponseQuality.POOR,
                confidence_score=0.1,
                processing_time=processing_time,
                retrieved_doc_ids=[],
                conversation_context=None
            )
    
    async def _call_gemini_api(self, prompt: str) -> str:
        max_attempts = 3
        base_delay = 0.5
        for attempt in range(max_attempts):
            try:
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt,
                    generation_config=self.generation_config
                )
                
                if response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    if candidate.content and candidate.content.parts:
                        return candidate.content.parts[0].text
                
                self.logger.warning("No valid response generated by Gemini API")
                return "죄송합니다. 현재 답변을 생성할 수 없습니다. 다시 시도해 주세요."
                
            except Exception as e:
                if attempt < max_attempts - 1:
                    delay = base_delay * (2 ** attempt) + 0.1 * attempt
                    self.logger.warning(
                        f"Gemini API call failed (attempt {attempt+1}/{max_attempts}): {e}. Retrying in {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                self.logger.error(f"Error calling Gemini API after retries: {e}")
                await metrics_inc("llm_api_errors_total")
                raise

    # =======================
    # Internal helpers
    # =======================
    async def _update_conversation_memory(self, user_id: str, constructed_context: ConstructedContext) -> ConversationMemory:
        memory = self.conversation_memories.get(user_id)
        if not memory:
            memory = ConversationMemory(user_id=user_id, conversation_history=[], current_context=None, last_topic=None, follow_up_count=0)
            self.conversation_memories[user_id] = memory
        # Update basic context
        memory.current_context = self._extract_topic_from_question(constructed_context.user_question)
        memory.last_topic = memory.current_context
        memory.follow_up_count = (memory.follow_up_count or 0) + 1
        return memory

    async def _enhance_prompt_with_memory(self, prompt: str, memory: ConversationMemory) -> str:
        if not memory or not memory.conversation_history:
            return prompt
        last_items = memory.conversation_history[-3:]
        previous_context = "\n".join([
            f"Q: {c.question}\nA: {c.response}" for c in last_items
        ])
        enhanced = (
            f"이전 대화 맥락:\n{previous_context}\n\n"
            f"후속 질문 횟수: {memory.follow_up_count}\n\n{prompt}"
        )
        return enhanced

    async def _post_process_response(self, raw_response: str, constructed_context: ConstructedContext, memory: ConversationMemory) -> str:
        if not raw_response:
            return "죄송합니다. 현재 답변을 생성할 수 없습니다. 다시 시도해 주세요."
        text = raw_response
        # Remove simple markdown markers
        text = re.sub(r"[*_`#>]+", "", text)
        # Collapse excessive whitespace
        text = re.sub(r"\s+", " ", text).strip()
        # Korean formatting fixes
        text = self._fix_korean_formatting(text)
        # Optional enhancements
        text = await self._enhance_with_statistical_context(text, constructed_context)
        text = await self._enhance_with_learning_connections(text, constructed_context)
        return text

    def _validate_response_content(self, text: str) -> bool:
        if not text or len(text) < 5:
            return False
        if not self.validation_patterns["korean_content"].search(text):
            return False
        # Too many apologies/incompletes
        if len(self.validation_patterns["incomplete_response"].findall(text)) >= 3:
            return False
        return True

    def _assess_response_quality(self, processed_response: str, constructed_context: ConstructedContext) -> ResponseQuality:
        if not self._validate_response_content(processed_response):
            return ResponseQuality.POOR
        # Heuristic: longer + mentions stats => better
        score = 0
        if len(processed_response) > 100:
            score += 1
        if self.validation_patterns["statistical_info"].search(processed_response):
            score += 1
        return [ResponseQuality.ACCEPTABLE, ResponseQuality.GOOD, ResponseQuality.EXCELLENT][min(score, 2)]

    def _calculate_confidence_score(self, processed_response: str, constructed_context: ConstructedContext, quality: ResponseQuality) -> float:
        base = {
            ResponseQuality.POOR: 0.2,
            ResponseQuality.ACCEPTABLE: 0.5,
            ResponseQuality.GOOD: 0.75,
            ResponseQuality.EXCELLENT: 0.9,
        }[quality]
        # Slight boost if documents are present
        boost = 0.05 if constructed_context.retrieved_documents else -0.05
        return max(0.0, min(1.0, base + boost))

    async def _store_conversation_turn(self, user_id: str, constructed_context: ConstructedContext, generated_response: GeneratedResponse) -> None:
        memory = self.conversation_memories.get(user_id)
        if not memory:
            memory = ConversationMemory(user_id=user_id, conversation_history=[])
            self.conversation_memories[user_id] = memory
        # Use a lightweight object to store Q/A
        conversation_entry = type('Conv', (), {
            'question': constructed_context.user_question,
            'response': generated_response.content,
            'created_at': datetime.now()
        })()
        memory.conversation_history.append(conversation_entry)

    def _extract_topic_from_question(self, question: str) -> str:
        q = (question or "").lower()
        if any(k in q for k in ["성격", "personality"]):
            return "personality"
        if any(k in q for k in ["직업", "진로", "career"]):
            return "career"
        if any(k in q for k in ["사고", "능력", "thinking"]):
            return "thinking"
        if any(k in q for k in ["학습", "공부", "learning"]):
            return "learning"
        return "general"

    async def _enhance_with_statistical_context(self, response: str, constructed_context: ConstructedContext) -> str:
        # If context suggests stats are relevant, add a gentle note
        if constructed_context.prompt_template.name in ["STATISTICAL_INFO", "PERSONALITY_COMPARE", "GENERAL_COMPARE"]:
            return response + "\n\n참고: 점수, 백분위, 순위 등 통계 정보는 검사 결과 데이터에 기반합니다."
        return response

    async def _enhance_with_learning_connections(self, response: str, constructed_context: ConstructedContext) -> str:
        if constructed_context.prompt_template.name in ["LEARNING_STYLE_RECOMMEND", "PERSONALITY_EXPLAIN"]:
            return response + "\n\n학습 팁: 자신의 강점을 활용한 공부 전략을 적용해보세요."
        return response

    def _fix_korean_formatting(self, text: str) -> str:
        # Remove spaces before punctuation and normalize
        text = re.sub(r"\s+([\.,!?])", r"\1", text)
        text = re.sub(r"\s{2,}", " ", text)
        # Fix common patterns like " 점" -> "점"
        text = re.sub(r"\s+점", "점", text)
        text = text.replace(" 입니다", "입니다")
        text = text.replace(" .", ".")
        return text.strip()

    async def _generate_fallback_response(self, constructed_context: ConstructedContext) -> str:
        question = (constructed_context.user_question or "").lower()
        topic = self._extract_topic_from_question(question)
        if topic == "personality":
            return "현재 상세 데이터를 불러오는 데 문제가 있어요. 성격 분석의 핵심 포인트를 먼저 안내드릴게요: 강점, 보완점, 추천 활동을 중심으로 스스로의 패턴을 관찰해보세요."
        if topic == "career":
            return "지금은 실시간 데이터를 가져오지 못했어요. 진로 추천을 위해서는 강점과 흥미를 기준으로 2~3개의 직무를 후보로 두고, 필요한 역량과 학습 경로를 역으로 계획해보는 것을 권장합니다."
        return "죄송합니다. 답변을 생성하는데 문제가 있습니다. 잠시 후 다시 시도해 주세요."
    
    def get_model_info(self):
        return {
            "model_name": self.model_name,
            "generation_config": {
                "temperature": self.generation_config.temperature,
                "top_p": self.generation_config.top_p,
                "top_k": self.generation_config.top_k,
                "max_output_tokens": self.generation_config.max_output_tokens
            },
            "active_conversations": len(self.conversation_memories)
        }
