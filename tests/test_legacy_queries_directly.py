#!/usr/bin/env python3
"""
Legacy Query Executor의 실제 쿼리들을 직접 테스트
"""
import logging
from sqlalchemy import text
from database.connection import get_sync_session

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

def test_legacy_queries_directly():
    """Legacy 쿼리들을 직접 실행해서 결과 확인"""
    anp_seq = 18240
    
    logger.info(f"🔍 Testing legacy queries directly for anp_seq: {anp_seq}")
    
    with get_sync_session() as session:
        # 1. 사고력 쿼리 테스트
        logger.info("🧠 Testing thinking skills query...")
        
        thinking_query = """
        select qa.qua_name as skill_name,
               coalesce(round(sc1.sc1_rate * 100), 0)::int as score,
               coalesce(round(sc1.sc1_rate * 100), 0)::int as percentile
        from mwd_score1 sc1
        join mwd_question_attr qa on qa.qua_code = sc1.qua_code
        where sc1.anp_seq = :anp_seq and sc1.sc1_step = 'thk'
        order by qa.qua_name
        """
        
        result = session.execute(text(thinking_query), {"anp_seq": anp_seq})
        thinking_results = result.fetchall()
        
        logger.info(f"사고력 쿼리 결과: {len(thinking_results)}건")
        for row in thinking_results:
            logger.info(f"  - {row.skill_name}: {row.score}점 ({row.percentile}%)")
        
        # 2. 역량 분석 쿼리 테스트
        logger.info("\n💪 Testing competency analysis query...")
        
        # legacy_query_executor.py의 _query_competency_analysis 쿼리 확인
        competency_query = """
        SELECT 
            qa.qua_name as competency_name,
            sc1.sc1_score as score,
            sc1.sc1_rank as rank,
            ROUND(sc1.sc1_rate * 100, 1) as percentile
        FROM mwd_score1 sc1
        JOIN mwd_question_attr qa ON sc1.qua_code = qa.qua_code
        WHERE sc1.anp_seq = :anp_seq AND sc1.sc1_step = 'tal'
        ORDER BY sc1.sc1_rank ASC
        """
        
        result = session.execute(text(competency_query), {"anp_seq": anp_seq})
        competency_results = result.fetchall()
        
        logger.info(f"역량 분석 쿼리 결과: {len(competency_results)}건")
        for i, row in enumerate(competency_results[:10]):  # 상위 10개만 출력
            logger.info(f"  - {row.competency_name}: {row.score}점 (순위: {row.rank}, 백분위: {row.percentile}%)")
        
        # 3. Legacy Query Executor 클래스를 직접 사용해서 테스트
        logger.info("\n🔧 Testing with actual LegacyQueryExecutor...")
        
        from etl.legacy_query_executor import AptitudeTestQueries
        
        # 임시 세션 객체 (실제로는 사용되지 않음)
        queries = AptitudeTestQueries(session)
        
        # 사고력 쿼리 실행
        thinking_results_legacy = queries._query_thinking_skills(anp_seq)
        logger.info(f"Legacy 사고력 쿼리 결과: {len(thinking_results_legacy)}건")
        
        # 역량 쿼리 실행
        competency_results_legacy = queries._query_competency_analysis(anp_seq)
        logger.info(f"Legacy 역량 쿼리 결과: {len(competency_results_legacy)}건")
        
        # 4. Simple Query Executor와 비교
        logger.info("\n⚡ Testing with SimpleQueryExecutor...")
        
        from etl.simple_query_executor import SimpleQueryExecutor
        simple_executor = SimpleQueryExecutor()
        
        simple_results = simple_executor.execute_core_queries(anp_seq)
        
        thinking_simple = simple_results.get("thinkingSkillsQuery")
        competency_simple = simple_results.get("competencyAnalysisQuery")
        
        logger.info(f"Simple 사고력 쿼리 결과: {len(thinking_simple.data) if thinking_simple and thinking_simple.data else 0}건")
        logger.info(f"Simple 역량 쿼리 결과: {len(competency_simple.data) if competency_simple and competency_simple.data else 0}건")
        
        # Cleanup
        simple_executor.cleanup()
        
        return {
            "direct_thinking": len(thinking_results),
            "direct_competency": len(competency_results),
            "legacy_thinking": len(thinking_results_legacy),
            "legacy_competency": len(competency_results_legacy),
            "simple_thinking": len(thinking_simple.data) if thinking_simple and thinking_simple.data else 0,
            "simple_competency": len(competency_simple.data) if competency_simple and competency_simple.data else 0
        }

if __name__ == "__main__":
    test_legacy_queries_directly()