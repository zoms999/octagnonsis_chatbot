#!/usr/bin/env python3
"""
간단한 ETL 테스트
"""

import asyncio
import sys
sys.path.append('.')

from etl.simple_query_executor import SimpleQueryExecutor

async def test_simple_etl():
    print("=== 간단한 ETL 테스트 ===")
    
    anp_seq = 18240
    print(f"anp_seq {anp_seq}에 대한 핵심 쿼리 실행 테스트")
    
    try:
        # 간단한 실행기 테스트
        executor = SimpleQueryExecutor()
        
        # 비동기로 실행
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None, executor.execute_core_queries, anp_seq
        )
        
        print(f"\n✅ 쿼리 실행 완료: {len(results)}개 쿼리")
        
        successful = 0
        failed = 0
        
        for query_name, result in results.items():
            status = "✅" if result.success else "❌"
            row_count = result.row_count if result.success else 0
            exec_time = result.execution_time or 0
            
            print(f"{status} {query_name}: {row_count}행, {exec_time:.2f}초")
            
            if result.success:
                successful += 1
            else:
                failed += 1
                if result.error:
                    print(f"    에러: {result.error}")
        
        print(f"\n📊 결과 요약:")
        print(f"  성공: {successful}개")
        print(f"  실패: {failed}개")
        
        if successful > 0:
            print("\n✅ 핵심 데이터 추출 성공! ETL 파이프라인이 정상 작동할 것입니다.")
        else:
            print("\n❌ 모든 쿼리가 실패했습니다. 데이터베이스 연결을 확인하세요.")
        
        executor.cleanup()
        
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple_etl())