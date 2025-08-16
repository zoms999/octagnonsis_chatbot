"""
Context construction engine for the RAG system.

This module handles document retrieval and ranking, prompt template management,
context window management for LLM input limits, and document relevance scoring.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json

from database.vector_search import VectorSearchService, SearchQuery, SearchResult as VectorSearchResult
from database.models import ChatDocument
from rag.question_processor import ProcessedQuestion, QuestionCategory, QuestionIntent
from database.vector_search import VectorSearchError


class PromptTemplate(Enum):
    """Template types for different question categories and intents."""
    PERSONALITY_EXPLAIN = "personality_explain"
    PERSONALITY_COMPARE = "personality_compare"
    CAREER_RECOMMEND = "career_recommend"
    CAREER_EXPLAIN = "career_explain"
    THINKING_SKILLS_ANALYZE = "thinking_skills_analyze"
    THINKING_SKILLS_COMPARE = "thinking_skills_compare"
    LEARNING_STYLE_RECOMMEND = "learning_style_recommend"
    COMPETENCY_ANALYZE = "competency_analyze"
    GENERAL_COMPARE = "general_compare"
    STATISTICAL_INFO = "statistical_info"
    FOLLOW_UP = "follow_up"
    DEFAULT = "default"


@dataclass
class RetrievedDocument:
    """Document retrieved from vector search with relevance scoring."""
    document: ChatDocument
    similarity_score: float
    relevance_score: float
    content_summary: str
    key_points: List[str]


@dataclass
class ConstructedContext:
    """Complete context constructed for LLM input."""
    user_question: str
    retrieved_documents: List[RetrievedDocument]
    prompt_template: PromptTemplate
    formatted_prompt: str
    context_metadata: Dict[str, Any]
    token_count_estimate: int
    truncated: bool = False


class ContextBuilder:
    """
    Context construction engine for the RAG system.
    
    Handles document retrieval, ranking, prompt template selection,
    and context window management for optimal LLM performance.
    """
    
    def __init__(self, vector_search_service: VectorSearchService, max_context_tokens: int = 4000):
        """
        Initialize the context builder.
        
        Args:
            vector_search_service: Service for vector similarity search
            max_context_tokens: Maximum tokens allowed in context window
        """
        self.vector_search = vector_search_service
        self.max_context_tokens = max_context_tokens
        self.logger = logging.getLogger(__name__)
        
        # Prompt templates for different question types
        self.prompt_templates = {
            PromptTemplate.PERSONALITY_EXPLAIN: """
당신은 적성검사 결과를 분석하고 설명하는 전문 상담사입니다. 사용자의 성격 유형에 대해 자세히 설명해주세요.

사용자 질문: {question}

관련 검사 결과:
{context_documents}

위 결과를 바탕으로 사용자의 성격 유형을 친근하고 이해하기 쉽게 설명해주세요. 구체적인 특징과 장점을 포함하여 답변해주세요.
""",
            
            PromptTemplate.PERSONALITY_COMPARE: """
당신은 적성검사 결과를 분석하는 전문 상담사입니다. 사용자의 성격을 다른 사람들과 비교하여 설명해주세요.

사용자 질문: {question}

관련 검사 결과:
{context_documents}

위 결과를 바탕으로 사용자의 성격이 일반적인 사람들과 어떻게 다른지, 어떤 점이 특별한지 비교하여 설명해주세요. 백분위나 순위 정보가 있다면 포함해주세요.
""",
            
            PromptTemplate.CAREER_RECOMMEND: """
당신은 진로 상담 전문가입니다. 사용자의 적성검사 결과를 바탕으로 적합한 직업을 추천해주세요.

사용자 질문: {question}

관련 검사 결과:
{context_documents}

위 결과를 바탕으로 사용자에게 적합한 직업들을 추천하고, 왜 그 직업이 적합한지 성격과 능력을 연결하여 구체적으로 설명해주세요.
""",
            
            PromptTemplate.CAREER_EXPLAIN: """
