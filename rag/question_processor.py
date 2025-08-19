"""
Question processing service for the RAG engine.

This module handles question categorization, intent detection, embedding generation,
validation, preprocessing, and follow-up question context management.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass
import asyncio

from etl.vector_embedder import VectorEmbedder


class QuestionCategory(Enum):
    """Categories for different types of questions users might ask."""
    PERSONALITY = "personality"
    THINKING_SKILLS = "thinking_skills"
    CAREER_RECOMMENDATIONS = "career_recommendations"
    LEARNING_STYLE = "learning_style"
    COMPETENCY_ANALYSIS = "competency_analysis"
    PREFERENCE_ANALYSIS = "preference_analysis"
    GENERAL_COMPARISON = "general_comparison"
    STATISTICAL_INFO = "statistical_info"
    UNKNOWN = "unknown"


class QuestionIntent(Enum):
    """Intent types for user questions."""
    EXPLAIN = "explain"  # "What does my personality type mean?"
    COMPARE = "compare"  # "How do I compare to others?"
    RECOMMEND = "recommend"  # "What careers are good for me?"
    ANALYZE = "analyze"  # "What are my strengths?"
    CLARIFY = "clarify"  # "Can you explain this result?"
    FOLLOW_UP = "follow_up"  # Follow-up to previous question
    UNKNOWN = "unknown"


@dataclass
class ProcessedQuestion:
    """Processed question with categorization and context."""
    original_text: str
    cleaned_text: str
    category: QuestionCategory
    intent: QuestionIntent
    embedding_vector: List[float]
    keywords: List[str]
    confidence_score: float
    context_from_previous: Optional[str] = None
    requires_specific_docs: List[str] = None


@dataclass
class ConversationContext:
    """Context from previous conversation turns."""
    user_id: str
    previous_questions: List[str]
    previous_categories: List[QuestionCategory]
    current_topic: Optional[QuestionCategory] = None
    conversation_depth: int = 0


class QuestionProcessor:
    """
    Service for processing user questions in the RAG system.
    
    Handles question categorization, intent detection, embedding generation,
    validation, preprocessing, and follow-up question context management.
    """
    
    def __init__(self, vector_embedder: VectorEmbedder):
        """Initialize the question processor with vector embedder."""
        self.vector_embedder = vector_embedder
        self.logger = logging.getLogger(__name__)
        
        # Category keywords for classification
        self.category_keywords = {
            QuestionCategory.PERSONALITY: [
                "성격", "성향", "기질", "personality", "tendency", "trait",
                "창의", "분석", "탐구", "안정", "보수", "수동",
                "primary", "secondary", "주요", "보조"
            ],
            QuestionCategory.THINKING_SKILLS: [
                "사고", "능력", "thinking", "cognitive", "skill", "ability",
                "언어", "수리", "공간", "추리", "지각", "기억", "처리",
                "verbal", "numerical", "spatial", "reasoning", "perceptual"
            ],
            QuestionCategory.CAREER_RECOMMENDATIONS: [
                "직업", "진로", "career", "job", "profession", "work",
                "추천", "recommend", "suitable", "적합", "맞는"
            ],
            QuestionCategory.LEARNING_STYLE: [
                "학습", "공부", "learning", "study", "education", "academic",
                "방법", "스타일", "style", "method", "approach"
            ],
            QuestionCategory.COMPETENCY_ANALYSIS: [
                "역량", "재능", "강점", "competency", "talent", "strength",
                "능력", "skill", "top", "상위", "우수"
            ],
            QuestionCategory.PREFERENCE_ANALYSIS: [
                "선호", "취향", "preference", "like", "interest", "favor",
                "이미지", "image", "picture", "visual", "선호도", "좋아하는",
                "관심", "흥미", "매력", "끌리는", "선택", "취미", "활동",
                "스타일", "패턴", "경향", "성향", "기호", "선호분석",
                "이미지선호", "선호검사", "선호결과", "선호도분석", "좋아",
                "어떤것", "무엇을", "뭘", "뭐를", "어떤활동", "어떤일",
                "취향분석"  # Specific combination
            ],
            QuestionCategory.GENERAL_COMPARISON: [
                "비교", "compare", "comparison", "versus", "차이", "difference",
                "다른", "similar", "유사", "대비"
            ],
            QuestionCategory.STATISTICAL_INFO: [
                "통계", "백분위", "순위", "statistics", "percentile", "rank",
                "평균", "average", "mean", "score", "점수"
            ]
        }
        
        # Intent keywords for classification
        self.intent_keywords = {
            QuestionIntent.EXPLAIN: [
                "설명", "의미", "뜻", "explain", "meaning", "what", "무엇",
                "어떤", "이란", "라는"
            ],
            QuestionIntent.COMPARE: [
                "비교", "compare", "차이", "difference", "다른", "similar",
                "대비", "versus", "보다"
            ],
            QuestionIntent.RECOMMEND: [
                "추천", "recommend", "suggest", "좋은", "적합", "맞는",
                "어떤", "which", "what"
            ],
            QuestionIntent.ANALYZE: [
                "분석", "analyze", "강점", "약점", "strength", "weakness",
                "특징", "characteristic", "어떻게"
            ],
            QuestionIntent.CLARIFY: [
                "명확", "자세", "더", "clarify", "detail", "specific",
                "구체적", "정확"
            ]
        }
        
        # Follow-up indicators
        self.follow_up_indicators = [
            "그럼", "그러면", "그래서", "또", "그리고", "추가로",
            "then", "also", "additionally", "furthermore", "moreover",
            "what about", "how about", "그것", "이것", "that", "this"
        ]
    
    async def process_question(
        self, 
        question: str, 
        user_id: str,
        conversation_context: Optional[ConversationContext] = None
    ) -> ProcessedQuestion:
        """
        Process a user question with full analysis and embedding generation.
        
        Args:
            question: Raw user question text
            user_id: User identifier
            conversation_context: Previous conversation context
            
        Returns:
            ProcessedQuestion with all analysis results
        """
        try:
            # Clean and preprocess the question
            cleaned_question = self._preprocess_question(question)
            
            # Validate the question
            if not self._validate_question(cleaned_question):
                raise ValueError(f"Invalid question format: {question}")
            
            # Categorize the question
            category, category_confidence = self._categorize_question(cleaned_question)
            
            # Detect intent
            intent, intent_confidence = self._detect_intent(cleaned_question, conversation_context)
            
            # Extract keywords
            keywords = self._extract_keywords(cleaned_question)
            
            # Generate embedding vector
            embedding_vector = await self.vector_embedder.generate_embedding(cleaned_question)
            
            # Handle follow-up context
            context_from_previous = self._extract_follow_up_context(
                cleaned_question, conversation_context
            )
            
            # Determine required document types
            required_docs = self._determine_required_documents(category, intent)
            
            # Calculate overall confidence
            confidence_score = (category_confidence + intent_confidence) / 2
            
            processed_question = ProcessedQuestion(
                original_text=question,
                cleaned_text=cleaned_question,
                category=category,
                intent=intent,
                embedding_vector=embedding_vector,
                keywords=keywords,
                confidence_score=confidence_score,
                context_from_previous=context_from_previous,
                requires_specific_docs=required_docs
            )
            
            self.logger.info(
                f"Processed question for user {user_id}: "
                f"category={category.value}, intent={intent.value}, "
                f"confidence={confidence_score:.2f}"
            )
            
            return processed_question
            
        except Exception as e:
            self.logger.error(f"Error processing question: {e}")
            raise
    
    def _preprocess_question(self, question: str) -> str:
        """
        Clean and preprocess the question text.
        
        Args:
            question: Raw question text
            
        Returns:
            Cleaned question text
        """
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', question.strip())
        
        # Remove special characters but keep Korean, English, numbers, and basic punctuation
        cleaned = re.sub(r'[^\w\s가-힣?.!,]', '', cleaned)
        
        # Normalize question marks
        cleaned = re.sub(r'[?？]+', '?', cleaned)
        
        # Ensure question ends with appropriate punctuation
        if not cleaned.endswith(('?', '.', '!', '？')):
            cleaned += '?'
        
        return cleaned
    
    def _validate_question(self, question: str) -> bool:
        """
        Validate if the question is appropriate for processing.
        
        Args:
            question: Cleaned question text
            
        Returns:
            True if valid, False otherwise
        """
        # Check minimum length
        if len(question.strip()) < 3:
            return False
        
        # Check maximum length (prevent extremely long questions)
        if len(question) > 500:
            return False
        
        # Check if it contains at least some meaningful content
        meaningful_chars = re.sub(r'[^\w가-힣]', '', question)
        if len(meaningful_chars) < 2:
            return False
        
        return True
    
    def _categorize_question(self, question: str) -> Tuple[QuestionCategory, float]:
        """
        Categorize the question based on keywords and patterns.
        
        Args:
            question: Cleaned question text
            
        Returns:
            Tuple of (category, confidence_score)
        """
        question_lower = question.lower()
        category_scores = {}
        
        # Score each category based on keyword matches
        for category, keywords in self.category_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in question_lower:
                    # Weight longer keywords more heavily
                    keyword_weight = len(keyword) / 10
                    
                    # Give extra weight to preference-specific keywords
                    if category == QuestionCategory.PREFERENCE_ANALYSIS:
                        if keyword in ["선호", "선호도", "취향", "좋아하는", "preference"]:
                            keyword_weight *= 2.0  # Double weight for core preference terms
                    
                    score += keyword_weight
            category_scores[category] = score
        
        # Find the category with highest score
        if not category_scores or max(category_scores.values()) == 0:
            return QuestionCategory.UNKNOWN, 0.0
        
        best_category = max(category_scores, key=category_scores.get)
        max_score = category_scores[best_category]
        
        # Normalize confidence score (0-1)
        confidence = min(max_score / 2.0, 1.0)
        
        return best_category, confidence
    
    def _detect_intent(
        self, 
        question: str, 
        context: Optional[ConversationContext] = None
    ) -> Tuple[QuestionIntent, float]:
        """
        Detect the intent of the question.
        
        Args:
            question: Cleaned question text
            context: Conversation context
            
        Returns:
            Tuple of (intent, confidence_score)
        """
        question_lower = question.lower()
        
        # Check for follow-up indicators first
        if context and context.conversation_depth > 0:
            for indicator in self.follow_up_indicators:
                if indicator in question_lower:
                    return QuestionIntent.FOLLOW_UP, 0.8
        
        # Score each intent based on keyword matches
        intent_scores = {}
        for intent, keywords in self.intent_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in question_lower:
                    score += len(keyword) / 10
            intent_scores[intent] = score
        
        # Find the intent with highest score
        if not intent_scores or max(intent_scores.values()) == 0:
            return QuestionIntent.UNKNOWN, 0.0
        
        best_intent = max(intent_scores, key=intent_scores.get)
        max_score = intent_scores[best_intent]
        
        # Normalize confidence score (0-1)
        confidence = min(max_score / 1.5, 1.0)
        
        return best_intent, confidence
    
    def _extract_keywords(self, question: str) -> List[str]:
        """
        Extract important keywords from the question.
        
        Args:
            question: Cleaned question text
            
        Returns:
            List of extracted keywords
        """
        # Remove common stop words (Korean and English)
        stop_words = {
            '은', '는', '이', '가', '을', '를', '에', '에서', '로', '으로',
            '와', '과', '의', '도', '만', '부터', '까지', '처럼', '같이',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'what', 'how', 'why',
            'when', 'where', 'who', 'which', '무엇', '어떻게', '왜', '언제',
            '어디서', '누가', '어떤', '그', '그것', '이것', '저것'
        }
        
        # Extract words (Korean and English) - improved regex for Korean
        words = re.findall(r'[가-힣]+|[a-zA-Z]+|\d+', question.lower())
        
        # Filter out stop words and short words
        keywords = [
            word for word in words 
            if word not in stop_words and len(word) > 1
        ]
        
        # Remove duplicates while preserving order
        unique_keywords = []
        seen = set()
        for keyword in keywords:
            if keyword not in seen:
                unique_keywords.append(keyword)
                seen.add(keyword)
        
        return unique_keywords[:10]  # Limit to top 10 keywords
    
    def _extract_follow_up_context(
        self, 
        question: str, 
        context: Optional[ConversationContext]
    ) -> Optional[str]:
        """
        Extract context from previous conversation for follow-up questions.
        
        Args:
            question: Current question text
            context: Previous conversation context
            
        Returns:
            Context string if this is a follow-up, None otherwise
        """
        if not context or context.conversation_depth == 0:
            return None
        
        question_lower = question.lower()
        
        # Check for follow-up indicators
        has_follow_up_indicator = any(
            indicator in question_lower 
            for indicator in self.follow_up_indicators
        )
        
        if has_follow_up_indicator and context.previous_questions:
            # Return the most recent question as context
            return context.previous_questions[-1]
        
        # Check for pronoun references that might indicate follow-up
        pronouns = ['그것', '이것', '저것', 'that', 'this', 'it']
        has_pronoun = any(pronoun in question_lower for pronoun in pronouns)
        
        if has_pronoun and context.current_topic:
            return f"Previous topic: {context.current_topic.value}"
        
        return None
    
    def _determine_required_documents(
        self, 
        category: QuestionCategory, 
        intent: QuestionIntent
    ) -> List[str]:
        """
        Determine which document types are needed to answer the question.
        
        Args:
            category: Question category
            intent: Question intent
            
        Returns:
            List of required document types
        """
        doc_mapping = {
            QuestionCategory.PERSONALITY: ["PERSONALITY_PROFILE"],
            QuestionCategory.THINKING_SKILLS: ["THINKING_SKILLS"],
            QuestionCategory.CAREER_RECOMMENDATIONS: [
                "CAREER_RECOMMENDATIONS", "PERSONALITY_PROFILE", "THINKING_SKILLS"
            ],
            QuestionCategory.LEARNING_STYLE: ["LEARNING_STYLE", "PERSONALITY_PROFILE"],
            QuestionCategory.COMPETENCY_ANALYSIS: ["COMPETENCY_ANALYSIS"],
            QuestionCategory.PREFERENCE_ANALYSIS: ["PREFERENCE_ANALYSIS"],
            QuestionCategory.GENERAL_COMPARISON: [
                "PERSONALITY_PROFILE", "THINKING_SKILLS", "COMPETENCY_ANALYSIS"
            ],
            QuestionCategory.STATISTICAL_INFO: [
                "PERSONALITY_PROFILE", "THINKING_SKILLS", "COMPETENCY_ANALYSIS"
            ]
        }
        
        required_docs = doc_mapping.get(category, [])
        
        # For comparison intents, we might need multiple document types
        if intent == QuestionIntent.COMPARE and len(required_docs) == 1:
            required_docs.extend(["COMPETENCY_ANALYSIS"])
        
        return required_docs
    
    def update_conversation_context(
        self, 
        context: ConversationContext, 
        processed_question: ProcessedQuestion
    ) -> ConversationContext:
        """
        Update conversation context with the new question.
        
        Args:
            context: Current conversation context
            processed_question: Newly processed question
            
        Returns:
            Updated conversation context
        """
        # Add question to history
        context.previous_questions.append(processed_question.original_text)
        context.previous_categories.append(processed_question.category)
        
        # Update current topic
        if processed_question.category != QuestionCategory.UNKNOWN:
            context.current_topic = processed_question.category
        
        # Increment conversation depth
        context.conversation_depth += 1
        
        # Keep only recent history (last 5 questions)
        if len(context.previous_questions) > 5:
            context.previous_questions = context.previous_questions[-5:]
            context.previous_categories = context.previous_categories[-5:]
        
        return context