#!/usr/bin/env python3
"""
멈춰있는 ETL 작업을 수정하는 스크립트
"""
import logging
from sqlalchemy import text
from database.connection import get_sync_session

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_stuck_etl_job():
    """멈춰있는 ETL 작업 수정"""
    anp_seq = 18420
    job_id = "557006d3-2be3-4f3c-8992-4a9ac81c62c2"
    
    logger.info(f"🔧 Fixing stuck ETL job for anp_seq: {anp_seq}")
    
    with get_sync_session() as session:
        # 1. 멈춰있는 작업을 실패로 표시
        update_query = """
            UPDATE chat_etl_jobs 
            SET status = 'failed',
                error_message = 'Job stuck in processing_queries - manually terminated',
                error_type = 'timeout',
                failed_stage = 'data_readiness_check',
                completed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE job_id = :job_id AND anp_seq = :anp_seq
        """
        
        try:
            result = session.execute(text(update_query), {
                "job_id": job_id, 
                "anp_seq": anp_seq
            })
            session.commit()
            
            logger.info(f"✅ Updated stuck job status: {result.rowcount} rows affected")
            
        except Exception as e:
            logger.error(f"Error updating job status: {e}")
            session.rollback()
            return False
        
        # 2. 새로운 ETL 작업 생성 (수정된 로직 적용)
        logger.info("🚀 Creating new ETL job with improved logic...")
        
        # 새 작업 ID 생성
        import uuid
        new_job_id = str(uuid.uuid4())
        
        insert_query = """
            INSERT INTO chat_etl_jobs (
                job_id, user_id, anp_seq, status, current_step,
                started_at, updated_at
            ) VALUES (
                :job_id, 
                (SELECT user_id FROM chat_etl_jobs WHERE anp_seq = :anp_seq LIMIT 1),
                :anp_seq, 
                'pending', 
                'initialization',
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
        """
        
        try:
            result = session.execute(text(insert_query), {
                "job_id": new_job_id,
                "anp_seq": anp_seq
            })
            session.commit()
            
            logger.info(f"✅ Created new ETL job: {new_job_id}")
            return new_job_id
            
        except Exception as e:
            logger.error(f"Error creating new job: {e}")
            session.rollback()
            return False

if __name__ == "__main__":
    fix_stuck_etl_job()