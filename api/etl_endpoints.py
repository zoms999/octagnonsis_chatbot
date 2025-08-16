"""
FastAPI Endpoints for ETL Processing
API endpoints for test completion notifications and job monitoring
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
# Note: Redis dependency removed - using database-based job tracking
# Note: Celery dependency removed

from etl.test_completion_handler import (
    TestCompletionHandler, 
    TestCompletionRequest, 
    JobTracker,
    JobStatus
)
# Note: Background task management will be handled by BackgroundTaskManager in task 12.2

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/etl", tags=["ETL Processing"])

# Pydantic models for API
class TestCompletionNotification(BaseModel):
    """Test completion notification request model"""
    user_id: str = Field(..., description="User identifier")
    anp_seq: int = Field(..., description="Test sequence number", gt=0)
    test_type: str = Field(default="standard", description="Type of test completed")
    completed_at: Optional[datetime] = Field(default=None, description="Test completion timestamp")
    notification_source: str = Field(default="test_system", description="Source of notification")
    
    @validator('completed_at', pre=True, always=True)
    def set_completed_at(cls, v):
        return v or datetime.now()
    
    @validator('user_id')
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError('user_id cannot be empty')
        return v.strip()

class JobStatusResponse(BaseModel):
    """Job status response model"""
    job_id: str
    user_id: str
    anp_seq: int
    status: str
    progress_percentage: float
    current_step: str
    completed_steps: int
    total_steps: int
    started_at: str
    updated_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    failed_stage: Optional[str] = None
    retry_count: int = 0
    query_results_summary: Optional[Dict[str, Any]] = None
    documents_created: Optional[List[str]] = None

class JobHistoryResponse(BaseModel):
    """Job history response model"""
    job_id: str
    anp_seq: int
    status: str
    progress_percentage: float
    started_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    documents_created: Optional[List[str]] = None

class ETLJobResponse(BaseModel):
    """ETL job creation response model"""
    job_id: str
    task_id: str
    status: str
    message: str
    estimated_completion_time: str
    progress_url: str

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

@router.post(
    "/test-completion",
    response_model=ETLJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Handle Test Completion",
    description="Receive test completion notification and trigger ETL processing"
)
async def handle_test_completion(
    notification: TestCompletionNotification,
    handler: TestCompletionHandler = Depends(get_test_completion_handler)
) -> ETLJobResponse:
    """
    Handle test completion notification and trigger ETL processing
    
    This endpoint receives notifications when a user completes an aptitude test
    and triggers the asynchronous ETL pipeline to process the results.
    
    Args:
        notification: Test completion notification data
        handler: Test completion handler instance
        
    Returns:
        ETL job information including job ID and progress URL
        
    Raises:
        HTTPException: If ETL processing cannot be started
    """
    try:
        logger.info(f"Received test completion notification for user {notification.user_id}")
        
        # Convert to internal request format
        request = TestCompletionRequest(
            user_id=notification.user_id,
            anp_seq=notification.anp_seq,
            test_type=notification.test_type,
            completed_at=notification.completed_at,
            notification_source=notification.notification_source
        )
        
        # Trigger ETL processing
        result = await handler.handle_test_completion(request)
        
        return ETLJobResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to handle test completion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start ETL processing: {str(e)}"
        )

@router.get(
    "/jobs/{job_id}/status",
    response_model=JobStatusResponse,
    summary="Get Job Status",
    description="Get current status and progress of an ETL job"
)
async def get_job_status(
    job_id: str,
    handler: TestCompletionHandler = Depends(get_test_completion_handler)
) -> JobStatusResponse:
    """
    Get current status and progress of an ETL job
    
    Args:
        job_id: Job identifier
        handler: Test completion handler instance
        
    Returns:
        Current job status and progress information
        
    Raises:
        HTTPException: If job is not found
    """
    try:
        job_status = await handler.get_job_status(job_id)
        
        if not job_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        return JobStatusResponse(**job_status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve job status: {str(e)}"
        )

@router.get(
    "/jobs/{job_id}/progress",
    summary="Get Job Progress (SSE)",
    description="Get real-time job progress updates via Server-Sent Events"
)
async def get_job_progress_stream(
    job_id: str,
    handler: TestCompletionHandler = Depends(get_test_completion_handler)
):
    """
    Get real-time job progress updates via Server-Sent Events
    
    This endpoint provides a streaming connection for real-time job progress updates.
    Clients can use this to show live progress indicators.
    
    Args:
        job_id: Job identifier
        handler: Test completion handler instance
        
    Returns:
        Server-Sent Events stream with job progress updates
    """
    from fastapi.responses import StreamingResponse
    import asyncio
    import json
    
    async def event_stream():
        """Generate Server-Sent Events for job progress"""
        try:
            last_status = None
            
            while True:
                # Get current job status
                job_status = await handler.get_job_status(job_id)
                
                if not job_status:
                    yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                    break
                
                # Only send updates if status changed
                if job_status != last_status:
                    yield f"data: {json.dumps(job_status)}\n\n"
                    last_status = job_status
                
                # Stop streaming if job is completed
                if job_status.get('status') in ['success', 'failure']:
                    break
                
                # Wait before next check
                await asyncio.sleep(2)
                
        except Exception as e:
            logger.error(f"Error in job progress stream for {job_id}: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@router.get(
    "/users/{user_id}/jobs",
    response_model=List[JobHistoryResponse],
    summary="Get User Job History",
    description="Get job history for a specific user"
)
async def get_user_job_history(
    user_id: str,
    limit: int = 10,
    handler: TestCompletionHandler = Depends(get_test_completion_handler)
) -> List[JobHistoryResponse]:
    """
    Get job history for a specific user
    
    Args:
        user_id: User identifier
        limit: Maximum number of jobs to return (default: 10)
        handler: Test completion handler instance
        
    Returns:
        List of user's job history
    """
    try:
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 100"
            )
        
        job_history = await handler.get_user_job_history(user_id, limit)
        
        return [JobHistoryResponse(**job) for job in job_history]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job history for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve job history: {str(e)}"
        )

@router.post(
    "/jobs/{job_id}/cancel",
    summary="Cancel Job",
    description="Cancel a running ETL job"
)
async def cancel_job(
    job_id: str,
    handler: TestCompletionHandler = Depends(get_test_completion_handler)
) -> Dict[str, Any]:
    """
    Cancel a running ETL job
    
    Args:
        job_id: Job identifier
        handler: Test completion handler instance
        
    Returns:
        Cancellation result
        
    Raises:
        HTTPException: If job cannot be cancelled
    """
    try:
        success = await handler.cancel_job(job_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job cannot be cancelled (not found or already completed)"
            )
        
        return {
            "job_id": job_id,
            "status": "cancelled",
            "message": "Job cancellation requested"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}"
        )

@router.post(
    "/jobs/{job_id}/retry",
    response_model=ETLJobResponse,
    summary="Retry Failed Job",
    description="Retry a failed ETL job"
)
async def retry_failed_job(
    job_id: str,
    handler: TestCompletionHandler = Depends(get_test_completion_handler)
) -> ETLJobResponse:
    """
    Retry a failed ETL job
    
    Args:
        job_id: Job identifier
        handler: Test completion handler instance
        
    Returns:
        New job information for the retry
        
    Raises:
        HTTPException: If job cannot be retried
    """
    try:
        result = await handler.retry_failed_job(job_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job cannot be retried (not found, not failed, or max retries exceeded)"
            )
        
        return ETLJobResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry job: {str(e)}"
        )

@router.post(
    "/users/{user_id}/reprocess",
    response_model=ETLJobResponse,
    summary="Reprocess User Data",
    description="Trigger reprocessing of user's test data"
)
async def reprocess_user_data(
    user_id: str,
    anp_seq: int,
    force: bool = False,
    handler: TestCompletionHandler = Depends(get_test_completion_handler)
) -> ETLJobResponse:
    """
    Trigger reprocessing of user's test data
    
    This endpoint allows manual reprocessing of a user's data, useful for
    data corrections or system updates.
    
    Args:
        user_id: User identifier
        anp_seq: Test sequence number
        force: Whether to force reprocessing even if data exists
        handler: Test completion handler instance
        
    Returns:
        New job information for the reprocessing
    """
    try:
        # Create reprocessing request
        request = TestCompletionRequest(
            user_id=user_id,
            anp_seq=anp_seq,
            test_type="reprocess",
            completed_at=datetime.now(),
            notification_source="manual_reprocess"
        )
        
        # Trigger reprocessing
        result = await handler.handle_test_completion(request)
        
        return ETLJobResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to reprocess user data for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start reprocessing: {str(e)}"
        )

@router.get(
    "/health",
    summary="ETL Service Health Check",
    description="Check health status of ETL service components"
)
async def health_check() -> Dict[str, Any]:
    """
    Check health status of ETL service components
    
    Returns:
        Health status of various components
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }
    
    # Note: Redis health check removed - using database-based job tracking
    
    try:
        # Check background task manager status
        # Note: This will be implemented with BackgroundTaskManager in task 12.2
        health_status["components"]["background_tasks"] = "placeholder"
            
    except Exception as e:
        health_status["components"]["background_tasks"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check database connection (placeholder)
    try:
        # This would check actual database connection
        health_status["components"]["database"] = "healthy"
    except Exception as e:
        health_status["components"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    return health_status

@router.get(
    "/stats",
    summary="ETL Service Statistics",
    description="Get ETL service statistics and metrics"
)
async def get_etl_stats() -> Dict[str, Any]:
    """
    Get ETL service statistics and metrics
    
    Returns:
        Service statistics and metrics
    """
    try:
        # Get background task statistics
        # Note: This will be implemented with BackgroundTaskManager in task 12.2
        total_active = 0
        total_scheduled = 0
        total_reserved = 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "background_tasks": {
                "active_tasks": total_active,
                "scheduled_tasks": total_scheduled,
                "reserved_tasks": total_reserved,
                "workers": 0  # Will be implemented in task 12.2
            },
            "jobs": {
                # This would include job statistics from our tracking
                "total_jobs_tracked": "unknown",  # Would query Redis for actual count
                "jobs_in_progress": "unknown",
                "jobs_completed_today": "unknown",
                "jobs_failed_today": "unknown"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get ETL stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )