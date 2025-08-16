"""
Tests for the context builder service.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock
from dataclasses import dataclass

from rag.context_builder import (
    ContextBuilder, PromptTemplate, RetrievedDocument, ConstructedContext
)
from rag.question_processor import (
    ProcessedQuestion, QuestionCategory, QuestionIntent
)
from database.vector_search import VectorSearchService, SearchResult as VectorSearchResult
from database.models import ChatDocument


@dataclass
class MockChatDocument:
    """Mock ChatDocument for testing."""
    doc_id: str
    user_id: str
    doc_type: str
    content: str
    summary_text: str
    embedding_vector: list


@pytest.fixture
def mock_vector_search():
    """Create a mock vector search service."""
    service = Mock(spec=VectorSearchService)
    
    # Create mock documents
    personality_doc = MockChatDocument(
        doc_id="doc1",
        user_id="user1",
        doc_type="PERSONALITY_PROFILE",
        content=json.dumps({
            "primary_tendency": {"name": "창의형", "score": 85},
            "secondary_tendency": {"name": "분석형", "score": 78},
            "top_tendencies": [
                {"rank": 1, "name": "창의형", "score": 85},
                {"rank": 2, "name": "분석형", "score": 78}
            ]
        }),
        summary_text="주요 성향: 창의형, 보조 성향: 분석형",
        embedding_vector=[0.1] * 768
    )
    
    career_doc = MockChatDocument(
        doc_id="doc2",
        user_id="user1",
        doc_type="CAREER_RECOMMENDATIONS",
        content=json.dumps({
            "recommended_jobs": [
                {"name": "소프트웨어 개발자", "match_score": 92},
                {"name": "데이터 분석가", "match_score": 88}
            ]
        }),
        summary_text="추천 직업: 소프트웨어 개발자, 데이터 분석가",
        embedding_vector=[0.2] * 768
    )
    
    # Mock the similarity_search method to return VectorSearchResult objects
    search_result1 = VectorSearchResult(
        document=personality_doc,
        similarity_score=0.85,
        rank=1,
        search_metadata={}
    )
    search_result2 = VectorSearchResult(
        document=career_doc,
        similarity_score=0.78,
        rank=2,
        search_metadata={}
    )
    
    service.similarity_search = AsyncMock(return_value=[search_result1, search_result2])
    
    return service


@pytest.fixture
def context_builder(mock_vector_search):
    """Create a context builder with mock dependencies."""
    return ContextBuilder(mock_vector_search, max_context_tokens=4000)


@pytest.fixture
def sample_processed_question():
    """Create a sample processed question."""
    return ProcessedQuestion(
        original_text="내 성격 유형이 무엇인가요?",
        cleaned_text="내 성격 유형이 무엇인가요?",
        category=QuestionCategory.PERSONALITY,
        intent=QuestionIntent.EXPLAIN,
        embedding_vector=[0.1] * 768,
        keywords=["성격", "유형"],
        confidence_score=0.8,
        requires_specific_docs=["PERSONALITY_PROFILE"]
    )


@pytest.mark.asyncio
async def test_build_context_personality_question(context_builder, sample_processed_question):
    """Test building context for a personality question."""
    result = await context_builder.build_context(
        sample_processed_question, "user1"
    )
    
    assert isinstance(result, ConstructedContext)
    assert result.user_question == "내 성격 유형이 무엇인가요?"
    assert result.prompt_template == PromptTemplate.PERSONALITY_EXPLAIN
    assert len(result.retrieved_documents) > 0
    assert "성격 유형" in result.formatted_prompt
    assert result.token_count_estimate > 0


@pytest.mark.asyncio
async def test_build_context_career_question(context_builder, mock_vector_search):
    """Test building context for a career question."""
    career_question = ProcessedQuestion(
        original_text="어떤 직업이 나에게 맞나요?",
        cleaned_text="어떤 직업이 나에게 맞나요?",
        category=QuestionCategory.CAREER_RECOMMENDATIONS,
        intent=QuestionIntent.RECOMMEND,
        embedding_vector=[0.1] * 768,
        keywords=["직업", "맞는"],
        confidence_score=0.9,
        requires_specific_docs=["CAREER_RECOMMENDATIONS"]
    )
    
    result = await context_builder.build_context(career_question, "user1")
    
    assert result.prompt_template == PromptTemplate.CAREER_RECOMMEND
    assert "직업" in result.formatted_prompt
    assert "추천" in result.formatted_prompt


@pytest.mark.asyncio
async def test_build_context_follow_up_question(context_builder, sample_processed_question):
    """Test building context for a follow-up question."""
    follow_up_question = ProcessedQuestion(
        original_text="그럼 이 성격에 맞는 직업은 뭐가 있나요?",
        cleaned_text="그럼 이 성격에 맞는 직업은 뭐가 있나요?",
        category=QuestionCategory.CAREER_RECOMMENDATIONS,
        intent=QuestionIntent.FOLLOW_UP,
        embedding_vector=[0.1] * 768,
        keywords=["성격", "직업"],
        confidence_score=0.7,
        requires_specific_docs=["CAREER_RECOMMENDATIONS"]
    )
    
    previous_context = "이전에 성격 유형에 대해 질문했습니다."
    
    result = await context_builder.build_context(
        follow_up_question, "user1", previous_context
    )
    
    assert result.prompt_template == PromptTemplate.FOLLOW_UP
    assert "이전 맥락" in result.formatted_prompt
    assert previous_context in result.formatted_prompt


def test_select_prompt_template(context_builder):
    """Test prompt template selection logic."""
    # Personality explain
    personality_q = ProcessedQuestion(
        original_text="", cleaned_text="", 
        category=QuestionCategory.PERSONALITY, intent=QuestionIntent.EXPLAIN,
        embedding_vector=[], keywords=[], confidence_score=0.8
    )
    template = context_builder._select_prompt_template(personality_q)
    assert template == PromptTemplate.PERSONALITY_EXPLAIN
    
    # Career recommend
    career_q = ProcessedQuestion(
        original_text="", cleaned_text="",
        category=QuestionCategory.CAREER_RECOMMENDATIONS, intent=QuestionIntent.RECOMMEND,
        embedding_vector=[], keywords=[], confidence_score=0.8
    )
    template = context_builder._select_prompt_template(career_q)
    assert template == PromptTemplate.CAREER_RECOMMEND
    
    # Follow-up
    followup_q = ProcessedQuestion(
        original_text="", cleaned_text="",
        category=QuestionCategory.PERSONALITY, intent=QuestionIntent.FOLLOW_UP,
        embedding_vector=[], keywords=[], confidence_score=0.8
    )
    template = context_builder._select_prompt_template(followup_q)
    assert template == PromptTemplate.FOLLOW_UP
    
    # Default case
    unknown_q = ProcessedQuestion(
        original_text="", cleaned_text="",
        category=QuestionCategory.UNKNOWN, intent=QuestionIntent.UNKNOWN,
        embedding_vector=[], keywords=[], confidence_score=0.8
    )
    template = context_builder._select_prompt_template(unknown_q)
    assert template == PromptTemplate.DEFAULT


def test_calculate_relevance_score(context_builder, sample_processed_question):
    """Test relevance score calculation."""
    doc = MockChatDocument(
        doc_id="doc1",
        user_id="user1",
        doc_type="PERSONALITY_PROFILE",
        content="{}",
        summary_text="성격 유형에 대한 설명",
        embedding_vector=[0.1] * 768
    )
    
    # Test with matching document type and keywords
    score = context_builder._calculate_relevance_score(
        doc, sample_processed_question, 0.7
    )
    
    # Should be higher than base similarity due to type match and keyword match
    assert score > 0.7
    assert score <= 1.0


def test_extract_key_points(context_builder, sample_processed_question):
    """Test key point extraction from documents."""
    doc = MockChatDocument(
        doc_id="doc1",
        user_id="user1",
        doc_type="PERSONALITY_PROFILE",
        content=json.dumps({
            "primary_tendency": {"name": "창의형", "score": 85},
            "secondary_tendency": {"name": "분석형", "score": 78},
            "top_tendencies": [
                {"rank": 1, "name": "창의형", "score": 85},
                {"rank": 2, "name": "분석형", "score": 78},
                {"rank": 3, "name": "탐구형", "score": 72}
            ]
        }),
        summary_text="성격 프로필",
        embedding_vector=[0.1] * 768
    )
    
    key_points = context_builder._extract_key_points(doc, sample_processed_question)
    
    assert len(key_points) > 0
    assert any("창의형" in point for point in key_points)
    assert any("분석형" in point for point in key_points)


def test_create_content_summary(context_builder):
    """Test content summary creation."""
    doc = MockChatDocument(
        doc_id="doc1",
        user_id="user1",
        doc_type="PERSONALITY_PROFILE",
        content=json.dumps({
            "primary_tendency": {"name": "창의형"},
            "secondary_tendency": {"name": "분석형"}
        }),
        summary_text="",
        embedding_vector=[0.1] * 768
    )
    
    summary = context_builder._create_content_summary(doc)
    
    assert "창의형" in summary
    assert "분석형" in summary
    assert "주요 성향" in summary


def test_format_documents_for_prompt(context_builder):
    """Test document formatting for prompts."""
    doc = MockChatDocument(
        doc_id="doc1",
        user_id="user1",
        doc_type="PERSONALITY_PROFILE",
        content=json.dumps({"test": "data"}),
        summary_text="테스트 문서",
        embedding_vector=[0.1] * 768
    )
    
    retrieved_doc = RetrievedDocument(
        document=doc,
        similarity_score=0.8,
        relevance_score=0.85,
        content_summary="테스트 문서 요약",
        key_points=["포인트 1", "포인트 2"]
    )
    
    formatted = context_builder._format_documents_for_prompt([retrieved_doc])
    
    assert "검사 결과 1" in formatted
    assert "PERSONALITY_PROFILE" in formatted
    assert "테스트 문서 요약" in formatted
    assert "포인트 1" in formatted


def test_estimate_token_count(context_builder):
    """Test token count estimation."""
    short_text = "짧은 텍스트"
    long_text = "이것은 매우 긴 텍스트입니다. " * 100
    
    short_tokens = context_builder._estimate_token_count(short_text)
    long_tokens = context_builder._estimate_token_count(long_text)
    
    assert short_tokens > 0
    assert long_tokens > short_tokens
    assert isinstance(short_tokens, int)
    assert isinstance(long_tokens, int)


@pytest.mark.asyncio
async def test_context_truncation(mock_vector_search):
    """Test context truncation when exceeding token limits."""
    # Create context builder with very small token limit
    context_builder = ContextBuilder(mock_vector_search, max_context_tokens=100)
    
    question = ProcessedQuestion(
        original_text="매우 긴 질문입니다.",
        cleaned_text="매우 긴 질문입니다.",
        category=QuestionCategory.PERSONALITY,
        intent=QuestionIntent.EXPLAIN,
        embedding_vector=[0.1] * 768,
        keywords=["긴", "질문"],
        confidence_score=0.8,
        requires_specific_docs=["PERSONALITY_PROFILE"]
    )
    
    result = await context_builder.build_context(question, "user1")
    
    # Should be truncated due to small token limit
    assert result.token_count_estimate <= 100
    assert result.truncated == True


if __name__ == "__main__":
    pytest.main([__file__])