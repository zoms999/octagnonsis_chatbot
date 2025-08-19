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

from rag.context_builder import ConstructedContext, PromptTemplate
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
            # Pre-validate preference data availability for preference questions
            is_preference_question = (
                constructed_context.prompt_template in [
                    PromptTemplate.PREFERENCE_EXPLAIN, 
                    PromptTemplate.PREFERENCE_MISSING, 
                    PromptTemplate.PREFERENCE_PARTIAL
                ] or 
                any(keyword in constructed_context.user_question.lower() 
                    for keyword in ["선호", "preference", "좋아", "관심", "취향", "이미지"])
            )
            
            if is_preference_question:
                data_availability = self._validate_preference_data_availability(constructed_context)
                
                # If no preference data and template is not already PREFERENCE_MISSING,
                # use a focused fallback response
                if (data_availability["completion_level"] == "missing" and 
                    constructed_context.prompt_template != PromptTemplate.PREFERENCE_MISSING):
                    
                    fallback_response = self._generate_preference_focused_fallback(constructed_context)
                    processing_time = time.time() - start_time
                    
                    return GeneratedResponse(
                        content=fallback_response,
                        quality_score=ResponseQuality.ACCEPTABLE,
                        confidence_score=0.6,
                        processing_time=processing_time,
                        retrieved_doc_ids=[str(doc.document.doc_id) for doc in constructed_context.retrieved_documents],
                        conversation_context=None
                    )
            
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

    def _validate_preference_data_availability(self, constructed_context: ConstructedContext) -> dict:
        """
        Analyze preference data availability and completeness.
        
        Args:
            constructed_context: Context used for generation
            
        Returns:
            Dictionary with availability analysis
        """
        preference_docs = [
            doc for doc in constructed_context.retrieved_documents 
            if doc.document.doc_type == "PREFERENCE_ANALYSIS"
        ]
        
        if not preference_docs:
            return {
                "has_preference_docs": False,
                "completion_level": "missing",
                "available_components": [],
                "missing_components": ["stats", "preferences", "jobs"],
                "data_quality": "none"
            }
        
        # Analyze document completeness
        available_components = []
        missing_components = []
        completion_levels = []
        
        for doc in preference_docs:
            try:
                content = json.loads(doc.document.content) if isinstance(doc.document.content, str) else doc.document.content
                metadata = doc.document.metadata or {}
                
                # Check metadata completion level
                completion_level = metadata.get("completion_level", "unknown")
                completion_levels.append(completion_level)
                
                # Check content components
                if isinstance(content, dict):
                    if content.get("stats") and content["stats"] is not None:
                        available_components.append("stats")
                    else:
                        missing_components.append("stats")
                    
                    if content.get("preferences") and len(content.get("preferences", [])) > 0:
                        available_components.append("preferences")
                    else:
                        missing_components.append("preferences")
                    
                    if content.get("jobs") and len(content.get("jobs", [])) > 0:
                        available_components.append("jobs")
                    else:
                        missing_components.append("jobs")
                
                # Check for fallback indicators
                content_str = str(content).lower()
                if any(indicator in content_str for indicator in ["데이터 준비 중", "찾을 수 없습니다", "준비되지 않았습니다"]):
                    missing_components.extend(["stats", "preferences", "jobs"])
                    
            except Exception as e:
                self.logger.warning(f"Error analyzing preference document: {e}")
                missing_components.extend(["stats", "preferences", "jobs"])
        
        # Determine overall completion level
        if "complete" in completion_levels and not missing_components:
            overall_completion = "complete"
            data_quality = "high"
        elif available_components:
            overall_completion = "partial"
            data_quality = "medium" if len(available_components) >= 2 else "low"
        else:
            overall_completion = "missing"
            data_quality = "none"
        
        return {
            "has_preference_docs": True,
            "completion_level": overall_completion,
            "available_components": list(set(available_components)),
            "missing_components": list(set(missing_components)),
            "data_quality": data_quality
        }

    def _detect_preference_hallucination_patterns(self, response: str, data_availability: dict) -> list:
        """
        Detect patterns that might indicate hallucination about preference data.
        
        Args:
            response: Generated response text
            data_availability: Data availability analysis
            
        Returns:
            List of detected hallucination patterns
        """
        detected_patterns = []
        
        # Patterns that indicate specific data claims
        specific_data_patterns = [
            (r'선호도.*?(\d+)위', "specific_ranking"),
            (r'이미지.*?선호.*?(\d+)%', "specific_percentage"),
            (r'선호.*?점수.*?(\d+)점', "specific_score"),
            (r'응답률.*?(\d+)%', "response_rate"),
            (r'총.*?(\d+)개.*?이미지', "image_count"),
            (r'가장.*?선호.*?(색상|형태|스타일|패턴)', "specific_preference_type"),
            (r'(\d+)번째.*?선호', "numbered_preference"),
            (r'선호도.*?상위.*?(\d+)%', "percentile_claim")
        ]
        
        # Definitive claim patterns
        definitive_patterns = [
            (r'당신의.*?선호도는.*?(확실히|명확히)', "definitive_claim"),
            (r'가장.*?선호하는.*?것은', "absolute_preference"),
            (r'선호.*?순위는.*?다음과 같습니다', "ranking_claim"),
            (r'확실히.*?선호', "certainty_claim"),
            (r'분명히.*?(좋아|선호)', "certainty_preference")
        ]
        
        # Check for specific data patterns when data is missing or incomplete
        if data_availability["completion_level"] in ["missing", "partial"]:
            for pattern, pattern_type in specific_data_patterns:
                if re.search(pattern, response):
                    detected_patterns.append({
                        "type": pattern_type,
                        "pattern": pattern,
                        "severity": "high" if data_availability["completion_level"] == "missing" else "medium"
                    })
        
        # Check for definitive claims when data quality is low
        if data_availability["data_quality"] in ["none", "low"]:
            for pattern, pattern_type in definitive_patterns:
                if re.search(pattern, response):
                    detected_patterns.append({
                        "type": pattern_type,
                        "pattern": pattern,
                        "severity": "high"
                    })
        
        return detected_patterns

    def _generate_data_availability_disclaimer(self, data_availability: dict, detected_patterns: list) -> str:
        """
        Generate appropriate disclaimer based on data availability and detected patterns.
        
        Args:
            data_availability: Data availability analysis
            detected_patterns: Detected hallucination patterns
            
        Returns:
            Disclaimer text or empty string
        """
        if not detected_patterns:
            return ""
        
        high_severity_patterns = [p for p in detected_patterns if p["severity"] == "high"]
        
        if data_availability["completion_level"] == "missing":
            return ("\n\n⚠️ 중요: 현재 선호도 분석 데이터가 준비되지 않아 구체적인 수치나 순위는 "
                   "제공할 수 없습니다. 위 내용은 일반적인 가이드라인이며, 정확한 분석을 위해서는 "
                   "다른 검사 결과(성격 분석, 사고능력 등)를 참고하시기 바랍니다.")
        
        elif data_availability["completion_level"] == "partial":
            available = ", ".join(data_availability["available_components"])
            missing = ", ".join(data_availability["missing_components"])
            
            disclaimer = f"\n\n💡 데이터 상태 안내: 현재 {available} 데이터는 준비되어 있으나, {missing} 데이터는 아직 준비 중입니다."
            
            if high_severity_patterns:
                disclaimer += " 완전한 분석을 위해서는 추가 검사나 다른 분석 결과를 함께 참고하시기 바랍니다."
            
            return disclaimer
        
        elif data_availability["data_quality"] == "low" and high_severity_patterns:
            return ("\n\n💡 참고: 현재 제한적인 선호도 데이터를 바탕으로 한 분석입니다. "
                   "보다 정확한 인사이트를 위해 성격 분석이나 역량 분석 결과도 함께 확인해보세요.")
        
        return ""

    def _validate_preference_response(self, response: str, constructed_context: ConstructedContext) -> str:
        """
        Validate and enhance preference-related responses to prevent hallucination.
        
        Args:
            response: Generated response text
            constructed_context: Context used for generation
            
        Returns:
            Validated and potentially modified response
        """
        # Check if this is a preference-related question
        is_preference_question = (
            constructed_context.prompt_template in [
                PromptTemplate.PREFERENCE_EXPLAIN, 
                PromptTemplate.PREFERENCE_MISSING, 
                PromptTemplate.PREFERENCE_PARTIAL
            ] or 
            any(keyword in constructed_context.user_question.lower() 
                for keyword in ["선호", "preference", "좋아", "관심", "취향", "이미지"])
        )
        
        if not is_preference_question:
            return response
        
        # Analyze data availability
        data_availability = self._validate_preference_data_availability(constructed_context)
        
        # Detect potential hallucination patterns
        detected_patterns = self._detect_preference_hallucination_patterns(response, data_availability)
        
        # Generate appropriate disclaimer
        disclaimer = self._generate_data_availability_disclaimer(data_availability, detected_patterns)
        
        # Add disclaimer if needed
        if disclaimer:
            response += disclaimer
        
        # Log validation results for monitoring
        if detected_patterns:
            self.logger.warning(
                f"Preference response validation detected potential hallucination: "
                f"patterns={len(detected_patterns)}, data_quality={data_availability['data_quality']}"
            )
        
        return response

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
        # Validate preference responses to prevent hallucination
        text = self._validate_preference_response(text, constructed_context)
        
        # Optional enhancements
        text = await self._enhance_with_statistical_context(text, constructed_context)
        text = await self._enhance_with_learning_connections(text, constructed_context)
        text = await self._enhance_with_preference_alternatives(text, constructed_context)
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
        if any(k in q for k in ["선호", "preference", "좋아", "관심", "취향", "이미지"]):
            return "preference"
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

    def _get_preference_acknowledgment_template(self, data_availability: dict, user_question: str) -> str:
        """
        Get appropriate acknowledgment template for preference data availability.
        
        Args:
            data_availability: Data availability analysis
            user_question: Original user question
            
        Returns:
            Acknowledgment template text
        """
        completion_level = data_availability["completion_level"]
        available_components = data_availability["available_components"]
        
        if completion_level == "missing":
            return (
                "현재 선호도 분석 데이터가 준비되지 않았습니다. "
                "하지만 다른 검사 결과를 통해 유사한 인사이트를 얻을 수 있어요! "
            )
        
        elif completion_level == "partial":
            if available_components:
                available_str = ", ".join({
                    "stats": "통계 정보",
                    "preferences": "선호도 순위",
                    "jobs": "직업 추천"
                }.get(comp, comp) for comp in available_components)
                
                return (
                    f"현재 {available_str}는 준비되어 있지만, "
                    "일부 선호도 데이터가 아직 처리 중입니다. "
                    "준비된 데이터를 바탕으로 분석해드릴게요. "
                )
            else:
                return (
                    "선호도 분석 데이터가 부분적으로만 준비되어 있습니다. "
                    "현재 가능한 범위에서 분석해드리겠습니다. "
                )
        
        return ""

    def _get_alternative_analysis_suggestions(self, user_question: str) -> str:
        """
        Generate alternative analysis suggestions when preference data is unavailable.
        
        Args:
            user_question: Original user question
            
        Returns:
            Alternative suggestions text
        """
        question_lower = user_question.lower()
        
        # Determine what the user is looking for
        if any(keyword in question_lower for keyword in ["직업", "진로", "career", "job"]):
            focus = "career"
        elif any(keyword in question_lower for keyword in ["활동", "취미", "관심", "activity"]):
            focus = "activity"
        elif any(keyword in question_lower for keyword in ["학습", "공부", "study"]):
            focus = "learning"
        else:
            focus = "general"
        
        base_suggestions = [
            "\n\n🔍 대안 분석 방법:",
            "• 성격 분석 결과를 통해 선호하는 활동 유형을 파악해보세요",
            "• 사고능력 분석에서 강점 영역과 관련된 관심사를 찾아보세요",
            "• 역량 분석 결과로 자연스럽게 끌리는 분야를 확인해보세요"
        ]
        
        # Add focus-specific suggestions
        if focus == "career":
            base_suggestions.extend([
                "• '내게 맞는 직업은 무엇인가요?' 질문으로 진로 추천을 받아보세요",
                "• '내 성격에 맞는 업무 환경은?' 같은 질문도 도움이 됩니다"
            ])
        elif focus == "activity":
            base_suggestions.extend([
                "• '내 강점을 활용할 수 있는 활동은?' 질문을 해보세요",
                "• '어떤 취미가 나에게 맞을까요?' 같은 질문도 좋습니다"
            ])
        elif focus == "learning":
            base_suggestions.extend([
                "• '내게 맞는 학습 방법은?' 질문으로 맞춤 학습법을 알아보세요",
                "• '어떤 공부 방식이 효과적일까요?' 같은 질문도 유용합니다"
            ])
        else:
            base_suggestions.extend([
                "• '내 강점은 무엇인가요?' 또는 '어떤 활동이 나에게 맞나요?' 같은 질문을 해보세요",
                "• '내 성격 특성을 알려주세요' 질문으로 더 자세한 분석을 받아보세요"
            ])
        
        return "\n".join(base_suggestions)

    async def _enhance_with_preference_alternatives(self, response: str, constructed_context: ConstructedContext) -> str:
        """
        Enhance preference responses with alternatives when data is missing or partial.
        
        Args:
            response: Current response text
            constructed_context: Context used for generation
            
        Returns:
            Enhanced response with alternatives
        """
        # Only enhance if this is a preference-related template
        if constructed_context.prompt_template not in [
            PromptTemplate.PREFERENCE_MISSING, 
            PromptTemplate.PREFERENCE_PARTIAL
        ]:
            return response
        
        # Analyze data availability
        data_availability = self._validate_preference_data_availability(constructed_context)
        
        # Add acknowledgment template
        acknowledgment = self._get_preference_acknowledgment_template(
            data_availability, constructed_context.user_question
        )
        
        if acknowledgment and acknowledgment not in response:
            # Insert acknowledgment at the beginning if not already present
            response = acknowledgment + response
        
        # Add alternative suggestions for missing data
        if data_availability["completion_level"] == "missing":
            alternatives = self._get_alternative_analysis_suggestions(constructed_context.user_question)
            response += alternatives
        
        # Add enhancement note for partial data
        elif data_availability["completion_level"] == "partial":
            enhancement = (
                "\n\n💡 완전한 선호도 분석을 위한 팁:\n"
                "• 다른 검사 결과(성격, 사고능력, 역량)와 함께 종합적으로 해석해보세요\n"
                "• 시간이 지나면 더 완전한 선호도 데이터가 준비될 수 있습니다\n"
                "• 현재 결과만으로도 의미 있는 인사이트를 얻을 수 있어요"
            )
            response += enhancement
        
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

    def _generate_preference_focused_fallback(self, constructed_context: ConstructedContext) -> str:
        """
        Generate fallback response for preference questions that focuses on available data.
        
        Args:
            constructed_context: Context for the failed generation
            
        Returns:
            Preference-focused fallback response
        """
        # Check what other document types are available
        available_doc_types = set()
        for doc in constructed_context.retrieved_documents:
            if doc.document.doc_type != "PREFERENCE_ANALYSIS":
                available_doc_types.add(doc.document.doc_type)
        
        base_response = "현재 선호도 분석 데이터에 접근할 수 없지만, "
        
        if "PERSONALITY_PROFILE" in available_doc_types:
            base_response += (
                "성격 분석 결과를 통해 선호하는 활동 유형을 파악할 수 있어요. "
                "'내 성격에 맞는 활동은 무엇인가요?' 같은 질문을 해보시면 "
                "성격 특성을 바탕으로 관심사를 추론해드릴 수 있습니다."
            )
        elif "THINKING_SKILLS" in available_doc_types:
            base_response += (
                "사고능력 분석 결과를 활용해 강점 영역과 관련된 관심사를 찾아볼 수 있어요. "
                "'내 사고능력 강점은 무엇인가요?' 질문으로 시작해보세요."
            )
        elif "COMPETENCY_ANALYSIS" in available_doc_types:
            base_response += (
                "역량 분석 결과를 통해 자연스럽게 끌리는 분야를 확인할 수 있어요. "
                "'내 핵심 역량은 무엇인가요?' 질문을 해보시면 도움이 될 것입니다."
            )
        elif "CAREER_RECOMMENDATIONS" in available_doc_types:
            base_response += (
                "진로 추천 결과를 통해 관심 분야를 역추적할 수 있어요. "
                "'추천된 직업들의 공통점은 무엇인가요?' 같은 질문을 해보세요."
            )
        else:
            base_response += (
                "다른 검사 결과가 준비되면 그를 바탕으로 선호도와 관련된 "
                "인사이트를 제공해드릴 수 있습니다. 적성검사를 완료하셨는지 확인해주세요."
            )
        
        return base_response

    async def _generate_fallback_response(self, constructed_context: ConstructedContext) -> str:
        question = (constructed_context.user_question or "").lower()
        topic = self._extract_topic_from_question(question)
        
        # Special handling for preference questions
        if (topic == "preference" or 
            any(keyword in question for keyword in ["선호", "preference", "좋아", "관심", "취향"])):
            return self._generate_preference_focused_fallback(constructed_context)
        
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
