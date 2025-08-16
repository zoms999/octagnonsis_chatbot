#!/usr/bin/env python3
"""
anp_seq 18420에 대한 데이터 준비 상태를 디버깅하는 스크립트
"""
import asyncio
import logging
from sqlalchemy import text
from database.connection import get_sync_session

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_data_readiness():
    """anp_seq 18420에 대한 데이터 준비 상태를 상세히 분석"""
    anp_seq = 18420
    logger.info(f"🔍 Debugging data readiness for anp_seq: {anp_seq}")
    
    with get_sync_session() as session:
        # 1. mwd_score1 테이블 전체 데이터 분포 확인
        score_distribution_query = """
            SELECT sc1_step, COUNT(*) as count
            FROM mwd_score1 
            WHERE anp_seq = :anp_seq
            GROUP BY sc1_step
            ORDER BY sc1_step
        """
        result = session.execute(text(score_distribution_query), {"anp_seq": anp_seq})
        score_distribution = result.fetchall()
        
        logger.info("📊 mwd_score1 테이블 데이터 분포:")
        for row in score_distribution:
            logger.info(f"- {row.sc1_step}: {row.count}건")
        
        # 2. 핵심 데이터 존재 여부 확인
        core_data_queries = {
            "사고력(thk)": "SELECT COUNT(*) FROM mwd_score1 WHERE anp_seq = :anp_seq AND sc1_step = 'thk'",
            "역량(tal)": "SELECT COUNT(*) FROM mwd_score1 WHERE anp_seq = :anp_seq AND sc1_step = 'tal'", 
            "성향(tnd)": "SELECT COUNT(*) FROM mwd_score1 WHERE anp_seq = :anp_seq AND sc1_step = 'tnd'",
            "이미지(img)": "SELECT COUNT(*) FROM mwd_score1 WHERE anp_seq = :anp_seq AND sc1_step = 'img'"
        }
        
        logger.info("🎯 핵심 데이터 존재 여부:")
        for data_type, query in core_data_queries.items():
            result = session.execute(text(query), {"anp_seq": anp_seq})
            count = result.scalar_one_or_none()
            logger.info(f"- {data_type}: {count}건")
        
        # 3. 이미지 선호도 검사 상태 확인 (간단한 버전)
        image_preference_query = """
            SELECT 
                COUNT(*) as total_responses,
                COUNT(CASE WHEN rv_imgrcnt > 0 THEN 1 END) as positive_responses
            FROM mwd_resval 
            WHERE anp_seq = :anp_seq
        """
        result = session.execute(text(image_preference_query), {"anp_seq": anp_seq})
        image_stats = result.fetchone()
        
        logger.info("📷 이미지 선호도 검사 상태:")
        if image_stats:
            logger.info(f"- 총 응답 수: {image_stats.total_responses}")
            logger.info(f"- 긍정 응답 수: {image_stats.positive_responses}")
        else:
            logger.info("- 이미지 선호도 데이터 없음")
        
        # 4. 현재 ETL 대기 조건 시뮬레이션
        thk_count = session.execute(text("SELECT COUNT(*) FROM mwd_score1 WHERE anp_seq = :anp_seq AND sc1_step = 'thk'"), {"anp_seq": anp_seq})
        thk_count = thk_count.scalar_one_or_none()
        
        tal_count = session.execute(text("SELECT COUNT(*) FROM mwd_score1 WHERE anp_seq = :anp_seq AND sc1_step = 'tal'"), {"anp_seq": anp_seq})
        tal_count = tal_count.scalar_one_or_none()
        
        score_count = (1 if thk_count > 0 else 0) + (1 if tal_count > 0 else 0)
        
        image_result = session.execute(text("SELECT COUNT(*) FROM mwd_resval WHERE anp_seq = :anp_seq AND rv_imgrcnt > 0"), {"anp_seq": anp_seq})
        image_result = image_result.scalar_one_or_none()
        
        logger.info(f"🔍 현재 대기 조건 결과: {score_count} (2여야 통과)")
        
        if score_count < 2:
            logger.info("⚠️ 사고력 또는 역량 데이터 누락")
        else:
            logger.info("✅ 점수 데이터 준비됨")
            
        if image_result and image_result > 0:
            logger.info("✅ 이미지 선호도 데이터 준비됨")
        else:
            logger.info("⚠️ 이미지 선호도 데이터 누락")

if __name__ == "__main__":
    debug_data_readiness()