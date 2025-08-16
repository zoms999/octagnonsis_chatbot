#!/usr/bin/env python3
"""
데이터 무결성 검증 스크립트
mwd_score1과 mwd_question_attr 테이블 간의 참조 무결성 문제를 진단합니다.
"""
import logging
from sqlalchemy import text
from database.connection import get_sync_session

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

def diagnose_data_integrity():
    """데이터 무결성 문제 진단"""
    anp_seq = 18240
    
    logger.info(f"🔍 Diagnosing data integrity for anp_seq: {anp_seq}")
    
    with get_sync_session() as session:
        # 1. mwd_score1 테이블의 데이터 현황 확인
        logger.info("📊 Step 1: mwd_score1 테이블 데이터 현황")
        
        score_summary_query = """
            SELECT 
                sc1_step,
                COUNT(*) as count,
                COUNT(DISTINCT qua_code) as unique_codes
            FROM mwd_score1 
            WHERE anp_seq = :anp_seq
            GROUP BY sc1_step
            ORDER BY sc1_step
        """
        
        result = session.execute(text(score_summary_query), {"anp_seq": anp_seq})
        score_data = result.fetchall()
        
        for row in score_data:
            logger.info(f"- {row.sc1_step}: {row.count}건 (고유 코드 {row.unique_codes}개)")
        
        # 2. 사고력(thk) 데이터의 참조 무결성 검증
        logger.info("\n🧠 Step 2: 사고력(thk) 데이터 참조 무결성 검증")
        
        thk_integrity_query = """
            SELECT 
                sc1.qua_code,
                COUNT(*) as score_count,
                CASE WHEN qa.qua_code IS NULL THEN 'MISSING' ELSE 'EXISTS' END as attr_status,
                qa.qua_name
            FROM mwd_score1 sc1
            LEFT JOIN mwd_question_attr qa ON sc1.qua_code = qa.qua_code
            WHERE sc1.anp_seq = :anp_seq AND sc1.sc1_step = 'thk'
            GROUP BY sc1.qua_code, qa.qua_code, qa.qua_name
            ORDER BY sc1.qua_code
        """
        
        result = session.execute(text(thk_integrity_query), {"anp_seq": anp_seq})
        thk_data = result.fetchall()
        
        missing_thk_codes = []
        for row in thk_data:
            status_icon = "❌" if row.attr_status == 'MISSING' else "✅"
            logger.info(f"{status_icon} qua_code: {row.qua_code} ({row.score_count}건) - {row.qua_name or 'NAME_MISSING'}")
            if row.attr_status == 'MISSING':
                missing_thk_codes.append(row.qua_code)
        
        # 3. 역량(tal) 데이터의 참조 무결성 검증
        logger.info("\n💪 Step 3: 역량(tal) 데이터 참조 무결성 검증")
        
        tal_integrity_query = """
            SELECT 
                sc1.qua_code,
                COUNT(*) as score_count,
                CASE WHEN qa.qua_code IS NULL THEN 'MISSING' ELSE 'EXISTS' END as attr_status,
                qa.qua_name
            FROM mwd_score1 sc1
            LEFT JOIN mwd_question_attr qa ON sc1.qua_code = qa.qua_code
            WHERE sc1.anp_seq = :anp_seq AND sc1.sc1_step = 'tal'
            GROUP BY sc1.qua_code, qa.qua_code, qa.qua_name
            ORDER BY sc1.qua_code
        """
        
        result = session.execute(text(tal_integrity_query), {"anp_seq": anp_seq})
        tal_data = result.fetchall()
        
        missing_tal_codes = []
        for row in tal_data:
            status_icon = "❌" if row.attr_status == 'MISSING' else "✅"
            logger.info(f"{status_icon} qua_code: {row.qua_code} ({row.score_count}건) - {row.qua_name or 'NAME_MISSING'}")
            if row.attr_status == 'MISSING':
                missing_tal_codes.append(row.qua_code)
        
        # 4. 실제 JOIN 쿼리 테스트
        logger.info("\n🔗 Step 4: 실제 JOIN 쿼리 결과 테스트")
        
        # 사고력 JOIN 테스트
        thk_join_query = """
            SELECT qa.qua_name as skill_name, sc1.sc1_score as score
            FROM mwd_score1 sc1
            JOIN mwd_question_attr qa ON qa.qua_code = sc1.qua_code
            WHERE sc1.anp_seq = :anp_seq AND sc1.sc1_step = 'thk'
            ORDER BY sc1.sc1_score DESC
        """
        
        result = session.execute(text(thk_join_query), {"anp_seq": anp_seq})
        thk_join_results = result.fetchall()
        logger.info(f"사고력 JOIN 결과: {len(thk_join_results)}건")
        
        # 역량 JOIN 테스트
        tal_join_query = """
            SELECT qa.qua_name as competency_name, sc1.sc1_score as score
            FROM mwd_score1 sc1
            JOIN mwd_question_attr qa ON qa.qua_code = sc1.qua_code
            WHERE sc1.anp_seq = :anp_seq AND sc1.sc1_step = 'tal'
            ORDER BY sc1.sc1_score DESC
        """
        
        result = session.execute(text(tal_join_query), {"anp_seq": anp_seq})
        tal_join_results = result.fetchall()
        logger.info(f"역량 JOIN 결과: {len(tal_join_results)}건")
        
        # 5. 요약 및 권장사항
        logger.info("\n📋 Step 5: 진단 요약")
        logger.info(f"- 사고력 누락 코드: {len(missing_thk_codes)}개 {missing_thk_codes}")
        logger.info(f"- 역량 누락 코드: {len(missing_tal_codes)}개 {missing_tal_codes}")
        logger.info(f"- 사고력 JOIN 성공: {len(thk_join_results)}건")
        logger.info(f"- 역량 JOIN 성공: {len(tal_join_results)}건")
        
        if missing_thk_codes or missing_tal_codes:
            logger.warning("⚠️ 데이터 무결성 문제 발견!")
            logger.warning("mwd_question_attr 테이블에 누락된 qua_code들이 있습니다.")
            logger.warning("이는 상위 시스템의 데이터 생성 과정에서 발생한 문제로 보입니다.")
        else:
            logger.info("✅ 데이터 무결성 검증 통과!")
        
        return {
            "missing_thk_codes": missing_thk_codes,
            "missing_tal_codes": missing_tal_codes,
            "thk_join_count": len(thk_join_results),
            "tal_join_count": len(tal_join_results)
        }

if __name__ == "__main__":
    diagnose_data_integrity()