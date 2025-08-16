#!/usr/bin/env python3
"""
데이터 준비 상태 디버깅 스크립트
mwd_score1 테이블의 실제 데이터 상태를 확인합니다.
"""

import asyncio
import logging
from sqlalchemy import text
from database.connection import db_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_data_readiness(anp_seq: int = 18240):
    """특정 anp_seq의 데이터 준비 상태를 상세히 확인"""
    
    logger.info(f"🔍 Debugging data readiness for anp_seq: {anp_seq}")
    
    try:
        # 동기 세션 사용
        with db_manager.get_sync_session() as session:
            
            # 1. mwd_score1 테이블의 전체 데이터 확인
            query1 = """
                SELECT sc1_step, COUNT(*) as count
                FROM mwd_score1 
                WHERE anp_seq = :anp_seq
                GROUP BY sc1_step
                ORDER BY sc1_step
            """
            results1 = session.execute(text(query1), {"anp_seq": anp_seq}).fetchall()
            
            logger.info("📊 mwd_score1 테이블 데이터 분포:")
            for row in results1:
                logger.info(f"  - {row.sc1_step}: {row.count}건")
            
            if not results1:
                logger.warning("❌ mwd_score1 테이블에 해당 anp_seq 데이터가 전혀 없습니다!")
                return
            
            # 2. 핵심 데이터 존재 여부 확인
            query2 = """
                SELECT 
                    COUNT(CASE WHEN sc1_step = 'thk' THEN 1 END) as thk_count,
                    COUNT(CASE WHEN sc1_step = 'tal' THEN 1 END) as tal_count,
                    COUNT(CASE WHEN sc1_step = 'tnd' THEN 1 END) as tnd_count,
                    COUNT(CASE WHEN sc1_step = 'img' THEN 1 END) as img_count
                FROM mwd_score1 
                WHERE anp_seq = :anp_seq
            """
            result2 = session.execute(text(query2), {"anp_seq": anp_seq}).fetchone()
            
            logger.info("🎯 핵심 데이터 존재 여부:")
            logger.info(f"  - 사고력(thk): {result2.thk_count}건")
            logger.info(f"  - 역량(tal): {result2.tal_count}건") 
            logger.info(f"  - 성향(tnd): {result2.tnd_count}건")
            logger.info(f"  - 이미지(img): {result2.img_count}건")
            
            # 3. mwd_resval 테이블의 이미지 관련 데이터 확인
            query3 = """
                SELECT rv_imgtcnt, rv_imgrcnt, rv_imgresrate
                FROM mwd_resval 
                WHERE anp_seq = :anp_seq
            """
            result3 = session.execute(text(query3), {"anp_seq": anp_seq}).fetchone()
            
            if result3:
                logger.info("📷 이미지 선호도 검사 상태:")
                logger.info(f"  - 총 이미지 수: {result3.rv_imgtcnt}")
                logger.info(f"  - 응답 수: {result3.rv_imgrcnt}")
                logger.info(f"  - 응답률: {result3.rv_imgresrate}")
            else:
                logger.warning("❌ mwd_resval 테이블에 해당 anp_seq 데이터가 없습니다!")
            
            # 4. 현재 대기 조건 테스트
            current_condition_query = """
                SELECT COUNT(DISTINCT sc1_step) as step_count
                FROM mwd_score1 
                WHERE anp_seq = :anp_seq AND sc1_step IN ('thk', 'tal')
            """
            current_result = session.execute(text(current_condition_query), {"anp_seq": anp_seq}).scalar_one_or_none()
            
            logger.info(f"🔍 현재 대기 조건 결과: {current_result} (2여야 통과)")
            
            # 5. 권장 대기 조건 제안
            if result2.thk_count > 0 and result2.tal_count > 0:
                logger.info("✅ 사고력과 역량 데이터 모두 준비됨")
            else:
                logger.warning("⚠️ 사고력 또는 역량 데이터 누락")
                
            if result3 and result3.rv_imgrcnt > 0:
                logger.info("✅ 이미지 선호도 데이터 준비됨")
            else:
                logger.warning("⚠️ 이미지 선호도 데이터 누락")
                
    except Exception as e:
        logger.error(f"❌ 데이터 확인 중 오류 발생: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(debug_data_readiness())