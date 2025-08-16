"""
FastAPI Endpoints for User Management
API endpoints for user profiles, document access, and ETL re-triggering
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

import os
from fastapi import APIRouter, HTTPException, Depends, status, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload

from database.connection import get_async_session
from database.models import ChatUser, ChatDocument, ChatConversation, DocumentType
from etl.test_completion_handler import TestCompletionHandler, TestCompletionRequest
# Note: Background task management will be handled by BackgroundTaskManager in task 12.2

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/users", tags=["User Management"])

# Pydantic models for API
class UserProfile(BaseModel):
    """User profile response model"""
    user_id: str
    anp_seq: int
    name: str
    email: Optional[str]
    test_completed_at: str
    created_at: str
    updated_at: str
    document_count: int
    conversation_count: int
    available_document_types: List[str]
    last_conversation_at: Optional[str] = None

class DocumentSummary(BaseModel):
    """Document summary for user documents endpoint"""
    doc_id: str
    doc_type: str
    summary_text: str
    created_at: str
    updated_at: str
    content_preview: Dict[str, Any]

class UserDocumentsResponse(BaseModel):
    """User documents response model"""
    user_id: str
    documents: List[DocumentSummary]
    total_count: int
    document_types: List[str]

class ReprocessRequest(BaseModel):
    """ETL reprocessing request model"""
    force: bool = Field(default=False, description="Force reprocessing even if data exists")
    reason: str = Field(default="manual_request", description="Reason for reprocessing")

class ReprocessResponse(BaseModel):
    """ETL reprocessing response model"""
    job_id: str
    status: str
    message: str
    user_id: str
    anp_seq: int
    estimated_completion_time: str
    progress_url: str

def _is_admin(admin_token: Optional[str]) -> bool:
    expected = os.getenv("ADMIN_TOKEN")
    if not expected:
        return False
    return admin_token == expected

# Authentication and authorization middleware (basic)
async def verify_user_access(
    user_id: str,
    requesting_user: Optional[str] = None,
    admin_token: Optional[str] = None,
) -> bool:
    """Basic access check: allow if admin token matches or user matches."""
    # Allow if admin
    if _is_admin(admin_token):
        return True
    # Allow if requesting user matches target
    if requesting_user and requesting_user.strip() == user_id:
        return True
    # Fallback: if auth disabled via env, allow
    if os.getenv("AUTH_DISABLED", "true").lower() == "true":
        return True
    return False

async def get_user_by_id(user_id: str, db: AsyncSession) -> ChatUser:
    """Get user by ID with error handling"""
    try:
        # Try to parse as UUID first
        if len(user_id) == 32 and '-' not in user_id:
            # Add dashes to make it a proper UUID format
            formatted_uuid = f"{user_id[:8]}-{user_id[8:12]}-{user_id[12:16]}-{user_id[16:20]}-{user_id[20:]}"
            user_uuid = UUID(formatted_uuid)
        else:
            user_uuid = UUID(user_id)
        
        # Load user with relationships
        result = await db.execute(
            select(ChatUser)
            .options(
                selectinload(ChatUser.documents),
                selectinload(ChatUser.conversations)
            )
            .where(ChatUser.user_id == user_uuid)
        )
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

# Note: Redis dependency removed - using database-based job tracking

# Dependency to get test completion handler
def get_test_completion_handler() -> TestCompletionHandler:
    """Get test completion handler instance"""
    try:
        return TestCompletionHandler(
            max_retries=3,
            retry_delay=60
        )
    except Exception as e:
        logger.error(f"Failed to initialize test completion handler: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ETL service initialization failed"
        )

@router.get(
    "/{user_id}/profile",
    response_model=UserProfile,
    summary="Get User Profile",
    description="Retrieve detailed profile information for a specific user"
)
async def get_user_profile(
    user_id: str,
    db: AsyncSession = Depends(get_async_session),
    requesting_user: Optional[str] = Header(None, alias="X-User-Id"),
    admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
) -> UserProfile:
    """
    Get detailed user profile information.
    
    This endpoint provides comprehensive information about a user including
    their test completion status, document counts, and conversation history.
    
    Args:
        user_id: User identifier
        db: Database session
        
    Returns:
        Detailed user profile information
        
    Raises:
        HTTPException: If user not found or access denied
    """
    try:
        # Verify access (basic auth)
        if not await verify_user_access(user_id, requesting_user, admin_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get user with relationships
        user = await get_user_by_id(user_id, db)
        
        # Calculate statistics
        document_count = len(user.documents)
        conversation_count = len(user.conversations)
        
        # Get available document types
        available_doc_types = list(set(doc.doc_type for doc in user.documents))
        
        # Get last conversation timestamp
        last_conversation_at = None
        if user.conversations:
            latest_conversation = max(user.conversations, key=lambda c: c.created_at)
            last_conversation_at = latest_conversation.created_at.isoformat()
        
        profile = UserProfile(
            user_id=user_id,
            anp_seq=user.anp_seq,
            name=user.name,
            email=user.email,
            test_completed_at=user.test_completed_at.isoformat(),
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
            document_count=document_count,
            conversation_count=conversation_count,
            available_document_types=available_doc_types,
            last_conversation_at=last_conversation_at
        )
        
        logger.info(f"Retrieved profile for user {user_id}")
        return profile
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user profile: {str(e)}"
        )

@router.get(
    "/{user_id}/documents",
    response_model=UserDocumentsResponse,
    summary="Get User Documents",
    description="Retrieve all documents associated with a specific user"
)
async def get_user_documents(
    user_id: str,
    doc_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_async_session),
    requesting_user: Optional[str] = Header(None, alias="X-User-Id"),
    admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
) -> UserDocumentsResponse:
    """
    Get all documents for a specific user.
    
    This endpoint provides access to all processed documents from the user's
    aptitude test results, with optional filtering by document type.
    
    Args:
        user_id: User identifier
        doc_type: Optional filter by document type
        limit: Maximum number of documents to return (1-100)
        offset: Number of documents to skip
        db: Database session
        
    Returns:
        User's documents with metadata
        
    Raises:
        HTTPException: If user not found, invalid parameters, or access denied
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
        
        if doc_type and not DocumentType.is_valid(doc_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document type: {doc_type}. Valid types: {DocumentType.all_types()}"
            )
        
        # Verify access
        if not await verify_user_access(user_id, requesting_user, admin_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get user to verify existence
        user = await get_user_by_id(user_id, db)
        
        # Build query for documents
        query = select(ChatDocument).where(ChatDocument.user_id == user.user_id)
        
        if doc_type:
            query = query.where(ChatDocument.doc_type == doc_type)
        
        # Get total count
        count_query = select(func.count(ChatDocument.doc_id)).where(ChatDocument.user_id == user.user_id)
        if doc_type:
            count_query = count_query.where(ChatDocument.doc_type == doc_type)
        
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        # Get documents with pagination
        query = query.order_by(desc(ChatDocument.created_at)).limit(limit).offset(offset)
        result = await db.execute(query)
        documents = result.scalars().all()
        
        # Format documents for response
        document_summaries = []
        for doc in documents:
            # Create content preview (first few fields of content)
            content_preview = {}
            try:
                import json
                content = json.loads(doc.content) if isinstance(doc.content, str) else doc.content
                
                # Extract key information based on document type
                if doc.doc_type == "PERSONALITY_PROFILE":
                    if "primary_tendency" in content:
                        content_preview["primary_tendency"] = content["primary_tendency"].get("name", "")
                    if "secondary_tendency" in content:
                        content_preview["secondary_tendency"] = content["secondary_tendency"].get("name", "")
                
                elif doc.doc_type == "THINKING_SKILLS":
                    if "skills" in content:
                        top_skills = content["skills"][:3]
                        content_preview["top_skills"] = [
                            {"name": skill.get("name", ""), "score": skill.get("score", "")}
                            for skill in top_skills
                        ]
                
                elif doc.doc_type == "CAREER_RECOMMENDATIONS":
                    if "recommended_jobs" in content:
                        top_jobs = content["recommended_jobs"][:3]
                        content_preview["top_recommendations"] = [
                            job.get("name", "") for job in top_jobs
                        ]
                
                elif doc.doc_type == "COMPETENCY_ANALYSIS":
                    if "top_competencies" in content:
                        top_comps = content["top_competencies"][:3]
                        content_preview["top_competencies"] = [
                            {"name": comp.get("name", ""), "percentile": comp.get("percentile", "")}
                            for comp in top_comps
                        ]
                
                else:
                    # Generic preview for other document types
                    content_preview = {k: v for k, v in list(content.items())[:3]}
                    
            except Exception as e:
                logger.warning(f"Error creating content preview for document {doc.doc_id}: {e}")
                content_preview = {"error": "Unable to preview content"}
            
            document_summaries.append(DocumentSummary(
                doc_id=str(doc.doc_id),
                doc_type=doc.doc_type,
                summary_text=doc.summary_text,
                created_at=doc.created_at.isoformat(),
                updated_at=doc.updated_at.isoformat(),
                content_preview=content_preview
            ))
        
        # Get all document types for this user
        all_doc_types_result = await db.execute(
            select(ChatDocument.doc_type)
            .where(ChatDocument.user_id == user.user_id)
            .distinct()
        )
        all_doc_types = [row[0] for row in all_doc_types_result.fetchall()]
        
        response = UserDocumentsResponse(
            user_id=user_id,
            documents=document_summaries,
            total_count=total_count,
            document_types=all_doc_types
        )
        
        logger.info(f"Retrieved {len(document_summaries)} documents for user {user_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user documents for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user documents: {str(e)}"
        )

@router.post(
    "/{user_id}/reprocess",
    response_model=ReprocessResponse,
    summary="Reprocess User Data",
    description="Trigger reprocessing of user's aptitude test data through ETL pipeline"
)
async def reprocess_user_data(
    user_id: str,
    request: ReprocessRequest,
    db: AsyncSession = Depends(get_async_session),
    handler: TestCompletionHandler = Depends(get_test_completion_handler),
    requesting_user: Optional[str] = Header(None, alias="X-User-Id"),
    admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
) -> ReprocessResponse:
    """
    Trigger reprocessing of user's test data.
    
    This endpoint allows manual reprocessing of a user's aptitude test data,
    useful for data corrections, system updates, or when processing initially failed.
    
    Args:
        user_id: User identifier
        request: Reprocessing request parameters
        db: Database session
        handler: Test completion handler instance
        
    Returns:
        Reprocessing job information
        
    Raises:
        HTTPException: If user not found, access denied, or reprocessing fails
    """
    try:
        # Verify access (admin or self)
        if not await verify_user_access(user_id, requesting_user, admin_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get user to verify existence and get anp_seq
        user = await get_user_by_id(user_id, db)
        
        # Check if user already has documents and force flag
        if user.documents and not request.force:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already has processed documents. Use force=true to reprocess."
            )
        
        # Create reprocessing request
        completion_request = TestCompletionRequest(
            user_id=user_id,
            anp_seq=user.anp_seq,
            test_type="reprocess",
            completed_at=datetime.now(),
            notification_source=f"manual_reprocess_{request.reason}"
        )
        
        # Trigger ETL processing
        result = await handler.handle_test_completion(completion_request)
        
        # Create response
        reprocess_response = ReprocessResponse(
            job_id=result["job_id"],
            status=result["status"],
            message=f"Reprocessing started for user {user_id}",
            user_id=user_id,
            anp_seq=user.anp_seq,
            estimated_completion_time=result["estimated_completion_time"],
            progress_url=result["progress_url"]
        )
        
        logger.info(
            f"Started reprocessing for user {user_id} (anp_seq: {user.anp_seq}), "
            f"job_id: {result['job_id']}, reason: {request.reason}"
        )
        
        return reprocess_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reprocessing user data for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start reprocessing: {str(e)}"
        )

