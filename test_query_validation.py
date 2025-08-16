#!/usr/bin/env python3
"""
Test query validation fixes
"""

import asyncio
import sys
sys.path.append('.')
from etl.legacy_query_executor import LegacyQueryExecutor
from database.connection import db_manager

async def test_queries():
    executor = LegacyQueryExecutor()
    
    try:
        async with db_manager.get_async_session() as session:
            results = await executor.execute_all_queries_async(session, 12345)
            
            failed_queries = []
            successful_queries = []
            
            for name, result in results.items():
                if result.success:
                    successful_queries.append(name)
                else:
                    failed_queries.append((name, result.error))
            
            print(f'성공한 쿼리: {len(successful_queries)}개')
            print(f'실패한 쿼리: {len(failed_queries)}개')
            
            if failed_queries:
                print('\n실패한 쿼리들:')
                for name, error in failed_queries:
                    print(f'  - {name}: {error}')
            
            if successful_queries:
                print(f'\n성공한 쿼리들 (처음 10개):')
                for name in successful_queries[:10]:
                    print(f'  - {name}')
                    
    finally:
        await executor.close()

if __name__ == "__main__":
    asyncio.run(test_queries())