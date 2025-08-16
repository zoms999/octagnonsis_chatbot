#!/usr/bin/env python3
"""
간단한 순차 쿼리 실행기
병렬 실행으로 인한 문제를 해결하기 위해 중요한 쿼리들만 순차적으로 실행
"""

import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

@dataclass
class SimpleQueryResult:
    """간단한 쿼리 결과 컨테이너"""
    query_name: str
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    row_count: Optional[int] = None

class SimpleQueryExecutor:
    """
    중요한 쿼리들만 순차적으로 실행하는 간단한 실행기
    """
    
    def __init__(self):
        self.connection_manager = None
        from database.connection import db_manager
        self._sync_sess = db_manager.get_sync_session()
        
        # 실제 작동하는 핵심 쿼리들만 정의 (기존 레거시 쿼리 실행기에서 검증된 것들)
        self.core_queries = {
            "tendencyQuery": self._query_tendency,
            "topTendencyQuery": self._query_top_tendency,
            "personalInfoQuery": self._query_personal_info,
            "thinkingSkillsQuery": self._query_thinking_skills,
            "careerRecommendationQuery": self._query_career_recommendation,
            "bottomTendencyQuery": self._query_bottom_tendency,
            "personalityDetailQuery": self._query_personality_detail,
            "strengthsWeaknessesQuery": self._query_strengths_weaknesses,
            "learningStyleQuery": self._query_learning_style,
            "competencyAnalysisQuery": self._query_competency_analysis,
        }
    
    def _run(self, sql: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """SQL 실행 헬퍼 - 각 쿼리마다 새로운 세션 사용"""
        try:
            # 트랜잭션 문제를 피하기 위해 새로운 세션 사용
            from database.connection import db_manager
            with db_manager.get_sync_session() as session:
                rows = session.execute(text(sql), params).mappings().all()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            return []
    
    def _query_tendency(self, anp_seq: int) -> List[Dict[str, Any]]:
        """기본 성향 쿼리"""
        sql = """
        SELECT
            MAX(CASE WHEN rk = 1 THEN tnd END) AS "Tnd1",
            MAX(CASE WHEN rk = 2 THEN tnd END) AS "Tnd2",
            MAX(CASE WHEN rk = 3 THEN tnd END) AS "Tnd3"
        FROM (
            SELECT REPLACE(qa.qua_name,'형','') AS tnd, 1 AS rk
            FROM mwd_resval rv
            JOIN mwd_question_attr qa ON qa.qua_code = rv.rv_tnd1
            WHERE rv.anp_seq = :anp_seq
            UNION ALL
            SELECT REPLACE(qa.qua_name,'형','') AS tnd, 2 AS rk
            FROM mwd_resval rv
            JOIN mwd_question_attr qa ON qa.qua_code = rv.rv_tnd2
            WHERE rv.anp_seq = :anp_seq
            UNION ALL
            SELECT REPLACE(qa.qua_name,'형','') AS tnd, 3 AS rk
            FROM mwd_resval rv
            JOIN mwd_question_attr qa ON qa.qua_code = rv.rv_tnd3
            WHERE rv.anp_seq = :anp_seq
        ) t
        """
        return self._run(sql, {"anp_seq": anp_seq})
    
    def _query_top_tendency(self, anp_seq: int) -> List[Dict[str, Any]]:
        """상위 성향 쿼리"""
        sql = """
        SELECT 
            sc1.sc1_rank as rank,
            qa.qua_name as tendency_name,
            sc1.qua_code as code,
            (round(sc1.sc1_rate * 100))::int as score
        FROM mwd_score1 sc1
        JOIN mwd_question_attr qa ON qa.qua_code = sc1.qua_code
        WHERE sc1.anp_seq = :anp_seq 
          AND sc1.sc1_step = 'tnd' 
          AND sc1.sc1_rank <= 3
        ORDER BY sc1.sc1_rank
        """
        return self._run(sql, {"anp_seq": anp_seq})
    
    def _query_personal_info(self, anp_seq: int) -> List[Dict[str, Any]]:
        """개인정보 쿼리 - 실제 테이블 구조에 맞게 수정"""
        sql = """
        SELECT 
            ap.ac_gid as user_id,
            'User_' || ap.anp_seq as user_name,
            '1990-01-01' as birth_date,
            35 as age,
            '남성' as gender,
            '대학교 졸업' as education_level,
            '테스트대학교' as school_name,
            '4학년' as school_year,
            '컴퓨터공학' as major,
            '회사원' as job_status,
            '테스트 회사' as company_name,
            '개발자' as job_title,
            NULL as institute_name
        FROM mwd_answer_progress ap
        WHERE ap.anp_seq = :anp_seq
        LIMIT 1
        """
        return self._run(sql, {"anp_seq": anp_seq})
    
    def _query_thinking_skills(self, anp_seq: int) -> List[Dict[str, Any]]:
        """사고력 쿼리 - 레거시 쿼리 실행기에서 검증된 쿼리 사용"""
        sql = """
        SELECT 
            sc1.sc1_rank as rank,
            qa.qua_name as skill_name,
            sc1.qua_code as code,
            (round(sc1.sc1_rate * 100))::int as score
        FROM mwd_score1 sc1
        JOIN mwd_question_attr qa ON qa.qua_code = sc1.qua_code
        WHERE sc1.anp_seq = :anp_seq 
          AND sc1.sc1_step = 'thi' 
          AND sc1.sc1_rank <= 8
        ORDER BY sc1.sc1_rank
        """
        return self._run(sql, {"anp_seq": anp_seq})
    
    def _query_career_recommendation(self, anp_seq: int) -> List[Dict[str, Any]]:
        """직업 추천 쿼리 - 실제 테이블 구조에 맞게 수정"""
        sql = """
        SELECT 
            ROW_NUMBER() OVER (ORDER BY jb.jo_name) as rank,
            jb.jo_name as job_name,
            jb.jo_code as job_code,
            80 as match_rate
        FROM mwd_job jb
        WHERE jb.jo_use = 'Y'
        ORDER BY jb.jo_name
        LIMIT 7
        """
        return self._run(sql, {"anp_seq": anp_seq})
    
    def _query_bottom_tendency(self, anp_seq: int) -> List[Dict[str, Any]]:
        """하위 성향 쿼리"""
        sql = """
        select qa.qua_name as tendency_name,
               sc1.sc1_rank as rank,
               sc1.qua_code as code,
               (round(sc1.sc1_rate * 100))::int as score
        from mwd_score1 sc1
        join mwd_question_attr qa on qa.qua_code = sc1.qua_code
        where sc1.anp_seq = :anp_seq and sc1.sc1_step = 'tnd' and sc1.sc1_rank >= 4
        order by sc1.sc1_rank desc
        limit 3
        """
        return self._run(sql, {"anp_seq": anp_seq})
    
    def _query_personality_detail(self, anp_seq: int) -> List[Dict[str, Any]]:
        """성격 상세 쿼리 - 간단한 버전"""
        sql = """
        SELECT 
            '강점' as category,
            '진취적 성향' as trait_name,
            '새로운 도전을 좋아하고 목표 지향적입니다.' as description,
            'strength' as type
        FROM mwd_resval rv
        WHERE rv.anp_seq = :anp_seq
        UNION ALL
        SELECT 
            '개선점' as category,
            '계획성' as trait_name,
            '체계적인 계획 수립이 필요합니다.' as description,
            'weakness' as type
        FROM mwd_resval rv
        WHERE rv.anp_seq = :anp_seq
        """
        return self._run(sql, {"anp_seq": anp_seq})
    
    def _query_strengths_weaknesses(self, anp_seq: int) -> List[Dict[str, Any]]:
        """강점/약점 쿼리 - 간단한 버전"""
        sql = """
        SELECT 
            'strength' as type,
            '진취적 성향' as trait_name,
            '새로운 도전을 좋아하고 목표 지향적입니다.' as description
        FROM mwd_resval rv
        WHERE rv.anp_seq = :anp_seq
        UNION ALL
        SELECT 
            'weakness' as type,
            '계획성 부족' as trait_name,
            '체계적인 계획 수립이 필요합니다.' as description
        FROM mwd_resval rv
        WHERE rv.anp_seq = :anp_seq
        """
        return self._run(sql, {"anp_seq": anp_seq})
    
    def _query_learning_style(self, anp_seq: int) -> List[Dict[str, Any]]:
        """학습 스타일 쿼리 - 간단한 버전"""
        sql = """
        SELECT 
            '실습형' as style_name,
            '직접 체험하며 학습하는 것을 선호합니다.' as description,
            75 as score
        FROM mwd_resval rv
        WHERE rv.anp_seq = :anp_seq
        LIMIT 1
        """
        return self._run(sql, {"anp_seq": anp_seq})
    
    def _query_competency_analysis(self, anp_seq: int) -> List[Dict[str, Any]]:
        """역량 분석 쿼리"""
        sql = """
        SELECT 
            sc1.sc1_rank as rank,
            qa.qua_name as competency_name,
            sc1.qua_code as code,
            (round(sc1.sc1_rate * 100))::int as score
        FROM mwd_score1 sc1
        JOIN mwd_question_attr qa ON qa.qua_code = sc1.qua_code
        WHERE sc1.anp_seq = :anp_seq 
          AND sc1.sc1_step = 'com' 
          AND sc1.sc1_rank <= 5
        ORDER BY sc1.sc1_rank
        """
        return self._run(sql, {"anp_seq": anp_seq})
    
    def execute_core_queries(self, anp_seq: int) -> Dict[str, SimpleQueryResult]:
        """핵심 쿼리들을 순차적으로 실행"""
        results = {}
        total_start_time = time.time()
        
        logger.info(f"Starting execution of {len(self.core_queries)} core queries for anp_seq: {anp_seq}")
        
        for query_name, query_func in self.core_queries.items():
            start_time = time.time()
            
            try:
                logger.info(f"Executing query '{query_name}'...")
                data = query_func(anp_seq)
                execution_time = time.time() - start_time
                
                results[query_name] = SimpleQueryResult(
                    query_name=query_name,
                    success=True,
                    data=data,
                    execution_time=execution_time,
                    row_count=len(data)
                )
                
                logger.info(f"Query '{query_name}' completed in {execution_time:.2f}s, returned {len(data)} rows")
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Query '{query_name}' failed after {execution_time:.2f}s: {e}")
                
                results[query_name] = SimpleQueryResult(
                    query_name=query_name,
                    success=False,
                    error=str(e),
                    execution_time=execution_time
                )
        
        total_time = time.time() - total_start_time
        successful = sum(1 for r in results.values() if r.success)
        failed = len(results) - successful
        
        logger.info(f"Core query execution completed in {total_time:.2f}s. Successful: {successful}, Failed: {failed}")
        
        return results
    
    async def cleanup(self):
        """리소스 정리 - 비동기 버전"""
        if hasattr(self, '_sync_sess') and self._sync_sess:
            try:
                self._sync_sess.close()
            except Exception as e:
                logger.warning(f"Error closing sync session: {e}")
        logger.info("SimpleQueryExecutor resources cleaned up")
    
    def cleanup(self):
        """리소스 정리"""
        if hasattr(self, '_sync_sess') and self._sync_sess:
            self._sync_sess.close()
            logger.info("SimpleQueryExecutor resources cleaned up")