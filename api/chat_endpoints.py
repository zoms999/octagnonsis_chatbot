"""
FastAPI Endpoints for Chat Interactions
API endpoints for user queries, conversation history, and real-time chat
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID
import asyncio
import json
import uuid

from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
# Note: Redis dependency removed - using database-based rate limiting

from database.connection import get_async_session, db_manager
from database.models import ChatUser, ChatConversation, ChatDocument, ChatFeedback
from api.auth_endpoints import get_current_user
from database.repositories import DocumentRepository
from database.cache import DocumentCache
from database.vector_search import VectorSearchService
from rag.question_processor import QuestionProcessor, ConversationContext, ProcessedQuestion
from rag.context_builder import ContextBuilder
from rag.response_generator import ResponseGenerator
from etl.vector_embedder import VectorEmbedder
from monitoring.metrics import inc as metrics_inc, observe as metrics_observe

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/chat", tags=["Chat Interactions"])

# Pydantic models for API
class ChatQuestionRequest(BaseModel):
    """Chat question request model"""
    user_id: str = Field(..., description="User identifier")
    question: str = Field(..., min_length=1, max_length=500, description="User question")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID for context")
    
    @validator('question')
    def validate_question(cls, v):
        if not v or not v.strip():
            raise ValueError('Question cannot be empty')
        return v.strip()
    
    @validator('user_id')
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError('user_id cannot be empty')
        return v.strip()

class ChatResponse(BaseModel):
    """Chat response model"""
    conversation_id: str
    user_id: str
    question: str
    response: str
    retrieved_documents: List[Dict[str, Any]]
    processing_time: float
    confidence_score: float
    created_at: str
    # Analytics/feedback
    ab_variant: Optional[str] = None

class ConversationHistoryItem(BaseModel):
    """Single conversation history item"""
    conversation_id: str
    question: str
    response: str
    created_at: str
    retrieved_doc_count: int

class ConversationHistoryResponse(BaseModel):
    """Conversation history response model"""
    user_id: str
    conversations: List[ConversationHistoryItem]
    total_count: int
    has_more: bool

class WebSocketMessage(BaseModel):
    """WebSocket message model"""
    type: str  # 'question', 'response', 'error', 'status'
    data: Dict[str, Any]
    timestamp: str

class FeedbackRequest(BaseModel):
    conversation_id: str
    user_id: str
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    helpful: Optional[bool] = None
    comment: Optional[str] = Field(default=None, max_length=1000)
    tags: Optional[List[str]] = None

# Rate limiting storage (in-memory for now, will be database-based in production)
user_request_counts = {}
RATE_LIMIT_REQUESTS = 30  # requests per minute
RATE_LIMIT_WINDOW = 60  # seconds

    

# Dependency to get RAG components
async def get_rag_components() -> tuple:
    """Get initialized RAG components"""
    try:
        # Initialize vector embedder (singleton for cache reuse)
        vector_embedder = VectorEmbedder.instance()
        
        # Initialize question processor
        question_processor = QuestionProcessor(vector_embedder)
        
        # These components will be initialized with sessions when needed
        # Initialize response generator (doesn't need DB session)
        response_generator = ResponseGenerator()
        
        return (
            question_processor,
            response_generator
        )
        
    except Exception as e:
        logger.error(f"Failed to initialize RAG components: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service initialization failed"
        )

def check_rate_limit(user_id: str) -> bool:
    """Check if user has exceeded rate limit"""
    current_time = datetime.now().timestamp()
    
    if user_id not in user_request_counts:
        user_request_counts[user_id] = []
    
    # Remove old requests outside the window
    user_request_counts[user_id] = [
        req_time for req_time in user_request_counts[user_id]
        if current_time - req_time < RATE_LIMIT_WINDOW
    ]
    
    # Check if limit exceeded
    if len(user_request_counts[user_id]) >= RATE_LIMIT_REQUESTS:
        return False
    
    # Add current request
    user_request_counts[user_id].append(current_time)
    return True

async def get_user_by_id(user_id: str, db: AsyncSession) -> ChatUser:
    """Get user by ID, handling both UUID and string formats"""
    try:
        # Try to parse as UUID first
        if len(user_id) == 32 and '-' not in user_id:
            # Add dashes to make it a proper UUID format
            formatted_uuid = f"{user_id[:8]}-{user_id[8:12]}-{user_id[12:16]}-{user_id[16:20]}-{user_id[20:]}"
            user_uuid = UUID(formatted_uuid)
        else:
            user_uuid = UUID(user_id)
        
        result = await db.execute(select(ChatUser).where(ChatUser.user_id == user_uuid))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        
        return user
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user ID format: {user_id}"
        )

@router.post(
    "/feedback",
    summary="Submit feedback for a conversation",
    description="Collect user satisfaction feedback and comments"
)
async def submit_feedback(
    payload: FeedbackRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        async with db_manager.get_async_session() as db:
            # Verify authenticated user matches feedback user
            if current_user["user_id"] != payload.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You can only submit feedback for your own conversations"
                )
            
            feedback = ChatFeedback(
                conversation_id=UUID(payload.conversation_id),
                user_id=UUID(payload.user_id),
                rating=payload.rating,
                helpful=payload.helpful,
                comment=payload.comment,
                tags=payload.tags or []
            )
            db.add(feedback)
            await db.commit()
            return {"status": "ok"}
    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}")
        raise HTTPException(status_code=500, detail="피드백 저장에 실패했습니다.")

@router.post(
    "/question",
    response_model=ChatResponse,
    summary="Ask Question",
    description="Submit a question about aptitude test results and get an AI-generated response"
)
async def ask_question(
    request: ChatQuestionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    rag_components: tuple = Depends(get_rag_components)
) -> ChatResponse:
    """
    Process a user question and generate a response using RAG.
    
    This endpoint processes natural language questions about aptitude test results,
    retrieves relevant documents, and generates contextual responses using LLM.
    
    Args:
        request: Chat question request
        db: Database session
        rag_components: RAG service components
        
    Returns:
        Generated response with context and metadata
        
    Raises:
        HTTPException: If processing fails or rate limit exceeded
    """
    start_time = datetime.now()
    
    try:
        # Metrics: request received
        await metrics_inc("chat_requests_total")
        # Check rate limiting
        if not check_rate_limit(request.user_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please wait before making another request."
            )
        
        # Get database session
        async with db_manager.get_async_session() as db:
            # Verify authenticated user matches request user
            if current_user["user_id"] != request.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You can only ask questions for your own account"
                )
            
            # Verify user exists
            user = await get_user_by_id(request.user_id, db)
            
            # Check if user has any documents
            from sqlalchemy import func
            doc_count_result = await db.execute(
                select(func.count(ChatDocument.doc_id))
                .where(ChatDocument.user_id == user.user_id)
            )
            doc_count = doc_count_result.scalar()
            
            if doc_count == 0:
                logger.warning(f"User {request.user_id} has no documents in the system")
                return ChatResponse(
                    conversation_id=str(uuid.uuid4()),
                    user_id=request.user_id,
                    question=request.question,
                    response="안녕하세요! 적성검사 결과를 찾을 수 없습니다. 적성검사를 먼저 완료해 주시기 바랍니다. 검사 완료 후 다시 질문해 주세요.",
                    retrieved_documents=[],
                    processing_time=(datetime.now() - start_time).total_seconds(),
                    confidence_score=0.0,
                    created_at=datetime.now().isoformat(),
                    ab_variant=None
                )
            
            logger.info(f"User {request.user_id} has {doc_count} documents in the system")
            
            # Unpack RAG components
            question_processor, response_generator = rag_components
            
            # Initialize database-dependent components
            vector_search_service = VectorSearchService(db)
            context_builder = ContextBuilder(vector_search_service)
            document_repository = DocumentRepository(db, DocumentRepository.get_global_cache())
        
            # Get conversation context if conversation_id provided
            conversation_context = None
            if request.conversation_id:
                try:
                    conv_uuid = UUID(request.conversation_id)
                    result = await db.execute(
                        select(ChatConversation)
                        .where(ChatConversation.user_id == user.user_id)
                        .order_by(desc(ChatConversation.created_at))
                        .limit(5)
                    )
                    recent_conversations = result.scalars().all()
                    
                    if recent_conversations:
                        conversation_context = ConversationContext(
                            user_id=request.user_id,
                            previous_questions=[conv.question for conv in recent_conversations],
                            previous_categories=[],  # Would need to store this
                            conversation_depth=len(recent_conversations)
                        )
                except ValueError:
                    logger.warning(f"Invalid conversation_id format: {request.conversation_id}")
            
            # Process the question
            q_start = datetime.now()
            processed_question = await question_processor.process_question(
                request.question,
                request.user_id,
                conversation_context
            )
            
            # Build context from retrieved documents
            context = await context_builder.build_context(
                processed_question,
                request.user_id,
                conversation_context.previous_questions[-1] if conversation_context else None
            )
            
            # Log context building results for debugging
            logger.info(
                f"Context built for user {request.user_id}: "
                f"retrieved_docs={len(context.retrieved_documents)}, "
                f"question_category={context.context_metadata.get('question_category')}, "
                f"question_intent={context.context_metadata.get('question_intent')}"
            )
            
            # Generate response
            response = await response_generator.generate_response(
                context,
                request.user_id,
                conversation_context
            )
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            await metrics_observe("chat_processing_seconds", processing_time)
            
            # Save conversation to database
            conversation = ChatConversation(
                user_id=user.user_id,
                question=request.question,
                response=response.content,
                retrieved_doc_ids=[doc.document.doc_id if isinstance(doc.document.doc_id, UUID) else UUID(doc.document.doc_id) for doc in context.retrieved_documents],
                confidence_score=response.confidence_score,
                processing_time=processing_time,
                question_category=context.context_metadata.get("question_category"),
                question_intent=context.context_metadata.get("question_intent"),
                prompt_template=context.prompt_template.value,
                ab_variant=request.conversation_id[-1] if request.conversation_id else None
            )
            
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
            
            # Format retrieved documents for response
            retrieved_docs = []
            for doc in context.retrieved_documents:
                retrieved_docs.append({
                    "doc_id": str(doc.document.doc_id),
                    "doc_type": doc.document.doc_type,
                    "similarity_score": doc.similarity_score,
                    "relevance_score": doc.relevance_score,
                    "content_summary": doc.content_summary
                })
            
            chat_response = ChatResponse(
                conversation_id=str(conversation.conversation_id),
                user_id=request.user_id,
                question=request.question,
                response=response.content,
                retrieved_documents=retrieved_docs,
                processing_time=processing_time,
                confidence_score=response.confidence_score,
                created_at=conversation.created_at.isoformat(),
                ab_variant=conversation.ab_variant
            )
            
            logger.info(
                f"Processed question for user {request.user_id}: "
                f"processing_time={processing_time:.2f}s, "
                f"confidence={response.confidence_score:.2f}"
            )
            
            return chat_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        await metrics_inc("chat_request_errors_total")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서비스 오류로 질문을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요."
        )

@router.get(
    "/history/{user_id}",
    response_model=ConversationHistoryResponse,
    summary="Get Conversation History",
    description="Retrieve conversation history for a specific user"
)
async def get_conversation_history(
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ConversationHistoryResponse:
    """
    Get conversation history for a user.
    
    Args:
        user_id: User identifier
        limit: Maximum number of conversations to return (1-100)
        offset: Number of conversations to skip
        db: Database session
        
    Returns:
        User's conversation history
        
    Raises:
        HTTPException: If user not found or invalid parameters
    """
    try:
        # Validate parameters
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 100"
            )
        
        if offset < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Offset must be non-negative"
            )
        
        async with db_manager.get_async_session() as db:
            # Verify authenticated user matches request user
            if current_user["user_id"] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You can only view your own conversation history"
                )
            
            # Verify user exists
            user = await get_user_by_id(user_id, db)
            
            # Get total count
            count_result = await db.execute(
                select(ChatConversation)
                .where(ChatConversation.user_id == user.user_id)
            )
            total_count = len(count_result.scalars().all())
            
            # Get conversations with pagination
            result = await db.execute(
                select(ChatConversation)
                .where(ChatConversation.user_id == user.user_id)
                .order_by(desc(ChatConversation.created_at))
                .limit(limit)
                .offset(offset)
            )
            conversations = result.scalars().all()
            
            # Format response
            conversation_items = []
            for conv in conversations:
                conversation_items.append(ConversationHistoryItem(
                    conversation_id=str(conv.conversation_id),
                    question=conv.question,
                    response=conv.response,
                    created_at=conv.created_at.isoformat(),
                    retrieved_doc_count=len(conv.retrieved_doc_ids) if conv.retrieved_doc_ids else 0
                ))
            
            has_more = (offset + len(conversations)) < total_count
            
            return ConversationHistoryResponse(
                user_id=user_id,
                conversations=conversation_items,
                total_count=total_count,
                has_more=has_more
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation history for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve conversation history: {str(e)}"
        )

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"WebSocket connected for user {user_id}")
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_message(self, user_id: str, message: WebSocketMessage):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(message.json())
            except Exception as e:
                logger.error(f"Error sending WebSocket message to {user_id}: {e}")
                self.disconnect(user_id)

manager = ConnectionManager()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str
):
    """
    WebSocket endpoint for real-time chat interactions.
    
    Provides real-time bidirectional communication for chat sessions.
    Clients can send questions and receive responses in real-time.
    
    Args:
        websocket: WebSocket connection
        user_id: User identifier
        db: Database session
    """
    await manager.connect(websocket, user_id)
    
    try:
        # Get database session
        async with db_manager.get_async_session() as db:
            # Verify user exists
            user = await get_user_by_id(user_id, db)
            
            # Send welcome message
            welcome_msg = WebSocketMessage(
                type="status",
                data={"message": "Connected to chat service", "user_id": user_id},
                timestamp=datetime.now().isoformat()
            )
            await manager.send_message(user_id, welcome_msg)
            
            # Initialize RAG components
            rag_components = await get_rag_components()
            question_processor, response_generator = rag_components
            
            # Initialize database-dependent components
            vector_search_service = VectorSearchService(db)
            context_builder = ContextBuilder(vector_search_service)
            document_repository = DocumentRepository(db, DocumentRepository.get_global_cache())
        
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                
                try:
                    message_data = json.loads(data)
                    
                    if message_data.get("type") == "question":
                        question = message_data.get("question", "").strip()
                        
                        if not question:
                            error_msg = WebSocketMessage(
                                type="error",
                                data={"error": "Question cannot be empty"},
                                timestamp=datetime.now().isoformat()
                            )
                            await manager.send_message(user_id, error_msg)
                            continue
                        
                        # Check rate limiting
                        if not check_rate_limit(user_id):
                            error_msg = WebSocketMessage(
                                type="error",
                                data={"error": "Rate limit exceeded. Please wait before asking another question."},
                                timestamp=datetime.now().isoformat()
                            )
                            await manager.send_message(user_id, error_msg)
                            continue
                        
                        # Send processing status
                        status_msg = WebSocketMessage(
                            type="status",
                            data={"message": "Processing your question...", "status": "processing"},
                            timestamp=datetime.now().isoformat()
                        )
                        await manager.send_message(user_id, status_msg)
                        
                        start_time = datetime.now()
                        
                        # Process question using RAG pipeline
                        processed_question = await question_processor.process_question(
                            question, user_id
                        )
                        
                        context = await context_builder.build_context(
                            processed_question, user_id
                        )
                        
                        response = await response_generator.generate_response(
                            context, user_id
                        )
                        
                        # Save conversation
                        conversation = ChatConversation(
                            user_id=user.user_id,
                            question=question,
                            response=response.content,
                            retrieved_doc_ids=[doc.document.doc_id if isinstance(doc.document.doc_id, UUID) else UUID(doc.document.doc_id) for doc in context.retrieved_documents]
                        )
                        
                        db.add(conversation)
                        await db.commit()
                        
                        processing_time = (datetime.now() - start_time).total_seconds()
                        
                        # Send response
                        response_msg = WebSocketMessage(
                            type="response",
                            data={
                                "conversation_id": str(conversation.conversation_id),
                                "question": question,
                                "response": response.content,
                                "processing_time": processing_time,
                                "confidence_score": response.confidence_score,
                                "retrieved_doc_count": len(context.retrieved_documents)
                            },
                            timestamp=datetime.now().isoformat()
                        )
                        await manager.send_message(user_id, response_msg)

                    elif message_data.get("type") == "feedback":
                        # Accept feedback over websocket
                        try:
                            payload = message_data.get("data", {})
                            feedback = ChatFeedback(
                                conversation_id=UUID(payload.get("conversation_id")),
                                user_id=user.user_id,
                                rating=payload.get("rating"),
                                helpful=payload.get("helpful"),
                                comment=payload.get("comment"),
                                tags=payload.get("tags") or []
                            )
                            db.add(feedback)
                            await db.commit()
                            ack = WebSocketMessage(
                                type="status",
                                data={"message": "Feedback received"},
                                timestamp=datetime.now().isoformat()
                            )
                            await manager.send_message(user_id, ack)
                        except Exception as e:
                            err = WebSocketMessage(
                                type="error",
                                data={"error": f"Feedback error: {str(e)}"},
                                timestamp=datetime.now().isoformat()
                            )
                            await manager.send_message(user_id, err)
                        
                    else:
                        error_msg = WebSocketMessage(
                            type="error",
                            data={"error": f"Unknown message type: {message_data.get('type')}"},
                            timestamp=datetime.now().isoformat()
                        )
                        await manager.send_message(user_id, error_msg)
                        
                except json.JSONDecodeError:
                    error_msg = WebSocketMessage(
                        type="error",
                        data={"error": "Invalid JSON format"},
                        timestamp=datetime.now().isoformat()
                    )
                    await manager.send_message(user_id, error_msg)
                    
                except Exception as e:
                    logger.error(f"Error processing WebSocket message for user {user_id}: {e}")
                    error_msg = WebSocketMessage(
                        type="error",
                        data={"error": "서비스 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."},
                        timestamp=datetime.now().isoformat()
                    )
                    await manager.send_message(user_id, error_msg)
    
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(user_id)

@router.get(
    "/health",
    summary="Chat Service Health Check",
    description="Check health status of chat service components"
)
async def health_check() -> Dict[str, Any]:
    """
    Check health status of chat service components.
    
    Returns:
        Health status of various components
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }
    
    async with db_manager.get_async_session() as db:
        try:
            # Check database connection
            await db.execute(select(1))
            health_status["components"]["database"] = "healthy"
            
            # Check user and document counts
            user_count = await db.execute(select(func.count(ChatUser.user_id)))
            doc_count = await db.execute(select(func.count(ChatDocument.doc_id)))
            health_status["components"]["data_stats"] = {
                "total_users": user_count.scalar(),
                "total_documents": doc_count.scalar()
            }
        except Exception as e:
            health_status["components"]["database"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        
        try:
            # Check RAG components initialization
            rag_components = await get_rag_components()
            health_status["components"]["rag_engine"] = "healthy"
        except Exception as e:
            health_status["components"]["rag_engine"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"

    # Cache stats
    try:
        cache = DocumentRepository.get_global_cache()
        stats = await cache.get_stats()
        health_status["components"]["document_cache"] = {
            "hits": stats.hits,
            "misses": stats.misses,
            "size": stats.size,
            "capacity": stats.capacity,
            "evictions": stats.evictions,
        }
    except Exception:
        pass
    
    # Check WebSocket connections
    health_status["components"]["websocket_connections"] = len(manager.active_connections)
    
    return health_status