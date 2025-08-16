#!/usr/bin/env python3
"""
ETL 작업 상태 확인 스크립트
"""
import logging
from sqlalchemy import text
from database.connection import get_sync_session

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

def check_etl_job_status():
    """ETL 작업 상태 확인"""
    anp_seq = 18420
    
    logger.info(f"🔍 Checking ETL job status for anp_seq: {anp_seq}")
    
    with get_sync_session() as session:
        # 1. ETL 작업 추적 테이블 확인
        job_query = """
            SELECT job_id, status, started_at, updated_at, error_message, completed_at
            FROM chat_etl_jobs 
            WHERE anp_seq = :anp_seq
            ORDER BY started_at DESC
            LIMIT 5
        """
        
        try:
            result = session.execute(text(job_query), {"anp_seq": anp_seq})
            jobs = result.fetchall()
            
            logger.info("📊 Recent ETL jobs:")
            for job in jobs:
                logger.info(f"- Job ID: {job.job_id}")
                logger.info(f"  Status: {job.status}")
                logger.info(f"  Started: {job.started_at}")
                logger.info(f"  Updated: {job.updated_at}")
                logger.info(f"  Completed: {job.completed_at}")
                if job.error_message:
                    logger.info(f"  Error: {job.error_message}")
                logger.info("")
                
        except Exception as e:
            logger.error(f"Error checking ETL jobs: {e}")
        
        # 2. 문서 저장 상태 확인
        doc_query = """
            SELECT COUNT(*) as doc_count, 
                   COUNT(DISTINCT doc_type) as doc_types
            FROM rag_documents 
            WHERE anp_seq = :anp_seq
        """
        
        try:
            result = session.execute(text(doc_query), {"anp_seq": anp_seq})
            doc_stats = result.fetchone()
            
            logger.info("📄 Document storage status:")
            logger.info(f"- Total documents: {doc_stats.doc_count}")
            logger.info(f"- Document types: {doc_stats.doc_types}")
            
        except Exception as e:
            logger.error(f"Error checking documents: {e}")

if __name__ == "__main__":
    check_etl_job_status()