#!/usr/bin/env python3
"""
개선된 ETL 로직으로 직접 처리하는 스크립트
"""
import asyncio
import logging
from datetime import datetime
from sqlalchemy import text
from database.connection import get_sync_session, get_async_session
from etl.simple_query_executor import SimpleQueryExecutor
from etl.document_transformer import DocumentTransformer

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

async def trigger_improved_etl():
    """개선된 ETL 로직으로 직접 처리"""
    anp_seq = 18420
    job_id = "7c9cd4c3-33b0-4403-a426-7e36bd830825"
    
    logger.info(f"🚀 Starting improved ETL processing for anp_seq: {anp_seq}")
    
    try:
        # 1. 작업 상태를 processing으로 업데이트
        with get_sync_session() as session:
            update_query = """
                UPDATE chat_etl_jobs 
                SET status = 'processing_queries',
                    current_step = 'query_execution',
                    updated_at = CURRENT_TIMESTAMP
                WHERE job_id = :job_id
            """
            session.execute(text(update_query), {"job_id": job_id})
            session.commit()
        
        # 2. Query Execution
        logger.info("📊 Step 1: Executing queries...")
        executor = SimpleQueryExecutor()
        results = executor.execute_core_queries(anp_seq)
        
        # 결과 변환
        formatted_results = {}
        for query_name, result in results.items():
            if result.success and result.data:
                formatted_results[query_name] = result.data
            else:
                formatted_results[query_name] = []
        
        logger.info(f"Query results: {len(formatted_results)} queries executed")
        
        # 3. 작업 상태 업데이트
        with get_sync_session() as session:
            update_query = """
                UPDATE chat_etl_jobs 
                SET status = 'transforming_documents',
                    current_step = 'document_transformation',
                    progress_percentage = 30,
                    updated_at = CURRENT_TIMESTAMP
                WHERE job_id = :job_id
            """
            session.execute(text(update_query), {"job_id": job_id})
            session.commit()
        
        # 4. Document Transformation
        logger.info("📝 Step 2: Transforming documents...")
        transformer = DocumentTransformer()
        documents = await transformer.transform_all_documents(formatted_results)
        
        # 문서 타입별 분포 계산
        doc_types = set()
        doc_type_counts = {}
        for doc in documents:
            doc_types.add(doc.doc_type)
            doc_type_counts[doc.doc_type] = doc_type_counts.get(doc.doc_type, 0) + 1
        
        # 5. 작업 완료 상태 업데이트
        with get_sync_session() as session:
            update_query = """
                UPDATE chat_etl_jobs 
                SET status = 'completed',
                    current_step = 'completed',
                    progress_percentage = 100,
                    completed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP,
                    documents_created = :doc_types
                WHERE job_id = :job_id
            """
            session.execute(text(update_query), {
                "job_id": job_id,
                "doc_types": list(doc_types)
            })
            session.commit()
        
        logger.info("✅ ETL processing completed successfully!")
        logger.info("📊 Final Results:")
        logger.info(f"- Documents created: {len(documents)}")
        logger.info(f"- Document types: {len(doc_types)}")
        logger.info(f"- Document type distribution: {doc_type_counts}")
        
        # 예상되는 7가지 문서 타입 확인
        expected_types = {
            'USER_PROFILE', 'PERSONALITY_PROFILE', 'THINKING_SKILLS', 
            'CAREER_RECOMMENDATIONS', 'COMPETENCY_ANALYSIS', 'LEARNING_STYLE', 
            'PREFERENCE_ANALYSIS'
        }
        
        missing_types = expected_types - doc_types
        if missing_types:
            logger.warning(f"Missing document types: {missing_types}")
        else:
            logger.info("✅ All 7 document types successfully created!")
        
        return {
            "status": "success",
            "job_id": job_id,
            "documents_created": len(documents),
            "document_types": len(doc_types),
            "document_type_distribution": doc_type_counts,
            "missing_types": list(missing_types)
        }
        
    except Exception as e:
        logger.error(f"❌ ETL processing failed: {e}", exc_info=True)
        
        # 실패 상태 업데이트
        with get_sync_session() as session:
            update_query = """
                UPDATE chat_etl_jobs 
                SET status = 'failed',
                    error_message = :error_message,
                    error_type = 'processing_error',
                    completed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE job_id = :job_id
            """
            session.execute(text(update_query), {
                "job_id": job_id,
                "error_message": str(e)
            })
            session.commit()
        
        raise
    finally:
        # Cleanup
        if 'executor' in locals():
            executor.cleanup()

if __name__ == "__main__":
    asyncio.run(trigger_improved_etl())