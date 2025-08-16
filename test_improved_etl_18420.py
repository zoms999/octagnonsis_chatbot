#!/usr/bin/env python3
"""
anp_seq 18420에 대한 개선된 ETL 프로세스 테스트
"""
import asyncio
import logging
from etl.simple_query_executor import SimpleQueryExecutor
from etl.document_transformer import DocumentTransformer

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_improved_etl():
    """개선된 ETL 프로세스 테스트"""
    anp_seq = 18420
    
    logger.info("🚀 Starting Improved ETL Test for anp_seq 18420")
    logger.info(f"Testing with anp_seq: {anp_seq}")
    
    try:
        # 1. Query Execution 테스트
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
        
        # 2. Document Transformation 테스트
        logger.info("📝 Step 2: Transforming documents...")
        transformer = DocumentTransformer()
        documents = await transformer.transform_all_documents(formatted_results)
        
        # 문서 타입별 분포 계산
        doc_types = set()
        doc_type_counts = {}
        for doc in documents:
            doc_types.add(doc.doc_type)
            doc_type_counts[doc.doc_type] = doc_type_counts.get(doc.doc_type, 0) + 1
        
        logger.info("✅ ETL Test completed successfully!")
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
            logger.warning(f"⚠️ Missing document types: {missing_types}")
        else:
            logger.info("✅ All 7 document types successfully created!")
        
        return {
            "status": "success",
            "documents_created": len(documents),
            "document_types": len(doc_types),
            "document_type_distribution": doc_type_counts,
            "missing_types": list(missing_types)
        }
        
    except Exception as e:
        logger.error(f"❌ ETL Test failed: {e}", exc_info=True)
        raise
    finally:
        # Cleanup
        if 'executor' in locals():
            executor.cleanup()

if __name__ == "__main__":
    asyncio.run(test_improved_etl())