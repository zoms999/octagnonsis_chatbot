#!/usr/bin/env python3
"""
완전한 ETL 파이프라인 테스트 (실제 데이터 포함)
"""
import asyncio
import logging
from etl.legacy_query_executor import LegacyQueryExecutor
from etl.document_transformer import DocumentTransformer
from database.connection import get_async_session

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_complete_etl_pipeline():
    """완전한 ETL 파이프라인 테스트"""
    anp_seq = 18240  # 실제 데이터가 있는 사용자
    
    logger.info("🚀 Starting Complete ETL Pipeline Test")
    logger.info(f"Testing with anp_seq: {anp_seq} (실제 데이터 포함)")
    
    try:
        # 1. Legacy Query Execution 테스트
        logger.info("📊 Step 1: Executing legacy queries...")
        
        session = await get_async_session()
        try:
            executor = LegacyQueryExecutor()
            results = await executor.execute_all_queries_async(session, anp_seq)
        finally:
            await session.close()
        
        # 결과 요약
        total_queries = len(results)
        successful_queries = sum(1 for result in results.values() if result.success)
        failed_queries = total_queries - successful_queries
        
        logger.info(f"Query execution completed: {successful_queries}/{total_queries} successful")
        
        # 실제 데이터가 있는 쿼리들 확인
        data_rich_queries = []
        for query_name, result in results.items():
            if result.success and result.data and len(result.data) > 0:
                data_rich_queries.append(f"{query_name}({len(result.data)}건)")
        
        logger.info(f"데이터가 있는 쿼리들: {', '.join(data_rich_queries[:10])}...")
        
        # 2. Document Transformation 테스트
        logger.info("📝 Step 2: Transforming documents with real data...")
        
        # 결과를 DocumentTransformer가 기대하는 형식으로 변환
        formatted_results = {}
        for query_name, result in results.items():
            if result.success and result.data:
                formatted_results[query_name] = result.data
            else:
                formatted_results[query_name] = []
        
        transformer = DocumentTransformer()
        documents = await transformer.transform_all_documents(formatted_results)
        
        # 문서 분석
        doc_types = set()
        doc_type_counts = {}
        real_data_docs = 0
        
        for doc in documents:
            doc_types.add(doc.doc_type)
            doc_type_counts[doc.doc_type] = doc_type_counts.get(doc.doc_type, 0) + 1
            
            # 실제 데이터가 포함된 문서인지 확인
            if not ("데이터가 아직 준비되지" in str(doc.content) or "데이터 준비 중" in doc.summary_text):
                real_data_docs += 1
        
        logger.info("✅ ETL Pipeline Test completed successfully!")
        logger.info("📊 Final Results:")
        logger.info(f"- Total queries executed: {total_queries}")
        logger.info(f"- Successful queries: {successful_queries}")
        logger.info(f"- Failed queries: {failed_queries}")
        logger.info(f"- Documents created: {len(documents)}")
        logger.info(f"- Document types: {len(doc_types)}")
        logger.info(f"- Documents with real data: {real_data_docs}")
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
        
        # 가상 질문 생성 확인
        docs_with_questions = sum(1 for doc in documents if doc.metadata.get('hypothetical_questions'))
        logger.info(f"- Documents with hypothetical questions: {docs_with_questions}/{len(documents)}")
        
        # 샘플 문서 내용 출력
        logger.info("\n📄 Sample Document Contents:")
        for doc_type in ['USER_PROFILE', 'PERSONALITY_PROFILE', 'THINKING_SKILLS']:
            sample_doc = next((doc for doc in documents if doc.doc_type == doc_type), None)
            if sample_doc:
                logger.info(f"\n{doc_type}:")
                logger.info(f"  Summary: {sample_doc.summary_text}")
                logger.info(f"  Content keys: {list(sample_doc.content.keys()) if isinstance(sample_doc.content, dict) else 'Non-dict content'}")
                questions = sample_doc.metadata.get('hypothetical_questions', [])
                logger.info(f"  Hypothetical questions: {questions[:2]}...")
        
        return {
            "status": "success",
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "documents_created": len(documents),
            "document_types": len(doc_types),
            "real_data_documents": real_data_docs,
            "document_type_distribution": doc_type_counts,
            "missing_types": list(missing_types),
            "docs_with_questions": docs_with_questions
        }
        
    except Exception as e:
        logger.error(f"❌ ETL Pipeline Test failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(test_complete_etl_pipeline())