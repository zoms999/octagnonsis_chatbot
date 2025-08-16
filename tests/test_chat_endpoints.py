"""
Tests for chat endpoints
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from main import app
from database.models import ChatUser, ChatConversation, ChatDocument
from api.chat_endpoints import get_async_session, get_rag_components

# Test client
client = TestClient(app)

# Mock data
TEST_USER_ID = str(uuid.uuid4())
TEST_CONVERSATION_ID = str(uuid.uuid4())

@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = Mock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session

@pytest.fixture
def mock_user():
    """Mock user object"""
    user = Mock(spec=ChatUser)
    user.user_id = uuid.UUID(TEST_USER_ID)
    user.anp_seq = 12345
    user.name = "Test User"
    user.email = "test@example.com"
    return user

@pytest.fixture
def mock_conversation():
    """Mock conversation object"""
    conversation = Mock(spec=ChatConversation)
    conversation.conversation_id = uuid.UUID(TEST_CONVERSATION_ID)
    conversation.user_id = uuid.UUID(TEST_USER_ID)
    conversation.question = "What is my personality type?"
    conversation.response = "Based on your test results, you have a creative personality type..."
    conversation.retrieved_doc_ids = []
    conversation.created_at = "2024-01-01T12:00:00"
    return conversation

@pytest.fixture
def mock_rag_components():
    """Mock RAG components"""
    question_processor = Mock()
    question_processor.process_question = AsyncMock()
    
    context_builder = Mock()
    context_builder.build_context = AsyncMock()
    
    response_generator = Mock()
    response_generator.generate_response = AsyncMock()
    
    document_repository = Mock()
    
    return (question_processor, context_builder, response_generator, document_repository)

class TestChatEndpoints:
    """Test chat endpoints functionality"""
    
    def test_health_check(self):
        """Test chat health check endpoint"""
        with patch('api.chat_endpoints.get_async_session') as mock_get_session:
            mock_session = Mock()
            mock_session.execute = AsyncMock()
            mock_get_session.return_value = mock_session
            
            response = client.get("/api/chat/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "components" in data
    
    @patch('api.chat_endpoints.get_async_session')
    @patch('api.chat_endpoints.get_rag_components')
    @patch('api.chat_endpoints.get_user_by_id')
    @patch('api.chat_endpoints.check_rate_limit')
    def test_ask_question_success(
        self, 
        mock_rate_limit,
        mock_get_user,
        mock_rag_components,
        mock_get_session,
        mock_user,
        mock_conversation
    ):
        """Test successful question processing"""
        # Setup mocks
        mock_rate_limit.return_value = True
        mock_get_user.return_value = mock_user
        
        # Mock RAG components
        question_processor = Mock()
        processed_question = Mock()
        processed_question.original_text = "What is my personality type?"
        question_processor.process_question = AsyncMock(return_value=processed_question)
        
        context_builder = Mock()
        context = Mock()
        context.retrieved_documents = []
        context_builder.build_context = AsyncMock(return_value=context)
        
        response_generator = Mock()
        generated_response = Mock()
        generated_response.content = "You have a creative personality type..."
        generated_response.confidence_score = 0.85
        response_generator.generate_response = AsyncMock(return_value=generated_response)
        
        document_repository = Mock()
        
        mock_rag_components.return_value = (
            question_processor, context_builder, response_generator, document_repository
        )
        
        # Mock database session
        mock_session = Mock()
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_get_session.return_value = mock_session
        
        # Mock conversation creation
        with patch('api.chat_endpoints.ChatConversation') as mock_conv_class:
            mock_conv_class.return_value = mock_conversation
            
            # Make request
            response = client.post(
                "/api/chat/question",
                json={
                    "user_id": TEST_USER_ID,
                    "question": "What is my personality type?"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "conversation_id" in data
            assert "response" in data
            assert data["user_id"] == TEST_USER_ID
            assert data["question"] == "What is my personality type?"
    
    def test_ask_question_invalid_request(self):
        """Test question endpoint with invalid request"""
        # Empty question
        response = client.post(
            "/api/chat/question",
            json={
                "user_id": TEST_USER_ID,
                "question": ""
            }
        )
        assert response.status_code == 422
        
        # Missing user_id
        response = client.post(
            "/api/chat/question",
            json={
                "question": "What is my personality type?"
            }
        )
        assert response.status_code == 422
    
    @patch('api.chat_endpoints.check_rate_limit')
    def test_ask_question_rate_limit(self, mock_rate_limit):
        """Test rate limiting"""
        mock_rate_limit.return_value = False
        
        response = client.post(
            "/api/chat/question",
            json={
                "user_id": TEST_USER_ID,
                "question": "What is my personality type?"
            }
        )
        assert response.status_code == 429
        assert "rate limit" in response.json()["detail"].lower()
    
    @patch('api.chat_endpoints.get_async_session')
    @patch('api.chat_endpoints.get_user_by_id')
    def test_get_conversation_history_success(
        self, 
        mock_get_user,
        mock_get_session,
        mock_user
    ):
        """Test successful conversation history retrieval"""
        mock_get_user.return_value = mock_user
        
        # Mock database session and results
        mock_session = Mock()
        
        # Mock count query result
        count_result = Mock()
        count_result.scalars.return_value.all.return_value = [1, 2, 3]  # 3 conversations
        
        # Mock conversations query result
        conversations_result = Mock()
        mock_conversations = [
            Mock(
                conversation_id=uuid.uuid4(),
                question="Question 1",
                response="Response 1",
                created_at="2024-01-01T12:00:00",
                retrieved_doc_ids=[]
            ),
            Mock(
                conversation_id=uuid.uuid4(),
                question="Question 2", 
                response="Response 2",
                created_at="2024-01-01T11:00:00",
                retrieved_doc_ids=[]
            )
        ]
        conversations_result.scalars.return_value.all.return_value = mock_conversations
        
        # Setup execute to return different results for different queries
        mock_session.execute = AsyncMock(side_effect=[count_result, conversations_result])
        mock_get_session.return_value = mock_session
        
        response = client.get(f"/api/chat/history/{TEST_USER_ID}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == TEST_USER_ID
        assert "conversations" in data
        assert data["total_count"] == 3
        assert len(data["conversations"]) == 2
    
    def test_get_conversation_history_invalid_params(self):
        """Test conversation history with invalid parameters"""
        # Invalid limit
        response = client.get(f"/api/chat/history/{TEST_USER_ID}?limit=0")
        assert response.status_code == 400
        
        response = client.get(f"/api/chat/history/{TEST_USER_ID}?limit=101")
        assert response.status_code == 400
        
        # Invalid offset
        response = client.get(f"/api/chat/history/{TEST_USER_ID}?offset=-1")
        assert response.status_code == 400

def test_rate_limiting():
    """Test rate limiting functionality"""
    from api.chat_endpoints import check_rate_limit, user_request_counts
    
    # Clear any existing data
    user_request_counts.clear()
    
    test_user = "test_user_rate_limit"
    
    # Should allow first request
    assert check_rate_limit(test_user) == True
    
    # Simulate many requests
    for _ in range(29):  # 29 more requests (30 total, which is the limit)
        check_rate_limit(test_user)
    
    # 31st request should be blocked
    assert check_rate_limit(test_user) == False

if __name__ == "__main__":
    pytest.main([__file__])