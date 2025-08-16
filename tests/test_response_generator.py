"""
Tests for the ResponseGenerator class.

Tests LLM response generation, prompt engineering, response post-processing,
validation, and conversation memory management.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from uuid import uuid4

from rag.response_generator import (
    ResponseGenerator, GeneratedResponse, ResponseQuality, 
    ConversationMemory
)
from rag.context_builder import ConstructedContext, RetrievedDocument, PromptTemplate
from rag.question_processor import ProcessedQuestion, QuestionCategory, QuestionIntent, ConversationContext
from database.models import ChatDocument


class TestResponseGenerator:
    """Test cases for ResponseGenerator class."""
    
    @pytest.fixture
    def mock_api_key(self):
        """Mock API key for testing."""
        return "test_api_key_12345"
    
    @pytest.fixture
    def response_generator(self, mock_api_key):
        """Create ResponseGenerator instance for testing."""
        with patch.dict('os.environ', {'GEMINI_API_KEY': mock_api_key}):
            with patch('google.generativeai.configure'):
                with patch('google.generativeai.GenerativeModel'):
                    generator = ResponseGenerator(api_key=mock_api_key)
                    return generator
    
    @pytest.fixture
    def sample_chat_document(self):
        """Create sample ChatDocument for testing."""
        return ChatDocument(
            doc_id=uuid4(),
            user_id=uuid4(),
            doc_type="PERSONALITY_PROFILE",
            content={
                "primary_tendency": {
                    "name": "창의형",
                    "code": "tnd12000",
                    "explanation": "새로운 아이디어를 창출하고 혁신적인 해결책을 찾는 성향",
                    "rank": 1,
                    "percentage_in_total": 15.2
                },
                "secondary_tendency": {
                    "name": "분석형", 
                    "code": "tnd21000",
                    "explanation": "논리적 사고를 통해 문제를 체계적으로 분석하는 성향",
                    "rank": 2,
                    "percentage_in_total": 12.8
                },
                "top_tendencies": [
                    {"rank": 1, "name": "창의형", "score": 85},
                    {"rank": 2, "name": "분석형", "score": 78},
                    {"rank": 3, "name": "탐구형", "score": 72}
                ]
            },
            summary_text="주요 성향: 창의형, 보조 성향: 분석형",
            embedding_vector=[0.1] * 768,
            doc_metadata={}
        )
    
    @pytest.fixture
    def sample_retrieved_document(self, sample_chat_document):
        """Create sample RetrievedDocument for testing."""
        return RetrievedDocument(
            document=sample_chat_document,
            similarity_score=0.85,
            relevance_score=0.90,
            content_summary="주요 성향: 창의형, 보조 성향: 분석형",
            key_points=[
                "주요 성향: 창의형",
                "보조 성향: 분석형", 
                "1위: 창의형 (85점)"
            ]
        )
    
    @pytest.fixture
    def sample_constructed_context(self, sample_retrieved_document):
        """Create sample ConstructedContext for testing."""
        return ConstructedContext(
            user_question="내 성격 유형에 대해 설명해주세요",
            retrieved_documents=[sample_retrieved_document],
            prompt_template=PromptTemplate.PERSONALITY_EXPLAIN,
            formatted_prompt="당신은 적성검사 결과를 분석하고 설명하는 전문 상담사입니다...",
            context_metadata={
                "question_category": "personality",
                "question_intent": "explain",
                "confidence_score": 0.85,
                "num_documents": 1,
                "has_previous_context": False
            },
            token_count_estimate=500,
            truncated=False
        )
    
    def test_initialization_with_api_key(self, mock_api_key):
        """Test ResponseGenerator initialization with API key."""
        with patch('google.generativeai.configure') as mock_configure:
            with patch('google.generativeai.GenerativeModel') as mock_model:
                generator = ResponseGenerator(api_key=mock_api_key)
                
                mock_configure.assert_called_once_with(api_key=mock_api_key)
                mock_model.assert_called_once()
                assert generator.model_name == "gemini-2.0-flash"
                assert isinstance(generator.conversation_memories, dict)
    
    def test_initialization_with_env_var(self, mock_api_key):
        """Test ResponseGenerator initialization with environment variable."""
        with patch.dict('os.environ', {'GEMINI_API_KEY': mock_api_key}):
            with patch('google.generativeai.configure') as mock_configure:
                with patch('google.generativeai.GenerativeModel'):
                    generator = ResponseGenerator()
                    mock_configure.assert_called_once_with(api_key=mock_api_key)
    
    def test_initialization_without_api_key(self):
        """Test ResponseGenerator initialization fails without API key."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                ResponseGenerator()
    
    @pytest.mark.asyncio
    async def test_generate_response_success(self, response_generator, sample_constructed_context):
        """Test successful response generation."""
        mock_response_text = "당신은 창의형 성격으로, 새로운 아이디어를 잘 만들어내는 특징이 있습니다. 이는 전체 인구의 15.2%에 해당하는 특별한 성향입니다."
        
        # Mock the Gemini API call
        with patch.object(response_generator, '_call_gemini_api', return_value=mock_response_text):
            response = await response_generator.generate_response(
                sample_constructed_context, 
                "user123"
            )
            
            assert isinstance(response, GeneratedResponse)
            assert response.content == mock_response_text
            assert isinstance(response.quality_score, ResponseQuality)
            assert 0 <= response.confidence_score <= 1
            assert response.processing_time > 0
            assert len(response.retrieved_doc_ids) == 1
    
    @pytest.mark.asyncio
    async def test_generate_response_with_conversation_context(self, response_generator, sample_constructed_context):
        """Test response generation with conversation context."""
        mock_response_text = "앞서 말씀드린 창의형 성향과 관련하여, 추가로 설명드리면..."
        
        conversation_context = ConversationContext(
            previous_questions=["내 성격이 뭐야?"],
            previous_responses=["당신은 창의형입니다."],
            current_topic="personality",
            follow_up_count=2
        )
        
        with patch.object(response_generator, '_call_gemini_api', return_value=mock_response_text):
            response = await response_generator.generate_response(
                sample_constructed_context,
                "user123", 
                conversation_context
            )
            
            assert response.conversation_context is not None
            assert "user123" in response_generator.conversation_memories
    
    @pytest.mark.asyncio
    async def test_call_gemini_api_success(self, response_generator):
        """Test successful Gemini API call."""
        mock_response = Mock()
        mock_candidate = Mock()
        mock_content = Mock()
        mock_part = Mock()
        mock_part.text = "테스트 응답입니다."
        mock_content.parts = [mock_part]
        mock_candidate.content = mock_content
        mock_response.candidates = [mock_candidate]
        
        with patch.object(response_generator.model, 'generate_content', return_value=mock_response):
            result = await response_generator._call_gemini_api("테스트 프롬프트")
            assert result == "테스트 응답입니다."
    
    @pytest.mark.asyncio
    async def test_call_gemini_api_no_response(self, response_generator):
        """Test Gemini API call with no valid response."""
        mock_response = Mock()
        mock_response.candidates = []
        
        with patch.object(response_generator.model, 'generate_content', return_value=mock_response):
            result = await response_generator._call_gemini_api("테스트 프롬프트")
            assert "죄송합니다" in result
    
    @pytest.mark.asyncio
    async def test_post_process_response(self, response_generator, sample_constructed_context):
        """Test response post-processing."""
        raw_response = "**당신은** *창의형* 성격입니다.   점수는  85점  입니다."
        memory = ConversationMemory(
            user_id="user123",
            conversation_history=[],
            current_context="personality"
        )
        
        processed = await response_generator._post_process_response(
            raw_response, sample_constructed_context, memory
        )
        
        # Check that markdown formatting is removed
        assert "**" not in processed
        assert "*" not in processed
        # Check that spacing is fixed
        assert "85점입니다" in processed or "85점 입니다" in processed
    
    def test_fix_korean_formatting(self, response_generator):
        """Test Korean text formatting fixes."""
        text = "안녕하세요 .   저는    홍길동  입니다 ."
        fixed = response_generator._fix_korean_formatting(text)
        assert fixed == "안녕하세요. 저는 홍길동입니다."
        
        # Test number formatting
        text = "점수는  85  점입니다"
        fixed = response_generator._fix_korean_formatting(text)
        assert fixed == "점수는 85점입니다"
    
    @pytest.mark.asyncio
    async def test_enhance_with_statistical_context(self, response_generator, sample_constructed_context):
        """Test enhancement with statistical context."""
        response = "당신은 창의형 성격입니다."
        
        enhanced = await response_generator._enhance_with_statistical_context(
            response, sample_constructed_context
        )
        
        # Should add statistical context note
        assert "백분위" in enhanced or "순위" in enhanced or "점수" in enhanced
    
    @pytest.mark.asyncio
    async def test_enhance_with_learning_connections(self, response_generator, sample_constructed_context):
        """Test enhancement with learning connections."""
        # Modify context to be learning-related
        sample_constructed_context.user_question = "내 학습 방법에 대해 알려주세요"
        response = "당신은 창의형 성격입니다."
        
        enhanced = await response_generator._enhance_with_learning_connections(
            response, sample_constructed_context
        )
        
        # Should add learning connection if personality and thinking skills data available
        assert len(enhanced) >= len(response)  # At minimum, should not shrink
    
    def test_validate_response_content(self, response_generator):
        """Test response content validation."""
        # Valid response
        valid_response = "당신은 창의형 성격으로 새로운 아이디어를 잘 만들어냅니다."
        assert response_generator._validate_response_content(valid_response) == True
        
        # Too short
        short_response = "네"
        assert response_generator._validate_response_content(short_response) == False
        
        # No Korean content
        no_korean = "You are creative type personality."
        assert response_generator._validate_response_content(no_korean) == False
        
        # Too many incomplete responses
        incomplete = "죄송합니다. 모르겠습니다. 알 수 없습니다. 미안합니다."
        assert response_generator._validate_response_content(incomplete) == False
    
    def test_assess_response_quality(self, response_generator, sample_constructed_context):
        """Test response quality assessment."""
        # Excellent response
        excellent_response = (
            "당신은 창의형 성격으로 전체 인구의 15.2%에 해당하는 특별한 성향을 가지고 있습니다. "
            "1위 창의형(85점), 2위 분석형(78점)으로 나타났으며, 이는 새로운 아이디어를 창출하고 "
            "논리적 분석을 통해 문제를 해결하는 능력이 뛰어나다는 것을 의미합니다."
        )
        quality = response_generator._assess_response_quality(excellent_response, sample_constructed_context)
        assert quality in [ResponseQuality.EXCELLENT, ResponseQuality.GOOD]
        
        # Poor response
        poor_response = "네, 그렇습니다."
        quality = response_generator._assess_response_quality(poor_response, sample_constructed_context)
        assert quality == ResponseQuality.POOR
    
    def test_calculate_confidence_score(self, response_generator, sample_constructed_context):
        """Test confidence score calculation."""
        response = "당신은 창의형 성격입니다."
        
        # Test with excellent quality
        confidence = response_generator._calculate_confidence_score(
            response, sample_constructed_context, ResponseQuality.EXCELLENT
        )
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be high for excellent quality
        
        # Test with poor quality
        confidence = response_generator._calculate_confidence_score(
            response, sample_constructed_context, ResponseQuality.POOR
        )
        assert 0.0 <= confidence <= 1.0
        assert confidence < 0.5  # Should be low for poor quality
    
    @pytest.mark.asyncio
    async def test_update_conversation_memory(self, response_generator, sample_constructed_context):
        """Test conversation memory updates."""
        user_id = "user123"
        
        memory = await response_generator._update_conversation_memory(
            user_id, sample_constructed_context
        )
        
        assert memory.user_id == user_id
        assert memory.current_context == "personality"
        assert memory.last_topic == "personality"
        assert memory.follow_up_count == 1
        assert user_id in response_generator.conversation_memories
    
    def test_extract_topic_from_question(self, response_generator):
        """Test topic extraction from questions."""
        # Personality topic
        assert response_generator._extract_topic_from_question("내 성격이 어떤가요?") == "personality"
        
        # Career topic
        assert response_generator._extract_topic_from_question("추천 직업이 뭐예요?") == "career"
        
        # Thinking skills topic
        assert response_generator._extract_topic_from_question("내 사고 능력은?") == "thinking"
        
        # Learning topic
        assert response_generator._extract_topic_from_question("어떻게 공부해야 하나요?") == "learning"
        
        # General topic
        assert response_generator._extract_topic_from_question("안녕하세요") == "general"
    
    @pytest.mark.asyncio
    async def test_enhance_prompt_with_memory(self, response_generator):
        """Test prompt enhancement with conversation memory."""
        original_prompt = "당신은 전문 상담사입니다. 질문에 답변해주세요."
        
        # Create memory with conversation history
        memory = ConversationMemory(
            user_id="user123",
            conversation_history=[
                type('Conv', (), {
                    'question': '내 성격이 뭐야?',
                    'response': '당신은 창의형입니다.',
                    'created_at': datetime.now()
                })()
            ],
            follow_up_count=2
        )
        
        enhanced = await response_generator._enhance_prompt_with_memory(original_prompt, memory)
        
        # Should include previous conversation context
        assert "이전 대화 맥락" in enhanced
        assert "내 성격이 뭐야?" in enhanced
    
    @pytest.mark.asyncio
    async def test_generate_fallback_response(self, response_generator, sample_constructed_context):
        """Test fallback response generation."""
        # Test personality-related fallback
        sample_constructed_context.user_question = "내 성격에 대해 알려주세요"
        fallback = await response_generator._generate_fallback_response(sample_constructed_context)
        assert "성격 분석" in fallback
        
        # Test career-related fallback
        sample_constructed_context.user_question = "추천 직업이 뭐예요?"
        fallback = await response_generator._generate_fallback_response(sample_constructed_context)
        assert "진로 추천" in fallback
        
        # Test general fallback
        sample_constructed_context.user_question = "안녕하세요"
        fallback = await response_generator._generate_fallback_response(sample_constructed_context)
        assert "답변을 생성하는데 문제" in fallback
    
    def test_conversation_memory_management(self, response_generator):
        """Test conversation memory management methods."""
        user_id = "user123"
        
        # Initially no memory
        assert response_generator.get_conversation_memory(user_id) is None
        
        # Create memory
        memory = ConversationMemory(user_id=user_id, conversation_history=[])
        response_generator.conversation_memories[user_id] = memory
        
        # Get memory
        retrieved = response_generator.get_conversation_memory(user_id)
        assert retrieved is not None
        assert retrieved.user_id == user_id
        
        # Clear memory
        response_generator.clear_conversation_memory(user_id)
        assert response_generator.get_conversation_memory(user_id) is None
    
    def test_get_model_info(self, response_generator):
        """Test model information retrieval."""
        info = response_generator.get_model_info()
        
        assert "model_name" in info
        assert "generation_config" in info
        assert "active_conversations" in info
        assert info["model_name"] == "gemini-2.0-flash"
        assert isinstance(info["generation_config"], dict)
        assert isinstance(info["active_conversations"], int)
    
    @pytest.mark.asyncio
    async def test_error_handling_in_generate_response(self, response_generator, sample_constructed_context):
        """Test error handling in response generation."""
        # Mock API call to raise exception
        with patch.object(response_generator, '_call_gemini_api', side_effect=Exception("API Error")):
            response = await response_generator.generate_response(
                sample_constructed_context,
                "user123"
            )
            
            # Should return fallback response
            assert response.quality_score == ResponseQuality.POOR
            assert response.confidence_score == 0.1
            assert "문제가 있습니다" in response.content
    
    @pytest.mark.asyncio
    async def test_store_conversation_turn(self, response_generator, sample_constructed_context):
        """Test storing conversation turns."""
        user_id = "user123"
        
        # Create initial memory
        memory = ConversationMemory(user_id=user_id, conversation_history=[])
        response_generator.conversation_memories[user_id] = memory
        
        # Create mock response
        mock_response = GeneratedResponse(
            content="테스트 응답",
            quality_score=ResponseQuality.GOOD,
            confidence_score=0.8,
            processing_time=1.0,
            retrieved_doc_ids=["doc1"]
        )
        
        # Store conversation turn
        await response_generator._store_conversation_turn(user_id, sample_constructed_context, mock_response)
        
        # Check that conversation was stored
        updated_memory = response_generator.get_conversation_memory(user_id)
        assert len(updated_memory.conversation_history) == 1
        assert updated_memory.conversation_history[0].question == sample_constructed_context.user_question
        assert updated_memory.conversation_history[0].response == mock_response.content


if __name__ == "__main__":
    pytest.main([__file__])