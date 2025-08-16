#!/usr/bin/env python3
"""
데이터베이스 테이블 구조 확인
"""

import asyncio
import sys
sys.path.append('.')

from database.connection import db_manager
from sqlalchemy import text

async def check_table_structure():
    print("=== 데이터베이스 테이블 구조 확인 ===")
    
    try:
        from database.connection import db_manager
        with db_manager.get_sync_session() as session:
            
            # mwd_answer_progress 테이블 구조 확인
            print("\n1. mwd_answer_progress 테이블 구조:")
            sql = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'mwd_answer_progress' 
            ORDER BY ordinal_position
            """
            result = session.execute(text(sql))
            columns = result.fetchall()
            for col in columns:
                print(f"  - {col[0]}: {col[1]}")
            
            # mwd_job 테이블 구조 확인
            print("\n2. mwd_job 테이블 구조:")
            sql = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'mwd_job' 
            ORDER BY ordinal_position
            """
            result = session.execute(text(sql))
            columns = result.fetchall()
            for col in columns:
                print(f"  - {col[0]}: {col[1]}")
            
            # 실제 데이터 샘플 확인
            print("\n3. mwd_answer_progress 샘플 데이터:")
            sql = "SELECT * FROM mwd_answer_progress WHERE anp_seq = 18240 LIMIT 1"
            result = session.execute(text(sql))
            row = result.fetchone()
            if row:
                print(f"  샘플 레코드: {dict(row._mapping)}")
            else:
                print("  데이터 없음")
                
            print("\n4. mwd_job 샘플 데이터:")
            sql = "SELECT * FROM mwd_job LIMIT 1"
            result = session.execute(text(sql))
            row = result.fetchone()
            if row:
                print(f"  샘플 레코드: {dict(row._mapping)}")
            else:
                print("  데이터 없음")
                
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_table_structure())