당신은 진로 상담 전문가입니다. 사용자의 적성검사 결과와 직업 추천에 대해 설명해주세요.

사용자 질문: {question}

관련 검사 결과:
{context_documents}

위 결과를 바탕으로 추천된 직업들이 왜 사용자에게 적합한지, 어떤 성격적 특성이나 능력이 해당 직업과 잘 맞는지 자세히 설명해주세요.
""",
            
            PromptTemplate.THINKING_SKILLS_ANALYZE: """
당신은 인지능력 평가 전문가입니다. 사용자의 사고 능력에 대해 분석하여 설명해주세요.

사용자 질문: {question}

관련 검사 결과:
{context_documents}

위 결과를 바탕으로 사용자의 8가지 사고 능력(언어, 수리, 공간, 추리, 지각속도, 기억력, 어학, 창의력)을 분석하여 강점과 약점을 설명해주세요.
""",
            
            PromptTemplate.THINKING_SKILLS_COMPARE: """
당신은 인지능력 평가 전문가입니다. 사용자의 사고 능력을 다른 사람들과 비교하여 설명해주세요.

사용자 질문: {question}

관련 검사 결과:
{context_documents}

위 결과를 바탕으로 사용자의 사고 능력이 또래나 일반인들과 비교했을 때 어떤 수준인지, 특히 뛰어난 영역이나 보완이 필요한 영역을 설명해주세요.
""",
            
            PromptTemplate.LEARNING_STYLE_RECOMMEND: """
당신은 학습 방법 전문가입니다. 사용자의 적성에 맞는 학습 방법을 추천해주세요.

사용자 질문: {question}

관련 검사 결과:
{context_documents}

위 결과를 바탕으로 사용자의 성격과 사고 능력에 맞는 효과적인 학습 방법과 공부 전략을 구체적으로 추천해주세요.
""",
            
            PromptTemplate.COMPETENCY_ANALYZE: """
당신은 역량 분석 전문가입니다. 사용자의 핵심 역량과 재능에 대해 분석해주세요.

사용자 질문: {question}

관련 검사 결과:
{context_documents}

위 결과를 바탕으로 사용자의 상위 5개 재능과 역량을 분석하고, 이를 어떻게 활용할 수 있는지 구체적으로 설명해주세요.
""",
            
            PromptTemplate.GENERAL_COMPARE: """
당신은 적성검사 분석 전문가입니다. 사용자의 전반적인 검사 결과를 비교 분석해주세요.

사용자 질문: {question}

관련 검사 결과:
{context_documents}

위 결과를 바탕으로 사용자의 성격, 사고능력, 역량 등을 종합적으로 분석하고 다른 사람들과 비교하여 설명해주세요.
""",
            
            PromptTemplate.STATISTICAL_INFO: """
당신은 적성검사 통계 분석 전문가입니다. 사용자의 검사 결과에 대한 통계적 정보를 설명해주세요.

사용자 질문: {question}

관련 검사 결과:
{context_documents}

위 결과를 바탕으로 사용자의 점수, 백분위, 순위 등 통계적 정보를 이해하기 쉽게 설명해주세요.
""",
            
            PromptTemplate.FOLLOW_UP: """
당신은 적성검사 상담 전문가입니다. 이전 대화의 맥락을 고려하여 추가 질문에 답변해주세요.

이전 맥락: {previous_context}
사용자 질문: {question}

관련 검사 결과:
{context_documents}

이전 대화의 맥락을 고려하여 사용자의 추가 질문에 자세히 답변해주세요.
""",
            
            PromptTemplate.DEFAULT: """
당신은 적성검사 결과 상담 전문가입니다. 사용자의 질문에 대해 검사 결과를 바탕으로 답변해주세요.

사용자 질문: {question}

관련 검사 결과:
{context_documents}

