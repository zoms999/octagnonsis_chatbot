#!/usr/bin/env python3
"""
Check raw data for anp_seq
"""

import asyncio
import sys
sys.path.append('.')
from etl.legacy_query_executor import AptitudeTestQueries

async def check_raw_data():
    # 동기 세션으로 직접 쿼리 실행
    aptitude_queries = AptitudeTestQueries(None)  # 내부에서 동기 세션 생성
    
    # 요청에서 사용된 user_id 확인
    user_id = "5294802c-2219-4651-a4a5-a9a5dae7546f"
    print(f'user_id {user_id}에 대한 데이터 확인:')
    
    try:
        # 사용자 매핑 테이블 확인
        sql = 'SELECT * FROM chat_users WHERE user_id = :user_id'
        rows = aptitude_queries._run(sql, {'user_id': user_id})
        print(f'  chat_users 테이블: {len(rows)}개 결과')
        if rows:
            print(f'    결과: {rows[0]}')
            anp_seq = rows[0].get('anp_seq')
            if anp_seq:
                print(f'    anp_seq: {anp_seq}')
                
                print(f'\n  anp_seq {anp_seq}에 대한 상세 데이터:')
                
                # 기본 성향 쿼리 테스트
                result = aptitude_queries._query_tendency(anp_seq)
                print(f'    Tendency Query: {len(result)}개 결과')
                if result:
                    print(f'      결과: {result[0]}')
                
                # 개인정보 쿼리 테스트  
                result = aptitude_queries._query_personal_info(anp_seq)
                print(f'    Personal Info Query: {len(result)}개 결과')
                if result:
                    print(f'      결과: {result[0]}')
                    
                # 저장된 문서 확인
                sql = 'SELECT doc_type, COUNT(*) as cnt FROM chat_documents WHERE user_id = :user_id GROUP BY doc_type'
                doc_rows = aptitude_queries._run(sql, {'user_id': user_id})
                print(f'    저장된 문서 타입별 개수:')
                for doc_row in doc_rows:
                    print(f'      {doc_row["doc_type"]}: {doc_row["cnt"]}개')
        else:
            print('    사용자를 찾을 수 없습니다.')
            
        # 전체 사용자 목록 확인
        sql = 'SELECT user_id, anp_seq, name FROM chat_users LIMIT 5'
        rows = aptitude_queries._run(sql, {})
        print(f'\n  등록된 사용자들 (처음 5개):')
        for row in rows:
            print(f'    user_id: {row["user_id"]}, anp_seq: {row["anp_seq"]}, name: {row["name"]}')
        
    except Exception as e:
        print(f'에러 발생: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_raw_data())