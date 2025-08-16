"""
Tests for the question processor service.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from rag.question_processor import (
    QuestionProcessor, QuestionCategory, QuestionIntent, 
    ProcessedQuestion, ConversationContext
)
from etl.vector_embedder import VectorEmbedder


@pytest.fixture
def mock_vector_embedder():
    """Create a mock vector embedder."""
    embedder = Mock(spec=VectorEmbedder)
    embedder.generate_embedding = AsyncMock(return_value=[0.1] * 768)
    return embedder


@pytest.fixture
def question_processor(mock_vector_embedder):
    """Create a question processor with mock embedder."""
    return QuestionProcessor(mock_vector_embedder)


@pytest.mark.asyncio
async def test_process_personality_question(question_processor):
    """Test processing a personality-related question."""
    question = "내 성격 유형이 무엇인가요?"
    user_id = "test_user"
    
    result = await question_processor.process_question(question, user_id)
    
    assert isinstance(result, ProcessedQuestion)
    assert result.original_text == question
    assert result.category == QuestionCategory.PERSONALITY
    assert result.intent in [QuestionIntent.EXPLAIN, QuestionIntent.UNKNOWN]
    assert len(result.embedding_vector) == 768
    assert len(result.keywords) > 0


@pytest.mark.asyncio
async def test_process_career_question(question_processor):
    """Test processing a career-related question."""
    question = "What careers are recommended for me?"
    user_id = "test_user"
    
    result = await question_processor.process_question(question, user_id)
    
    assert result.category == QuestionCategory.CAREER_RECOMMENDATIONS
    assert result.intent == QuestionIntent.RECOMMEND
    assert "CAREER_RECOMMENDATIONS" in result.requires_specific_docs


@pytest.mark.asyncio
async def test_process_thinking_skills_question(question_processor):
    """Test processing a thinking skills question."""
    question = "내 사고 능력은 어떤가요?"
    user_id = "test_user"
    
    result = await question_processor.process_question(question, user_id)
    
    assert result.category == QuestionCategory.THINKING_SKILLS
    assert "THINKING_SKILLS" in result.requires_specific_docs


@pytest.mark.asyncio
async def test_follow_up_question_detection(question_processor):
    """Test detection of follow-up questions."""
    # Create conversation context
    context = ConversationContext(
        user_id="test_user",
        previous_questions=["내 성격 유형이 무엇인가요?"],
        previous_categories=[QuestionCategory.PERSONALITY],
        current_topic=QuestionCategory.PERSONALITY,
        conversation_depth=1
    )
    
    follow_up_question = "그럼 이 성격에 맞는 직업은 뭐가 있나요?"
    
    result = await question_processor.process_question(
        follow_up_question, "test_user", context
    )
    
    assert result.intent == QuestionIntent.FOLLOW_UP
    assert result.context_from_previous is not None


def test_question_preprocessing(question_processor):
    """Test question preprocessing functionality."""
    # Test with messy input
    messy_question = "   내   성격이    어떤가요???   "
    cleaned = question_processor._preprocess_question(messy_question)
    
    assert cleaned == "내 성격이 어떤가요?"
    
    # Test with special characters
    special_chars = "내 성격@#$%이 어떤가요!!"
    cleaned = question_processor._preprocess_question(special_chars)
    
    assert "@#$%" not in cleaned
    assert "성격" in cleaned


def test_question_validation(question_processor):
    """Test question validation."""
    # Valid questions
    assert question_processor._validate_question("내 성격이 어떤가요?")
    assert question_processor._validate_question("What is my personality type?")
    
    # Invalid questions
    assert not question_processor._validate_question("")  # Empty
    assert not question_processor._validate_question("a")  # Too short
    assert not question_processor._validate_question("?" * 600)  # Too long


def test_question_categorization(question_processor):
    """Test question categorization."""
    # Personality questions
    personality_q = "내 주요 성향이 무엇인가요?"
    category, confidence = question_processor._categorize_question(personality_q)
    assert category == QuestionCategory.PERSONALITY
    assert confidence > 0
    
    # Career questions
    career_q = "추천 직업이 무엇인가요?"
    category, confidence = question_processor._categorize_question(career_q)
    assert category == QuestionCategory.CAREER_RECOMMENDATIONS
    assert confidence > 0
    
    # Unknown questions
    unknown_q = "오늘 날씨가 어떤가요?"
    category, confidence = question_processor._categorize_question(unknown_q)
    assert category == QuestionCategory.UNKNOWN


def test_intent_detection(question_processor):
    """Test intent detection."""
    # Explanation intent
    explain_q = "이 결과가 무엇을 의미하나요?"
    intent, confidence = question_processor._detect_intent(explain_q)
    assert intent == QuestionIntent.EXPLAIN
    
    # Recommendation intent
    recommend_q = "어떤 직업을 추천하나요?"
    intent, confidence = question_processor._detect_intent(recommend_q)
    assert intent == QuestionIntent.RECOMMEND
    
    # Comparison intent
    compare_q = "다른 사람들과 비교해서 어떤가요?"
    intent, confidence = question_processor._detect_intent(compare_q)
    assert intent == QuestionIntent.COMPARE


def test_keyword_extraction(question_processor):
    """Test keyword extraction."""
    question = "내 성격 유형과 추천 직업이 무엇인가요?"
    keywords = question_processor._extract_keywords(question)
    
    assert "성격" in keywords
    assert "추천" in keywords
    # Korean particles may be attached, so check for partial matches
    assert any("유형" in keyword for keyword in keywords)
    assert any("직업" in keyword for keyword in keywords)
    # Stop words should be filtered out
    assert "이" not in keywords
    assert "가" not in keywords


def test_conversation_context_update(question_processor):
    """Test conversation context updates."""
    context = ConversationContext(
        user_id="test_user",
        previous_questions=[],
        previous_categories=[],
        conversation_depth=0
    )
    
    processed_question = ProcessedQuestion(
        original_text="내 성격이 어떤가요?",
        cleaned_text="내 성격이 어떤가요?",
        category=QuestionCategory.PERSONALITY,
        intent=QuestionIntent.EXPLAIN,
        embedding_vector=[0.1] * 768,
        keywords=["성격"],
        confidence_score=0.8
    )
    
    updated_context = question_processor.update_conversation_context(
        context, processed_question
    )
    
    assert len(updated_context.previous_questions) == 1
    assert updated_context.current_topic == QuestionCategory.PERSONALITY
    assert updated_context.conversation_depth == 1


def test_required_documents_determination(question_processor):
    """Test determination of required documents."""
    # Personality questions should require personality profile
    docs = question_processor._determine_required_documents(
        QuestionCategory.PERSONALITY, QuestionIntent.EXPLAIN
    )
    assert "PERSONALITY_PROFILE" in docs
    
    # Career questions should require multiple document types
    docs = question_processor._determine_required_documents(
        QuestionCategory.CAREER_RECOMMENDATIONS, QuestionIntent.RECOMMEND
    )
    assert "CAREER_RECOMMENDATIONS" in docs
    assert "PERSONALITY_PROFILE" in docs
    assert "THINKING_SKILLS" in docs


if __name__ == "__main__":
    pytest.main([__file__])