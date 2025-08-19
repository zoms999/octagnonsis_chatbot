"""
Integration tests for RAG system with preference document scenarios.

Tests the enhanced RAG system's ability to handle preference-related questions
with various document availability scenarios (complete, partial, missing).
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime

from rag.question_processor import QuestionProcessor, ProcessedQuestion, QuestionCategory, QuestionIntent
from rag.context_builder import ContextBuilder, PromptTemplate, RetrievedDocument
from rag.response_generator import ResponseGenerator, GeneratedResponse, ResponseQuality
from etl.vector_embedder import VectorEmbedder
from database.vector_search import VectorSearchService, SearchResult
from database.models import ChatDocument


class TestRAGPreferenceIntegration:
    """Test RAG system integration with preference document scenarios."""
    
    @pytest.fixture
    def mock_vector_embedder(self):
        """Mock vector embedder for testing."""
        embedder = Mock(spec=VectorEmbedder)
        embedder.generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3] * 100)  # 300-dim vector
        return embedder
    
    @pytest.fixture
    def mock_vector_search(self):
        """Mock vector search service for testing."""
        search_service = Mock(spec=VectorSearchService)
        search_service.similarity_search = AsyncMock()
        return search_service
    
    @pytest.fixture
    def question_processor(self, mock_vector_embedder):
        """Question processor instance for testing."""
        return QuestionProcessor(mock_vector_embedder)
    
    @pytest.fixture
    def context_builder(self, mock_vector_search):
        """Context builder instance for testing."""
        return ContextBuilder(mock_vector_search)
    
    @pytest.fixture
    def response_generator(self):
        """Response generator instance for testing."""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
            generator = ResponseGenerator()
            # Mock the Gemini API call
            generator._call_gemini_api = AsyncMock()
            return generator
    
    def create_preference_document(self, doc_type="PREFERENCE_ANALYSIS", completion_level="complete", 
                                 sub_type="overview", content=None, summary="선호도 분석 결과"):
        """Helper to create preference documents for testing."""
        if content is None:
            content = {
                "completion_status": "완료" if completion_level == "complete" else "부분 완료",
                "preferences": [
                    {"preference_name": "창의적 활동", "rank": 1, "description": "예술적이고 창의적인 활동을 선호"},
                    {"preference_name": "분석적 사고", "rank": 2, "description": "논리적이고 체계적인 분석을 선호"}
                ] if completion_level != "missing" else [],
                "stats": {
                    "total_image_count": 50,
                    "response_count": 45,
                    "response_rate": 90
                } if completion_level == "complete" else None
            }
        
        return ChatDocument(
            doc_id=uuid4(),
            user_id=uuid4(),
            doc_type=doc_type,
            content=content,
            summary_text=summary,
            metadata={
                "completion_level": completion_level,
                "sub_type": sub_type,
                "created_at": datetime.now().isoformat()
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def create_retrieved_document(self, document, similarity_score=0.8, relevance_score=0.9):
        """Helper to create retrieved document wrapper."""
        return RetrievedDocument(
            document=document,
            similarity_score=similarity_score,
            relevance_score=relevance_score,
            content_summary=document.summary_text,
            key_points=["주요 선호도 분석", "개인별 맞춤 결과"]
        )

    @pytest.mark.asyncio
    async def test_preference_question_detection(self, question_processor):
        """Test that preference-related questions are correctly detected."""
        test_cases = [
            ("내 선호도 분석 결과 알려줘", QuestionCategory.PREFERENCE_ANALYSIS),
            ("이미지 선호도는 어떻게 나왔어?", QuestionCategory.PREFERENCE_ANALYSIS),
            ("나는 어떤 것을 좋아하나요?", QuestionCategory.PREFERENCE_ANALYSIS),
            ("선호하는 활동이 뭐야?", QuestionCategory.PREFERENCE_ANALYSIS),
            ("취향 분석 결과 보여줘", QuestionCategory.PREFERENCE_ANALYSIS),
            ("관심사가 뭔지 알려줘", QuestionCategory.PREFERENCE_ANALYSIS),
            ("내 성격은 어때?", QuestionCategory.PERSONALITY),  # Should not be preference
        ]
        
        for question, expected_category in test_cases:
            processed = await question_processor.process_question(question, "test_user")
            assert processed.category == expected_category, f"Question '{question}' should be categorized as {expected_category}"

    @pytest.mark.asyncio
    async def test_complete_preference_documents_context(self, context_builder, mock_vector_search):
        """Test context building with complete preference documents."""
        # Create complete preference documents
        complete_doc = self.create_preference_document(
            completion_level="complete",
            sub_type="overview",
            content={
                "completion_status": "완료",
                "preference_count": 5,
                "job_count": 12,
                "top_preferences": ["창의적 활동", "분석적 사고", "협력적 업무"],
                "quality_score": 0.9,
                "stats": {"response_rate": 95}
            }
        )
        
        retrieved_docs = [self.create_retrieved_document(complete_doc)]
        
        # Mock vector search to return complete documents
        mock_vector_search.similarity_search.return_value = [
            SearchResult(document=complete_doc, similarity_score=0.9, rank=1, search_metadata={})
        ]
        
        # Create processed question
        processed_question = ProcessedQuestion(
            original_text="내 선호도 분석 결과 알려줘",
            cleaned_text="내 선호도 분석 결과 알려줘?",
            category=QuestionCategory.PREFERENCE_ANALYSIS,
            intent=QuestionIntent.EXPLAIN,
            embedding_vector=[0.1] * 300,
            keywords=["선호도", "분석", "결과"],
            confidence_score=0.8,
            requires_specific_docs=["PREFERENCE_ANALYSIS"]
        )
        
        # Build context
        context = await context_builder.build_context(processed_question, "test_user")
        
        # Verify template selection
        assert context.prompt_template == PromptTemplate.PREFERENCE_EXPLAIN
        assert len(context.retrieved_documents) == 1
        assert "완료" in context.formatted_prompt
        assert "선호도 분석 전문가" in context.formatted_prompt

    @pytest.mark.asyncio
    async def test_partial_preference_documents_context(self, context_builder, mock_vector_search):
        """Test context building with partial preference documents."""
        # Create partial preference document
        partial_doc = self.create_preference_document(
            completion_level="partial",
            sub_type="partial_data",
            content={
                "completion_status": "부분 완료",
                "stats": None,  # Missing stats
                "preferences": [{"preference_name": "창의적 활동", "rank": 1}],
                "jobs": None  # Missing jobs
            },
            summary="선호도 분석: 일부 데이터만 준비됨"
        )
        
        retrieved_docs = [self.create_retrieved_document(partial_doc)]
        
        # Mock vector search
        mock_vector_search.similarity_search.return_value = [
            SearchResult(document=partial_doc, similarity_score=0.7, rank=1, search_metadata={})
        ]
        
        processed_question = ProcessedQuestion(
            original_text="내 선호도는 어떻게 나왔어?",
            cleaned_text="내 선호도는 어떻게 나왔어?",
            category=QuestionCategory.PREFERENCE_ANALYSIS,
            intent=QuestionIntent.EXPLAIN,
            embedding_vector=[0.1] * 300,
            keywords=["선호도"],
            confidence_score=0.8,
            requires_specific_docs=["PREFERENCE_ANALYSIS"]
        )
        
        context = await context_builder.build_context(processed_question, "test_user")
        
        # Verify partial template selection
        assert context.prompt_template == PromptTemplate.PREFERENCE_PARTIAL
        assert "부분적으로만 준비된" in context.formatted_prompt
        assert "⚠️ 주의" in context.formatted_prompt

    @pytest.mark.asyncio
    async def test_missing_preference_documents_context(self, context_builder, mock_vector_search):
        """Test context building when preference documents are missing."""
        # Create non-preference documents (personality, thinking skills)
        personality_doc = ChatDocument(
            doc_id=uuid4(),
            user_id=uuid4(),
            doc_type="PERSONALITY_PROFILE",
            content={"primary_tendency": {"name": "창의형"}},
            summary_text="성격 분석 결과",
            metadata={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Mock vector search to return non-preference documents
        mock_vector_search.similarity_search.return_value = [
            SearchResult(document=personality_doc, similarity_score=0.6, rank=1, search_metadata={})
        ]
        
        processed_question = ProcessedQuestion(
            original_text="내 이미지 선호도 알려줘",
            cleaned_text="내 이미지 선호도 알려줘?",
            category=QuestionCategory.PREFERENCE_ANALYSIS,
            intent=QuestionIntent.EXPLAIN,
            embedding_vector=[0.1] * 300,
            keywords=["이미지", "선호도"],
            confidence_score=0.8,
            requires_specific_docs=["PREFERENCE_ANALYSIS"]
        )
        
        context = await context_builder.build_context(processed_question, "test_user")
        
        # Verify missing template selection
        assert context.prompt_template == PromptTemplate.PREFERENCE_MISSING
        assert "데이터가 없는 상황" in context.formatted_prompt
        assert "다른 검사 결과" in context.formatted_prompt

    @pytest.mark.asyncio
    async def test_preference_response_validation_complete_data(self, response_generator, context_builder, mock_vector_search):
        """Test response validation with complete preference data."""
        # Setup complete preference context
        complete_doc = self.create_preference_document(completion_level="complete")
        mock_vector_search.similarity_search.return_value = [
            SearchResult(document=complete_doc, similarity_score=0.9, rank=1, search_metadata={})
        ]
        
        processed_question = ProcessedQuestion(
            original_text="내 선호도 분석 결과 알려줘",
            cleaned_text="내 선호도 분석 결과 알려줘?",
            category=QuestionCategory.PREFERENCE_ANALYSIS,
            intent=QuestionIntent.EXPLAIN,
            embedding_vector=[0.1] * 300,
            keywords=["선호도", "분석"],
            confidence_score=0.8,
            requires_specific_docs=["PREFERENCE_ANALYSIS"]
        )
        
        context = await context_builder.build_context(processed_question, "test_user")
        
        # Mock Gemini response with specific preference data
        mock_response = "당신의 선호도 분석 결과, 창의적 활동이 1위로 나타났습니다. 응답률은 95%로 매우 높아 신뢰할 수 있는 결과입니다."
        response_generator._call_gemini_api.return_value = mock_response
        
        # Generate response
        result = await response_generator.generate_response(context, "test_user")
        
        # Should not add disclaimers for complete data
        assert "⚠️ 참고" not in result.content
        assert "데이터가 준비되지 않아" not in result.content
        assert result.quality_score in [ResponseQuality.GOOD, ResponseQuality.EXCELLENT]

    @pytest.mark.asyncio
    async def test_preference_response_validation_missing_data(self, response_generator, context_builder, mock_vector_search):
        """Test response validation when preference data is missing."""
        # Setup missing preference context
        personality_doc = ChatDocument(
            doc_id=uuid4(),
            user_id=uuid4(),
            doc_type="PERSONALITY_PROFILE",
            content={"primary_tendency": {"name": "창의형"}},
            summary_text="성격 분석 결과",
            metadata={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        mock_vector_search.similarity_search.return_value = [
            SearchResult(document=personality_doc, similarity_score=0.6, rank=1, search_metadata={})
        ]
        
        processed_question = ProcessedQuestion(
            original_text="내 선호도 1위가 뭐야?",
            cleaned_text="내 선호도 1위가 뭐야?",
            category=QuestionCategory.PREFERENCE_ANALYSIS,
            intent=QuestionIntent.EXPLAIN,
            embedding_vector=[0.1] * 300,
            keywords=["선호도"],
            confidence_score=0.8,
            requires_specific_docs=["PREFERENCE_ANALYSIS"]
        )
        
        context = await context_builder.build_context(processed_question, "test_user")
        
        # Mock Gemini response that might hallucinate specific data
        mock_response = "당신의 선호도 1위는 창의적 활동입니다. 선호도 점수는 85점으로 나타났습니다."
        response_generator._call_gemini_api.return_value = mock_response
        
        # Generate response
        result = await response_generator.generate_response(context, "test_user")
        
        # Should add disclaimer for missing data
        assert ("⚠️ 참고" in result.content or 
                "데이터가 현재 준비되지 않았음" in result.content or
                "대안 분석 방법" in result.content)

    @pytest.mark.asyncio
    async def test_preference_response_with_alternatives(self, response_generator, context_builder, mock_vector_search):
        """Test that responses include alternatives when preference data is missing."""
        # Setup context with no preference documents
        mock_vector_search.similarity_search.return_value = []
        
        processed_question = ProcessedQuestion(
            original_text="내가 좋아하는 활동이 뭐야?",
            cleaned_text="내가 좋아하는 활동이 뭐야?",
            category=QuestionCategory.PREFERENCE_ANALYSIS,
            intent=QuestionIntent.EXPLAIN,
            embedding_vector=[0.1] * 300,
            keywords=["좋아하는", "활동"],
            confidence_score=0.8,
            requires_specific_docs=["PREFERENCE_ANALYSIS"]
        )
        
        context = await context_builder.build_context(processed_question, "test_user")
        
        # Mock response
        mock_response = "현재 선호도 분석 데이터가 준비되지 않았습니다."
        response_generator._call_gemini_api.return_value = mock_response
        
        # Generate response
        result = await response_generator.generate_response(context, "test_user")
        
        # Should include alternative suggestions
        assert "🔍 대안 분석 방법" in result.content
        assert "성격 분석 결과를 통해" in result.content
        assert "사고능력 분석에서" in result.content

    @pytest.mark.asyncio
    async def test_preference_partial_data_enhancement(self, response_generator, context_builder, mock_vector_search):
        """Test response enhancement for partial preference data."""
        # Setup partial preference context
        partial_doc = self.create_preference_document(
            completion_level="partial",
            content={
                "completion_status": "부분 완료",
                "preferences": [{"preference_name": "창의적 활동", "rank": 1}],
                "stats": None,
                "jobs": None
            }
        )
        
        mock_vector_search.similarity_search.return_value = [
            SearchResult(document=partial_doc, similarity_score=0.7, rank=1, search_metadata={})
        ]
        
        processed_question = ProcessedQuestion(
            original_text="내 선호도 분석해줘",
            cleaned_text="내 선호도 분석해줘?",
            category=QuestionCategory.PREFERENCE_ANALYSIS,
            intent=QuestionIntent.ANALYZE,
            embedding_vector=[0.1] * 300,
            keywords=["선호도", "분석"],
            confidence_score=0.8,
            requires_specific_docs=["PREFERENCE_ANALYSIS"]
        )
        
        context = await context_builder.build_context(processed_question, "test_user")
        
        # Mock response
        mock_response = "부분적인 데이터를 바탕으로 분석하면, 창의적 활동에 대한 선호가 높게 나타납니다."
        response_generator._call_gemini_api.return_value = mock_response
        
        # Generate response
        result = await response_generator.generate_response(context, "test_user")
        
        # Should include enhancement for partial data
        assert ("💡 추가 인사이트를 위해" in result.content or 
                "💡 완전한 선호도 분석을 위한 팁" in result.content)
        assert ("다른 분석 결과도 함께 확인" in result.content or
                "다른 검사 결과(성격, 사고능력, 역량)와 함께" in result.content)

    @pytest.mark.asyncio
    async def test_end_to_end_preference_workflow(self, question_processor, context_builder, response_generator, mock_vector_search):
        """Test complete end-to-end workflow for preference questions."""
        # Setup complete preference document
        complete_doc = self.create_preference_document(
            completion_level="complete",
            content={
                "completion_status": "완료",
                "preferences": [
                    {"preference_name": "창의적 활동", "rank": 1, "description": "예술적 창작 활동 선호"},
                    {"preference_name": "분석적 사고", "rank": 2, "description": "논리적 분석 업무 선호"}
                ],
                "stats": {"response_rate": 92, "total_image_count": 50},
                "jobs": [
                    {"job_name": "디자이너", "preference_match": "창의적 활동"},
                    {"job_name": "데이터 분석가", "preference_match": "분석적 사고"}
                ]
            }
        )
        
        mock_vector_search.similarity_search.return_value = [
            SearchResult(document=complete_doc, similarity_score=0.9, rank=1, search_metadata={})
        ]
        
        # Step 1: Process question
        question = "내 선호도 분석 결과와 추천 직업 알려줘"
        processed_question = await question_processor.process_question(question, "test_user")
        
        assert processed_question.category == QuestionCategory.PREFERENCE_ANALYSIS
        assert processed_question.intent in [QuestionIntent.EXPLAIN, QuestionIntent.RECOMMEND]
        
        # Step 2: Build context
        context = await context_builder.build_context(processed_question, "test_user")
        
        assert context.prompt_template == PromptTemplate.PREFERENCE_EXPLAIN
        assert len(context.retrieved_documents) == 1
        assert "선호도 분석 전문가" in context.formatted_prompt
        
        # Step 3: Generate response
        mock_response = "분석 결과 창의적 활동(1위)과 분석적 사고(2위)에 대한 선호가 높습니다. 추천 직업으로는 디자이너와 데이터 분석가가 있습니다."
        response_generator._call_gemini_api.return_value = mock_response
        
        result = await response_generator.generate_response(context, "test_user")
        
        # Verify final result
        assert result.quality_score in [ResponseQuality.GOOD, ResponseQuality.EXCELLENT]
        assert result.confidence_score > 0.7
        assert "창의적 활동" in result.content
        assert "분석적 사고" in result.content
        assert len(result.retrieved_doc_ids) == 1

    @pytest.mark.asyncio
    async def test_preference_question_with_follow_up_context(self, question_processor, context_builder, mock_vector_search):
        """Test preference questions with follow-up context."""
        # Setup preference document
        pref_doc = self.create_preference_document()
        mock_vector_search.similarity_search.return_value = [
            SearchResult(document=pref_doc, similarity_score=0.8, rank=1, search_metadata={})
        ]
        
        # First question
        first_question = await question_processor.process_question("내 선호도 분석 결과 알려줘", "test_user")
        
        # Follow-up question
        follow_up_question = await question_processor.process_question("그럼 추천 직업은 뭐야?", "test_user")
        
        # Build context with previous context
        context = await context_builder.build_context(
            follow_up_question, 
            "test_user", 
            previous_context="이전에 선호도 분석에 대해 질문했습니다."
        )
        
        # Should handle follow-up appropriately - either as follow-up or career recommendation with context
        assert ("이전 맥락" in context.formatted_prompt or 
                context.prompt_template == PromptTemplate.FOLLOW_UP or
                (context.prompt_template == PromptTemplate.CAREER_RECOMMEND and context.context_metadata["has_previous_context"]))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])