위 검사 결과를 바탕으로 사용자의 질문에 친근하고 전문적으로 답변해주세요.
"""
        }
    
    async def build_context(
        self, 
        processed_question: ProcessedQuestion, 
        user_id: str,
        previous_context: Optional[str] = None
    ) -> ConstructedContext:
        """
        Build complete context for LLM input.
        
        Args:
            processed_question: Processed user question
            user_id: User identifier
            previous_context: Previous conversation context if follow-up
            
        Returns:
            ConstructedContext with all necessary information
        """
        try:
            # Retrieve relevant documents
            retrieved_docs = await self._retrieve_and_rank_documents(
                processed_question, user_id
            )
            
            # Select appropriate prompt template
            template = self._select_prompt_template(processed_question)
            
            # Format context documents for prompt
            formatted_docs = self._format_documents_for_prompt(retrieved_docs)
            
            # Construct the prompt
            formatted_prompt = self._construct_prompt(
                template, processed_question.original_text, 
                formatted_docs, previous_context
            )
            
            # Estimate token count and truncate if necessary
            token_estimate = self._estimate_token_count(formatted_prompt)
            truncated = False
            
            if token_estimate > self.max_context_tokens:
                formatted_prompt, retrieved_docs = self._truncate_context(
                    formatted_prompt, retrieved_docs, template, 
                    processed_question.original_text, previous_context
                )
                token_estimate = self._estimate_token_count(formatted_prompt)
                truncated = True
            
            context = ConstructedContext(
                user_question=processed_question.original_text,
                retrieved_documents=retrieved_docs,
                prompt_template=template,
                formatted_prompt=formatted_prompt,
                context_metadata={
                    "question_category": processed_question.category.value,
                    "question_intent": processed_question.intent.value,
                    "confidence_score": processed_question.confidence_score,
                    "num_documents": len(retrieved_docs),
                    "has_previous_context": previous_context is not None
                },
                token_count_estimate=token_estimate,
                truncated=truncated
            )
            
            self.logger.info(
                f"Built context for user {user_id}: "
                f"template={template.value}, docs={len(retrieved_docs)}, "
                f"tokens={token_estimate}, truncated={truncated}"
            )
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error building context: {e}")
            raise
    
    async def _retrieve_and_rank_documents(
        self, 
        processed_question: ProcessedQuestion, 
        user_id: str
    ) -> List[RetrievedDocument]:
        """
        Retrieve and rank documents based on the processed question.
        
        Args:
            processed_question: Processed user question
            user_id: User identifier
            
        Returns:
            List of ranked retrieved documents
        """
        # Create search query for vector similarity search
        from uuid import UUID
        import uuid
        
        # Handle user_id conversion - if it's not a valid UUID, create one for testing
        try:
            if isinstance(user_id, str) and len(user_id) == 32:
                # Assume it's a hex string without dashes
                user_uuid = UUID(user_id)
            elif isinstance(user_id, str) and '-' in user_id:
                # Assume it's a properly formatted UUID string
                user_uuid = UUID(user_id)
            else:
                # For testing purposes, create a deterministic UUID from the string
                user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)
        except ValueError:
            # Fallback for invalid UUID strings (like "user1" in tests)
            user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)
        
        search_query = SearchQuery(
            user_id=user_uuid,
            query_vector=processed_question.embedding_vector,
            doc_type_filter=processed_question.requires_specific_docs,
            limit=10,  # Get more than needed for ranking
            similarity_threshold=0.5  # Lower threshold to get more candidates
        )
        
        # Perform vector similarity search with graceful degradation
        try:
            search_results = await self.vector_search.similarity_search(search_query)
            
            # If no results found, try with lower threshold
            if not search_results:
                self.logger.warning(f"No results found with threshold 0.5, retrying with 0.3")
                search_query.similarity_threshold = 0.3
                search_results = await self.vector_search.similarity_search(search_query)
                
            # If still no results, try without doc type filter
            if not search_results and processed_question.requires_specific_docs:
                self.logger.warning(f"No results found with doc type filter, retrying without filter")
                search_query.doc_type_filter = None
                search_query.similarity_threshold = 0.3
                search_results = await self.vector_search.similarity_search(search_query)
                
        except VectorSearchError as e:
            self.logger.error(f"Vector search failed: {e}. Falling back to empty context.")
            return []
        
        # Convert to RetrievedDocument objects with additional scoring
        retrieved_docs = []
        for search_result in search_results:
            doc = search_result.document
            similarity_score = search_result.similarity_score
            
            # Calculate relevance score based on multiple factors
            relevance_score = self._calculate_relevance_score(
                doc, processed_question, similarity_score
            )
            
            # Extract key points from document content
            key_points = self._extract_key_points(doc, processed_question)
            
            # Create content summary
            content_summary = self._create_content_summary(doc)
            
            retrieved_doc = RetrievedDocument(
                document=doc,
                similarity_score=similarity_score,
                relevance_score=relevance_score,
                content_summary=content_summary,
                key_points=key_points
            )
            retrieved_docs.append(retrieved_doc)
        
        # Sort by relevance score (highest first)
        retrieved_docs.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Return top 5 most relevant documents
        return retrieved_docs[:5]
    
    def _calculate_relevance_score(
        self, 
        document: ChatDocument, 
        processed_question: ProcessedQuestion, 
        similarity_score: float
    ) -> float:
        """
        Calculate relevance score combining multiple factors.
        
        Args:
            document: Retrieved document
            processed_question: Processed question
            similarity_score: Vector similarity score
            
        Returns:
            Combined relevance score (0-1)
        """
        # Start with similarity score (0-1)
        relevance = similarity_score
        
        # Boost score if document type matches required types
        if document.doc_type in processed_question.requires_specific_docs:
            relevance += 0.2
        
        # Boost score for keyword matches in document content
        doc_text = document.summary_text.lower()
        keyword_matches = sum(
            1 for keyword in processed_question.keywords 
            if keyword.lower() in doc_text
        )
        keyword_boost = min(keyword_matches * 0.1, 0.3)
        relevance += keyword_boost
        
        # Boost score based on document content richness
        try:
            content = json.loads(document.content) if isinstance(document.content, str) else document.content
            content_richness = len(str(content)) / 1000  # Normalize by content length
            content_boost = min(content_richness * 0.1, 0.2)
            relevance += content_boost
        except:
            pass
        
        # Ensure score stays within 0-1 range
        return min(relevance, 1.0)
    
    def _extract_key_points(
        self, 
        document: ChatDocument, 
        processed_question: ProcessedQuestion
    ) -> List[str]:
        """
        Extract key points from document relevant to the question.
        
        Args:
            document: Document to extract from
            processed_question: User's processed question
            
        Returns:
            List of key points
        """
        key_points = []
        
        try:
            content = json.loads(document.content) if isinstance(document.content, str) else document.content
            
            # Extract key points based on document type
            if document.doc_type == "PERSONALITY_PROFILE":
                if "primary_tendency" in content:
                    key_points.append(f"주요 성향: {content['primary_tendency'].get('name', '')}")
                if "secondary_tendency" in content:
                    key_points.append(f"보조 성향: {content['secondary_tendency'].get('name', '')}")
                if "top_tendencies" in content:
                    top_3 = content["top_tendencies"][:3]
                    for i, tendency in enumerate(top_3, 1):
                        key_points.append(f"{i}위: {tendency.get('name', '')} ({tendency.get('score', '')}점)")
            
            elif document.doc_type == "THINKING_SKILLS":
                if "skills" in content:
                    for skill in content["skills"][:3]:  # Top 3 skills
                        key_points.append(f"{skill.get('name', '')}: {skill.get('score', '')}점")
            
            elif document.doc_type == "CAREER_RECOMMENDATIONS":
                if "recommended_jobs" in content:
                    for job in content["recommended_jobs"][:3]:  # Top 3 jobs
                        key_points.append(f"추천 직업: {job.get('name', '')}")
            
            elif document.doc_type == "COMPETENCY_ANALYSIS":
                if "top_competencies" in content:
                    for comp in content["top_competencies"][:3]:  # Top 3 competencies
                        key_points.append(f"핵심 역량: {comp.get('name', '')} ({comp.get('percentile', '')}%)")
            
        except Exception as e:
            self.logger.warning(f"Error extracting key points: {e}")
            # Fallback to summary text
            key_points = [document.summary_text[:100] + "..."]
        
        return key_points[:5]  # Limit to 5 key points
    
    def _create_content_summary(self, document: ChatDocument) -> str:
        """
        Create a concise summary of document content.
        
        Args:
            document: Document to summarize
            
        Returns:
            Content summary string
        """
        # Use existing summary_text if available and concise
        if document.summary_text and len(document.summary_text) <= 200:
            return document.summary_text
        
        # Otherwise create a new summary from content
        try:
            content = json.loads(document.content) if isinstance(document.content, str) else document.content
            
            if document.doc_type == "PERSONALITY_PROFILE":
                primary = content.get("primary_tendency", {}).get("name", "")
                secondary = content.get("secondary_tendency", {}).get("name", "")
                return f"주요 성향: {primary}, 보조 성향: {secondary}"
            
            elif document.doc_type == "THINKING_SKILLS":
                skills = content.get("skills", [])[:2]
                skill_names = [skill.get("name", "") for skill in skills]
                return f"주요 사고능력: {', '.join(skill_names)}"
            
            elif document.doc_type == "CAREER_RECOMMENDATIONS":
                jobs = content.get("recommended_jobs", [])[:2]
                job_names = [job.get("name", "") for job in jobs]
                return f"추천 직업: {', '.join(job_names)}"
            
            else:
                return document.summary_text[:150] + "..." if document.summary_text else "검사 결과 데이터"
                
        except Exception as e:
            self.logger.warning(f"Error creating content summary: {e}")
            return document.summary_text[:150] + "..." if document.summary_text else "검사 결과 데이터"
    
    def _select_prompt_template(self, processed_question: ProcessedQuestion) -> PromptTemplate:
        """
        Select appropriate prompt template based on question analysis.
        
        Args:
            processed_question: Processed user question
            
        Returns:
            Selected prompt template
        """
        category = processed_question.category
        intent = processed_question.intent
        
        # Handle follow-up questions first
        if intent == QuestionIntent.FOLLOW_UP:
            return PromptTemplate.FOLLOW_UP
        
        # Map category and intent combinations to templates
        template_mapping = {
            (QuestionCategory.PERSONALITY, QuestionIntent.EXPLAIN): PromptTemplate.PERSONALITY_EXPLAIN,
            (QuestionCategory.PERSONALITY, QuestionIntent.COMPARE): PromptTemplate.PERSONALITY_COMPARE,
            (QuestionCategory.CAREER_RECOMMENDATIONS, QuestionIntent.RECOMMEND): PromptTemplate.CAREER_RECOMMEND,
            (QuestionCategory.CAREER_RECOMMENDATIONS, QuestionIntent.EXPLAIN): PromptTemplate.CAREER_EXPLAIN,
            (QuestionCategory.THINKING_SKILLS, QuestionIntent.ANALYZE): PromptTemplate.THINKING_SKILLS_ANALYZE,
            (QuestionCategory.THINKING_SKILLS, QuestionIntent.COMPARE): PromptTemplate.THINKING_SKILLS_COMPARE,
            (QuestionCategory.LEARNING_STYLE, QuestionIntent.RECOMMEND): PromptTemplate.LEARNING_STYLE_RECOMMEND,
            (QuestionCategory.COMPETENCY_ANALYSIS, QuestionIntent.ANALYZE): PromptTemplate.COMPETENCY_ANALYZE,
            (QuestionCategory.GENERAL_COMPARISON, QuestionIntent.COMPARE): PromptTemplate.GENERAL_COMPARE,
            (QuestionCategory.STATISTICAL_INFO, QuestionIntent.EXPLAIN): PromptTemplate.STATISTICAL_INFO,
        }
        
        return template_mapping.get((category, intent), PromptTemplate.DEFAULT)
    
    def _format_documents_for_prompt(self, retrieved_docs: List[RetrievedDocument]) -> str:
        """
        Format retrieved documents for inclusion in prompt.
        
        Args:
            retrieved_docs: List of retrieved documents
            
        Returns:
            Formatted document string
        """
        if not retrieved_docs:
            return "관련 검사 결과를 찾을 수 없습니다. 적성검사를 완료하셨는지 확인해 주세요."
        
        formatted_parts = []
        
        for i, doc in enumerate(retrieved_docs, 1):
            doc_section = f"\n=== 검사 결과 {i}: {doc.document.doc_type} ===\n"
            doc_section += f"요약: {doc.content_summary}\n"
            
            if doc.key_points:
                doc_section += "주요 내용:\n"
                for point in doc.key_points:
                    doc_section += f"- {point}\n"
            
            # Add relevant content details
            try:
                content = json.loads(doc.document.content) if isinstance(doc.document.content, str) else doc.document.content
                doc_section += f"\n상세 데이터:\n{json.dumps(content, ensure_ascii=False, indent=2)}\n"
            except:
                doc_section += f"\n상세 내용: {doc.document.summary_text}\n"
            
            formatted_parts.append(doc_section)
        
        return "\n".join(formatted_parts)
    
    def _construct_prompt(
        self, 
        template: PromptTemplate, 
        question: str, 
        formatted_docs: str,
        previous_context: Optional[str] = None
    ) -> str:
        """
        Construct the final prompt using the selected template.
        
        Args:
            template: Selected prompt template
            question: User's original question
            formatted_docs: Formatted document context
            previous_context: Previous conversation context
            
        Returns:
            Complete formatted prompt
        """
        template_str = self.prompt_templates[template]
        
        if template == PromptTemplate.FOLLOW_UP and previous_context:
            return template_str.format(
                question=question,
                context_documents=formatted_docs,
                previous_context=previous_context
            )
        else:
            return template_str.format(
                question=question,
                context_documents=formatted_docs
            )
    
    def _estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for the given text.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Rough estimation: 1 token ≈ 4 characters for mixed Korean/English text
        # This is a conservative estimate
        return len(text) // 3
    
    def _truncate_context(
        self, 
        prompt: str, 
        retrieved_docs: List[RetrievedDocument],
        template: PromptTemplate,
        question: str,
        previous_context: Optional[str] = None
    ) -> Tuple[str, List[RetrievedDocument]]:
        """
        Truncate context to fit within token limits.
        
        Args:
            prompt: Original prompt
            retrieved_docs: Retrieved documents
            template: Prompt template
            question: User question
            previous_context: Previous context
            
        Returns:
            Tuple of (truncated_prompt, truncated_docs)
        """
        # Start by reducing number of documents
        max_docs = len(retrieved_docs)
        
        while max_docs > 1:
            # Try with fewer documents
            truncated_docs = retrieved_docs[:max_docs]
            formatted_docs = self._format_documents_for_prompt(truncated_docs)
            
            # Reconstruct prompt
            truncated_prompt = self._construct_prompt(
                template, question, formatted_docs, previous_context
            )
            
            # Check if it fits
            if self._estimate_token_count(truncated_prompt) <= self.max_context_tokens:
                return truncated_prompt, truncated_docs
            
            max_docs -= 1
        
        # If still too long, truncate document content
        if retrieved_docs:
            doc = retrieved_docs[0]
            # Create minimal document representation
            minimal_doc = f"검사 결과: {doc.content_summary}"
            truncated_prompt = self._construct_prompt(
                template, question, minimal_doc, previous_context
            )
            return truncated_prompt, [doc]
        
        # Fallback: just the question
        fallback_prompt = f"사용자 질문: {question}\n\n검사 결과 데이터를 불러올 수 없습니다. 일반적인 조언을 제공해주세요."
        return fallback_prompt, []