@router.get(
    "/{user_id}/processing-status",
    summary="Get Processing Status",
    description="Get current processing status for user's data"
)
async def get_user_processing_status(
    user_id: str,
    db: AsyncSession = Depends(get_async_session),
    handler: TestCompletionHandler = Depends(get_test_completion_handler),
    requesting_user: Optional[str] = Header(None, alias="X-User-Id"),
    admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
) -> Dict[str, Any]:
    """
    Get current processing status for a user's data.
    
    This endpoint provides information about any ongoing or recent
    ETL processing jobs for the user.
    
    Args:
        user_id: User identifier
        db: Database session
        handler: Test completion handler instance
        
    Returns:
        Processing status information
    """
    try:
        # Verify access
        if not await verify_user_access(user_id, requesting_user, admin_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Verify user exists
        user = await get_user_by_id(user_id, db)
        
        # Get recent jobs for this user
        job_history = await handler.get_user_job_history(user_id, limit=5)
        
        # Determine current status
        current_status = "completed"
        active_job = None
        
        if job_history:
            latest_job = job_history[0]
            if latest_job["status"] in ["pending", "in_progress"]:
                current_status = latest_job["status"]
                active_job = latest_job
        
        return {
            "user_id": user_id,
            "current_status": current_status,
            "active_job": active_job,
            "recent_jobs": job_history,
            "has_documents": len(user.documents) > 0,
            "document_count": len(user.documents),
            "last_processed_at": max(
                (doc.created_at for doc in user.documents), 
                default=None
            ).isoformat() if user.documents else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting processing status for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get processing status: {str(e)}"
        )

@router.delete(
    "/{user_id}/documents",
    summary="Delete User Documents",
    description="Delete all or specific documents for a user"
)
async def delete_user_documents(
    user_id: str,
    doc_type: Optional[str] = None,
    confirm: bool = False,
    db: AsyncSession = Depends(get_async_session),
    requesting_user: Optional[str] = Header(None, alias="X-User-Id"),
    admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
) -> Dict[str, Any]:
    """
    Delete user documents.
    
    This endpoint allows deletion of user documents, either all documents
    or documents of a specific type. Requires confirmation parameter.
    
    Args:
        user_id: User identifier
        doc_type: Optional document type to delete (if not provided, deletes all)
        confirm: Confirmation flag (must be true to proceed)
        db: Database session
        
    Returns:
        Deletion result information
    """
    try:
        if not confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Deletion requires confirmation. Set confirm=true to proceed."
            )
        
        # Verify access (admin or self)
        if not await verify_user_access(user_id, requesting_user, admin_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get user to verify existence
        user = await get_user_by_id(user_id, db)
        
        # Build deletion query
        if doc_type:
            if not DocumentType.is_valid(doc_type):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid document type: {doc_type}"
                )
            
            # Delete specific document type
            result = await db.execute(
                select(ChatDocument)
                .where(ChatDocument.user_id == user.user_id)
                .where(ChatDocument.doc_type == doc_type)
            )
            docs_to_delete = result.scalars().all()
            
            for doc in docs_to_delete:
                await db.delete(doc)
            
            await db.commit()
            
            return {
                "user_id": user_id,
                "deleted_document_type": doc_type,
                "deleted_count": len(docs_to_delete),
                "message": f"Deleted {len(docs_to_delete)} documents of type {doc_type}"
            }
        
        else:
            # Delete all documents
            docs_to_delete = user.documents
            doc_count = len(docs_to_delete)
            
            for doc in docs_to_delete:
                await db.delete(doc)
            
            await db.commit()
            
            return {
                "user_id": user_id,
                "deleted_all_documents": True,
                "deleted_count": doc_count,
                "message": f"Deleted all {doc_count} documents for user"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting documents for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete documents: {str(e)}"
        )

@router.get(
    "/health",
    summary="User Service Health Check",
    description="Check health status of user management service"
)
async def health_check(
    db: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """
    Check health status of user management service.
    
    Returns:
        Health status information
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }
    
    try:
        # Check database connection
        await db.execute(select(1))
        health_status["components"]["database"] = "healthy"
    except Exception as e:
        health_status["components"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    try:
        # Check ETL handler
        handler = get_test_completion_handler()
        health_status["components"]["etl_handler"] = "healthy"
    except Exception as e:
        health_status["components"]["etl_handler"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status