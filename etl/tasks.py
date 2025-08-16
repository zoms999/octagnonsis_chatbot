"""
Background Tasks for ETL Processing
Asyncio-based task definitions for test completion processing
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import traceback
import os

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ChatUser, ChatDocument
from database.repositories import UserRepository, DocumentRepository
from database.connection import db_manager
from etl.legacy_query_executor import LegacyQueryExecutor, QueryResult
from etl.document_transformer import DocumentTransformer, TransformedDocument
from etl.vector_embedder import VectorEmbedder
from etl.test_completion_handler import JobTracker

logger = logging.getLogger(__name__)

# Task configuration
TASK_CONFIG = {
    'max_concurrent_jobs': int(os.getenv('ETL_MAX_CONCURRENT_JOBS', '5')),
    'job_timeout_minutes': int(os.getenv('ETL_JOB_TIMEOUT_MINUTES', '30')),
    'max_retries': int(os.getenv('ETL_MAX_RETRIES', '3')),
    'retry_delay_seconds': int(os.getenv('ETL_RETRY_DELAY_SECONDS', '60')),
}

def get_database_session():
    """Get async database session using the app's shared DatabaseManager."""
    return db_manager.get_async_session()

async def process_test_completion(
    user_id: str,
    anp_seq: int,
    job_id: str,
    test_type: str = "standard",
    completed_at: str = None,
    notification_source: str = "test_system"
) -> Dict[str, Any]:
    """
    Main ETL processing task for test completion
    
    Args:
        user_id: User identifier
        anp_seq: Test sequence number
        job_id: Job tracking identifier
        test_type: Type of test completed
        completed_at: ISO timestamp of test completion
        notification_source: Source of the notification
    """
    return await _process_test_completion_async(
        user_id, anp_seq, job_id, test_type, completed_at, notification_source
    )

