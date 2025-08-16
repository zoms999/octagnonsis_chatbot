"""
Test Completion Event Handler
Handles test completion notifications and triggers ETL processing
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import json

# Note: Celery and Redis dependencies removed - using database-based job tracking
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ChatUser, ChatETLJob
from database.connection import db_manager
from database.repositories import UserRepository
from etl.legacy_query_executor import LegacyQueryExecutor
from etl.document_transformer import DocumentTransformer
from etl.vector_embedder import VectorEmbedder

logger = logging.getLogger(__name__)

class JobStatus(Enum):
    """ETL job status enumeration"""
    PENDING = "pending"
    STARTED = "started"
    PROCESSING_QUERIES = "processing_queries"
    TRANSFORMING_DOCUMENTS = "transforming_documents"
    GENERATING_EMBEDDINGS = "generating_embeddings"
    STORING_DOCUMENTS = "storing_documents"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    PARTIAL = "partial"

@dataclass
class JobProgress:
    """Job progress tracking data"""
    job_id: str
    user_id: str
    anp_seq: int
    status: JobStatus
    progress_percentage: float
    current_step: str
    total_steps: int
    completed_steps: int
    started_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    failed_stage: Optional[str] = None
    retry_count: int = 0
    query_results_summary: Optional[Dict[str, Any]] = None
    documents_created: Optional[List[str]] = None

@dataclass
class TestCompletionRequest:
    """Test completion notification request"""
    user_id: str
    anp_seq: int
    test_type: str
    completed_at: datetime
    notification_source: str = "test_system"

class JobTracker:
    """
    Database-based job status tracking
    """

    def __init__(self):
        pass

    async def create_job(self, job_progress: JobProgress) -> None:
        """Create new job tracking entry in database"""
        async with db_manager.get_async_session() as session:
            # Ensure user exists to satisfy FK constraint on chat_etl_jobs
            try:
                user_uuid = uuid.UUID(job_progress.user_id)
            except Exception:
                # Fallback: generate UUID if invalid input (should not happen with API validation)
                user_uuid = uuid.uuid4()
            existing_user = await session.get(ChatUser, user_uuid)
            if not existing_user:
                # If user_id not found, try to find by anp_seq to avoid unique violations
                from sqlalchemy import select
                result = await session.execute(select(ChatUser).where(ChatUser.anp_seq == job_progress.anp_seq))
                user_by_anp = result.scalar_one_or_none()
                if user_by_anp:
                    user_uuid = user_by_anp.user_id
                else:
                    # Create minimal user record
                    session.add(ChatUser(
                        user_id=user_uuid,
                        anp_seq=job_progress.anp_seq,
                        name=f"User_{job_progress.anp_seq}",
                        test_completed_at=job_progress.started_at,
                    ))
                    await session.flush()

            job = ChatETLJob(
                job_id=uuid.UUID(job_progress.job_id),
                user_id=user_uuid,
                anp_seq=job_progress.anp_seq,
                status=job_progress.status.value,
                progress_percentage=int(job_progress.progress_percentage),
                current_step=job_progress.current_step,
                completed_steps=job_progress.completed_steps,
                total_steps=job_progress.total_steps,
                started_at=job_progress.started_at,
                updated_at=job_progress.updated_at,
                completed_at=job_progress.completed_at,
                error_message=job_progress.error_message,
                retry_count=job_progress.retry_count,
                query_results_summary=job_progress.query_results_summary,
                documents_created=job_progress.documents_created,
            )
            session.add(job)
            await session.flush()
        logger.info(f"Created job tracking for job_id: {job_progress.job_id}")

    async def update_job(self, job_id: str, **updates) -> Optional[JobProgress]:
        """Update job progress in database and return updated JobProgress if available"""
        async with db_manager.get_async_session() as session:
            job = await session.get(ChatETLJob, uuid.UUID(job_id))
            if not job:
                return None

            # Map incoming updates to model fields
            field_map = {
                'status': 'status',
                'progress_percentage': 'progress_percentage',
                'current_step': 'current_step',
                'completed_steps': 'completed_steps',
                'total_steps': 'total_steps',
                'completed_at': 'completed_at',
                'error_message': 'error_message',
                'error_type': 'error_type',
                'failed_stage': 'failed_stage',
                'retry_count': 'retry_count',
                'query_results_summary': 'query_results_summary',
                'documents_created': 'documents_created',
            }

            for key, value in updates.items():
                if key in field_map:
                    setattr(job, field_map[key], value)
            job.updated_at = datetime.now()

            await session.flush()

            return JobProgress(
                job_id=str(job.job_id),
                user_id=str(job.user_id),
                anp_seq=job.anp_seq,
                status=JobStatus(job.status),
                progress_percentage=float(job.progress_percentage),
                current_step=job.current_step or "",
                total_steps=job.total_steps,
                completed_steps=job.completed_steps,
                started_at=job.started_at,
                updated_at=job.updated_at,
                completed_at=job.completed_at,
                error_message=job.error_message,
                error_type=job.error_type,
                failed_stage=job.failed_stage,
                retry_count=job.retry_count,
                query_results_summary=job.query_results_summary,
                documents_created=job.documents_created,
            )

    async def get_job(self, job_id: str) -> Optional[JobProgress]:
        """Get job progress from database"""
        async with db_manager.get_async_session() as session:
            job = await session.get(ChatETLJob, uuid.UUID(job_id))
            if not job:
                return None
            return JobProgress(
                job_id=str(job.job_id),
                user_id=str(job.user_id),
                anp_seq=job.anp_seq,
                status=JobStatus(job.status),
                progress_percentage=float(job.progress_percentage),
                current_step=job.current_step or "",
                total_steps=job.total_steps,
                completed_steps=job.completed_steps,
                started_at=job.started_at,
                updated_at=job.updated_at,
                completed_at=job.completed_at,
                error_message=job.error_message,
                retry_count=job.retry_count,
                query_results_summary=job.query_results_summary,
                documents_created=job.documents_created,
            )

    async def get_user_jobs(self, user_id: str, limit: int = 10) -> List[JobProgress]:
        """Get user's recent jobs from database"""
        from sqlalchemy import select
        async with db_manager.get_async_session() as session:
            result = await session.execute(
                select(ChatETLJob).where(ChatETLJob.user_id == uuid.UUID(user_id)).order_by(ChatETLJob.started_at.desc()).limit(limit)
            )
            rows = result.scalars().all()
            jobs: List[JobProgress] = []
            for job in rows:
                jobs.append(JobProgress(
                    job_id=str(job.job_id),
                    user_id=str(job.user_id),
                    anp_seq=job.anp_seq,
                    status=JobStatus(job.status),
                    progress_percentage=float(job.progress_percentage),
                    current_step=job.current_step or "",
                    total_steps=job.total_steps,
                    completed_steps=job.completed_steps,
                    started_at=job.started_at,
                    updated_at=job.updated_at,
                    completed_at=job.completed_at,
                    error_message=job.error_message,
                    retry_count=job.retry_count,
                    query_results_summary=job.query_results_summary,
                    documents_created=job.documents_created,
                ))
            return jobs

    async def delete_job(self, job_id: str) -> bool:
        """Delete job tracking data from database"""
        async with db_manager.get_async_session() as session:
            job = await session.get(ChatETLJob, uuid.UUID(job_id))
            if not job:
                return False
            await session.delete(job)
            await session.flush()
            return True