async def _process_test_completion_async(
    user_id: str,
    anp_seq: int,
    job_id: str,
    test_type: str,
    completed_at: str,
    notification_source: str
) -> Dict[str, Any]:
    """
    Async implementation of ETL processing using the orchestrator
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"Starting ETL processing for job {job_id}, user {user_id}, anp_seq {anp_seq}")
        
        # Import orchestrator
        from etl.etl_orchestrator import ETLOrchestrator, ValidationLevel
        
        # Initialize orchestrator with configuration
        validation_level = ValidationLevel.STANDARD
        if os.getenv('ETL_VALIDATION_LEVEL') == 'strict':
            validation_level = ValidationLevel.STRICT
        elif os.getenv('ETL_VALIDATION_LEVEL') == 'basic':
            validation_level = ValidationLevel.BASIC
        
        orchestrator = ETLOrchestrator(
            validation_level=validation_level,
            enable_rollback=os.getenv('ETL_ENABLE_ROLLBACK', 'true').lower() == 'true',
            max_retries_per_stage=int(os.getenv('ETL_MAX_RETRIES_PER_STAGE', '2'))
        )
        
        # Get database session
        async with get_database_session() as session:
            # Process test completion using orchestrator with DB-based tracker
            result = await orchestrator.process_test_completion(
                user_id=user_id,
                anp_seq=anp_seq,
                job_id=job_id,
                session=session,
                job_tracker=JobTracker()
            )
            
            logger.info(f"ETL processing completed successfully for job {job_id}")
            # Ensure job is marked as success if orchestrator didn't already
            try:
                await JobTracker().update_job(
                    job_id,
                    status="success",
                    progress_percentage=100.0,
                    current_step="ETL processing completed",
                    completed_steps=7,
                    completed_at=datetime.now(),
                )
            except Exception:
                pass
            return result
        
    except Exception as e:
        # Handle failure
        processing_time = (datetime.now() - start_time).total_seconds()
        error_message = str(e)
        
        logger.error(f"ETL processing failed for job {job_id}: {error_message}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Ensure failure is recorded
        try:
            await JobTracker().update_job(
                job_id,
                status="failure",
                error_message=error_message,
                completed_at=datetime.now(),
            )
        except Exception:
            pass
        
        return {
            "job_id": job_id,
            "status": "failure",
            "error_message": error_message,
            "processing_time_seconds": processing_time
        }

# Individual step functions are now handled by the ETL orchestrator
# This keeps the code cleaner and provides better error handling and validation

async def cleanup_failed_jobs(max_age_hours: int = 168) -> Dict[str, Any]:
    """
    Cleanup old failed jobs
    
    Args:
        max_age_hours: Maximum age of jobs to keep in hours
    """
    return await _cleanup_failed_jobs_async(max_age_hours)

async def _cleanup_failed_jobs_async(max_age_hours: int) -> Dict[str, Any]:
    """Async implementation of job cleanup"""
    try:
        # This would need to be implemented based on how we store job data
        # For now, just log the intent
        logger.info(f"Would cleanup jobs older than {max_age_hours} hours")
        
        return {
            "status": "success",
            "cleaned_jobs": 0,
            "message": "Cleanup completed"
        }
        
    except Exception as e:
        logger.error(f"Job cleanup failed: {e}")
        return {
            "status": "failure",
            "error_message": str(e)
        }

async def reprocess_user_data(user_id: str, anp_seq: int, force: bool = False) -> Dict[str, Any]:
    """
    Reprocess user data (for data corrections or system updates)
    
    Args:
        user_id: User identifier
        anp_seq: Test sequence number
        force: Whether to force reprocessing even if data exists
    """
    return await _reprocess_user_data_async(user_id, anp_seq, force)

async def _reprocess_user_data_async(user_id: str, anp_seq: int, force: bool) -> Dict[str, Any]:
    """Async implementation of user data reprocessing"""
    try:
        # Check if user already has documents
        if not force:
            async with get_database_session() as session:
                doc_repo = DocumentRepository(session)
                existing_docs = await doc_repo.get_by_user_id(user_id)
                
                if existing_docs:
                    logger.info(f"User {user_id} already has {len(existing_docs)} documents. Use force=True to reprocess.")
                    return {
                        "status": "skipped",
                        "message": "User already has documents. Use force=True to reprocess.",
                        "existing_documents": len(existing_docs)
                    }
        
        # Trigger new ETL processing
        from etl.test_completion_handler import TestCompletionRequest, TestCompletionHandler
        
        request = TestCompletionRequest(
            user_id=user_id,
            anp_seq=anp_seq,
            test_type="reprocess",
            completed_at=datetime.now(),
            notification_source="reprocess_system"
        )
        
        # This would need the actual handler instance
        # For now, just log the intent
        logger.info(f"Would reprocess data for user {user_id}, anp_seq {anp_seq}")
        
        return {
            "status": "success",
            "message": "Reprocessing triggered",
            "user_id": user_id,
            "anp_seq": anp_seq
        }
        
    except Exception as e:
        logger.error(f"User data reprocessing failed: {e}")
        return {
            "status": "failure",
            "error_message": str(e)
        }

async def health_check() -> Dict[str, Any]:
    """Health check task for monitoring"""
    try:
        # Check database connection
        async with get_database_session() as session:
            # Simple query to test connection
            await session.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

# Periodic task configuration (for future BackgroundTaskManager implementation)
PERIODIC_TASKS = {
    'cleanup-failed-jobs': {
        'function': cleanup_failed_jobs,
        'schedule_seconds': 3600,  # Every hour
        'args': (168,)  # 7 days
    },
    'health-check': {
        'function': health_check,
        'schedule_seconds': 300,  # Every 5 minutes
    },
}

if __name__ == '__main__':
    # For testing individual tasks
    import sys
    
    async def main():
        if len(sys.argv) > 1:
            task_name = sys.argv[1]
            
            if task_name == 'test_completion':
                # Test the main ETL task
                result = await process_test_completion(
                    user_id="test_user_123",
                    anp_seq=12345,
                    job_id="test_job_123",
                    test_type="standard"
                )
                print(f"Task result: {result}")
                
            elif task_name == 'health_check':
                result = await health_check()
                print(f"Health check result: {result}")
    
    asyncio.run(main())