class TestCompletionHandler:
    """
    Handles test completion events and orchestrates ETL processing
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: int = 60
    ):
        # Database-based job tracking
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.job_tracker = JobTracker()
    
    async def handle_test_completion(
        self,
        request: TestCompletionRequest
    ) -> Dict[str, Any]:
        """
        Handle test completion notification and trigger ETL processing
        
        Args:
            request: Test completion request data
            
        Returns:
            Dictionary with job information
        """
        try:
            # Generate unique job ID
            job_id = str(uuid.uuid4())
            
            # Create initial job progress
            job_progress = JobProgress(
                job_id=job_id,
                user_id=request.user_id,
                anp_seq=request.anp_seq,
                status=JobStatus.PENDING,
                progress_percentage=0.0,
                current_step="Initializing ETL processing",
                total_steps=5,  # queries, transform, embed, store, complete
                completed_steps=0,
                started_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Store job tracking (creates user if needed)
            await self.job_tracker.create_job(job_progress)
            
            # Mark job as started
            await self.job_tracker.update_job(
                job_id,
                status=JobStatus.STARTED.value,
                current_step="Queued for processing",
                progress_percentage=1,
                completed_steps=0
            )
            
            # Trigger async ETL processing (fire-and-forget)
            # For now, schedule with asyncio.create_task
            try:
                from etl.tasks import process_test_completion as _process
                asyncio.create_task(_process(
                    user_id=request.user_id,
                    anp_seq=request.anp_seq,
                    job_id=job_id,
                    test_type=request.test_type,
                    completed_at=request.completed_at.isoformat() if isinstance(request.completed_at, datetime) else None,
                    notification_source=request.notification_source,
                ))
                task_id = f"task_{job_id}"
            except Exception as schedule_err:
                logger.error(f"Failed to schedule ETL task: {schedule_err}")
                task_id = f"task_{job_id}_failed_to_schedule"
            
            logger.info(
                f"Triggered ETL processing for user {request.user_id}, "
                f"anp_seq {request.anp_seq}, job_id {job_id}, "
                f"task_id {task_id}"
            )
            
            return {
                "job_id": job_id,
                "task_id": task_id,
                "status": JobStatus.STARTED.value,
                "message": "ETL job queued and started",
                "estimated_completion_time": "5-10 minutes",
                "progress_url": f"/api/etl/jobs/{job_id}/status"
            }
            
        except Exception as e:
            logger.error(f"Failed to handle test completion: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start ETL processing: {str(e)}"
            )
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current job status and progress
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job status dictionary or None if not found
        """
        job_progress = await self.job_tracker.get_job(job_id)
        
        if not job_progress:
            return None
        
        # Get Celery task status if available
        celery_status = None
        try:
            # This would need the actual Celery task ID, which we'd need to store
            # For now, we'll rely on our own job tracking
            pass
        except Exception as e:
            logger.warning(f"Could not get Celery status for job {job_id}: {e}")
        
        return {
            "job_id": job_progress.job_id,
            "user_id": job_progress.user_id,
            "anp_seq": job_progress.anp_seq,
            "status": job_progress.status.value,
            "progress_percentage": job_progress.progress_percentage,
            "current_step": job_progress.current_step,
            "completed_steps": job_progress.completed_steps,
            "total_steps": job_progress.total_steps,
            "started_at": job_progress.started_at.isoformat(),
            "updated_at": job_progress.updated_at.isoformat(),
            "completed_at": job_progress.completed_at.isoformat() if job_progress.completed_at else None,
            "error_message": job_progress.error_message,
            "retry_count": job_progress.retry_count,
            "query_results_summary": job_progress.query_results_summary,
            "documents_created": job_progress.documents_created,
            "task_status": "placeholder"
        }
    
    async def get_user_job_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get user's job history
        
        Args:
            user_id: User identifier
            limit: Maximum number of jobs to return
            
        Returns:
            List of job status dictionaries
        """
        jobs = await self.job_tracker.get_user_jobs(user_id, limit)
        
        return [
            {
                "job_id": job.job_id,
                "anp_seq": job.anp_seq,
                "status": job.status.value,
                "progress_percentage": job.progress_percentage,
                "started_at": job.started_at.isoformat(),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "error_message": job.error_message,
                "documents_created": job.documents_created
            }
            for job in jobs
        ]
    
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if job was cancelled, False otherwise
        """
        job_progress = await self.job_tracker.get_job(job_id)
        
        if not job_progress:
            return False
        
        if job_progress.status in [JobStatus.SUCCESS, JobStatus.FAILURE]:
            return False  # Already completed
        
        try:
            # Update job status to cancelled (we'll use FAILURE with specific message)
            await self.job_tracker.update_job(
                job_id,
                status=JobStatus.FAILURE.value,
                error_message="Job cancelled by user",
                completed_at=datetime.now().isoformat(),
                progress_percentage=0.0
            )
            
            # TODO: Cancel the actual Celery task if possible
            # This would require storing the Celery task ID
            
            logger.info(f"Cancelled job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False
    
    async def retry_failed_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retry a failed job
        
        Args:
            job_id: Job identifier
            
        Returns:
            New job information or None if retry not possible
        """
        job_progress = await self.job_tracker.get_job(job_id)
        
        if not job_progress:
            return None
        
        if job_progress.status != JobStatus.FAILURE:
            return None  # Only retry failed jobs
        
        if job_progress.retry_count >= self.max_retries:
            return None  # Max retries exceeded
        
        # Create new job for retry
        new_request = TestCompletionRequest(
            user_id=job_progress.user_id,
            anp_seq=job_progress.anp_seq,
            test_type="retry",  # Mark as retry
            completed_at=datetime.now(),
            notification_source="retry_system"
        )
        
        return await self.handle_test_completion(new_request)

# Failure recovery mechanisms
class FailureRecoveryManager:
    """
    Manages failure recovery and retry strategies
    """
    
    def __init__(self, job_tracker: JobTracker, max_auto_retries: int = 2):
        self.job_tracker = job_tracker
        self.max_auto_retries = max_auto_retries
    
    async def handle_job_failure(
        self,
        job_id: str,
        error: Exception,
        step: str,
        auto_retry: bool = True
    ) -> bool:
        """
        Handle job failure with recovery strategies
        
        Args:
            job_id: Job identifier
            error: Exception that caused the failure
            step: Current processing step
            auto_retry: Whether to attempt automatic retry
            
        Returns:
            True if recovery was attempted, False otherwise
        """
        job_progress = await self.job_tracker.get_job(job_id)
        
        if not job_progress:
            logger.error(f"Cannot handle failure for unknown job {job_id}")
            return False
        
        # Determine if this is a recoverable error
        recoverable = self._is_recoverable_error(error, step)
        
        # Update job with failure information
        await self.job_tracker.update_job(
            job_id,
            status=JobStatus.FAILURE.value,
            error_message=str(error),
            current_step=f"Failed at: {step}",
            completed_at=datetime.now().isoformat()
        )
        
        # Attempt automatic retry if conditions are met
        if (auto_retry and recoverable and 
            job_progress.retry_count < self.max_auto_retries):
            
            logger.info(f"Attempting automatic retry for job {job_id} (attempt {job_progress.retry_count + 1})")
            
            # Schedule retry with exponential backoff
            retry_delay = 60 * (2 ** job_progress.retry_count)  # 1min, 2min, 4min...
            
            # This would trigger a new Celery task with delay
            # For now, we'll just log the intent
            logger.info(f"Would retry job {job_id} in {retry_delay} seconds")
            
            return True
        
        # Log failure for manual intervention
        logger.error(
            f"Job {job_id} failed permanently at step '{step}': {error}. "
            f"Retry count: {job_progress.retry_count}/{self.max_auto_retries}"
        )
        
        return False
    
    def _is_recoverable_error(self, error: Exception, step: str) -> bool:
        """
        Determine if an error is recoverable
        
        Args:
            error: Exception that occurred
            step: Processing step where error occurred
            
        Returns:
            True if error is likely recoverable
        """
        # Network/API errors are usually recoverable
        if any(keyword in str(error).lower() for keyword in [
            'timeout', 'connection', 'network', 'rate limit', 'temporary'
        ]):
            return True
        
        # Database connection errors are recoverable
        if any(keyword in str(error).lower() for keyword in [
            'database', 'connection pool', 'deadlock'
        ]):
            return True
        
        # Embedding API errors might be recoverable
        if step == "generating_embeddings" and "api" in str(error).lower():
            return True
        
        # Data validation errors are usually not recoverable
        if any(keyword in str(error).lower() for keyword in [
            'validation', 'invalid data', 'missing required'
        ]):
            return False
        
        # Default to not recoverable for safety
        return False

# Administrator notification system
class AdminNotificationManager:
    """
    Manages notifications to administrators for critical failures
    """
    
    def __init__(self, notification_channels: List[str] = None):
        self.notification_channels = notification_channels or ["log", "email"]
    
    async def notify_critical_failure(
        self,
        job_id: str,
        user_id: str,
        anp_seq: int,
        error: Exception,
        step: str,
        retry_count: int
    ) -> None:
        """
        Notify administrators of critical failures
        
        Args:
            job_id: Job identifier
            user_id: User identifier
            anp_seq: Test sequence number
            error: Exception that caused the failure
            step: Processing step where failure occurred
            retry_count: Number of retries attempted
        """
        message = (
            f"CRITICAL ETL FAILURE\n"
            f"Job ID: {job_id}\n"
            f"User ID: {user_id}\n"
            f"ANP Sequence: {anp_seq}\n"
            f"Failed Step: {step}\n"
            f"Error: {str(error)}\n"
            f"Retry Count: {retry_count}\n"
            f"Timestamp: {datetime.now().isoformat()}\n"
            f"Manual intervention may be required."
        )
        
        # Log notification
        if "log" in self.notification_channels:
            logger.critical(message)
        
        # Email notification (placeholder - would integrate with actual email service)
        if "email" in self.notification_channels:
            await self._send_email_notification(message)
        
        # Slack notification (placeholder - would integrate with Slack API)
        if "slack" in self.notification_channels:
            await self._send_slack_notification(message)
    
    async def _send_email_notification(self, message: str) -> None:
        """Send email notification (placeholder)"""
        # TODO: Integrate with actual email service
        logger.info(f"Would send email notification: {message[:100]}...")
    
    async def _send_slack_notification(self, message: str) -> None:
        """Send Slack notification (placeholder)"""
        # TODO: Integrate with Slack API
        logger.info(f"Would send Slack notification: {message[:100]}...")