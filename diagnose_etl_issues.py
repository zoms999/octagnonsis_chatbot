#!/usr/bin/env python3
"""
Diagnose ETL Issues
Properly diagnose the ETL data and connection issues
"""

import asyncio
import logging
from typing import Dict, Any, List
from sqlalchemy import text

logger = logging.getLogger(__name__)

async def diagnose_etl_data_issues():
    """
    Diagnose why many queries are returning no data
    """
    from database.connection import db_manager
    
    # Test queries to check data availability
    test_queries = {
        "check_anp_seq_18240": "SELECT COUNT(*) as count FROM mwd_answer_progress WHERE anp_seq = 18240",
        "check_resval_18240": "SELECT COUNT(*) as count FROM mwd_resval WHERE anp_seq = 18240", 
        "check_score1_18240": "SELECT COUNT(*) as count FROM mwd_score1 WHERE anp_seq = 18240",
        "check_score1_tnd": "SELECT COUNT(*) as count FROM mwd_score1 WHERE anp_seq = 18240 AND sc1_step = 'tnd'",
        "check_score1_thi": "SELECT COUNT(*) as count FROM mwd_score1 WHERE anp_seq = 18240 AND sc1_step = 'thi'",
        "check_score1_com": "SELECT COUNT(*) as count FROM mwd_score1 WHERE anp_seq = 18240 AND sc1_step = 'com'",
        "check_question_attr": "SELECT COUNT(*) as count FROM mwd_question_attr",
        "check_job_table": "SELECT COUNT(*) as count FROM mwd_job WHERE jo_use = 'Y'",
        "sample_anp_seqs": "SELECT anp_seq, COUNT(*) FROM mwd_answer_progress GROUP BY anp_seq ORDER BY anp_seq DESC LIMIT 5",
        "sample_score1_data": "SELECT anp_seq, sc1_step, COUNT(*) FROM mwd_score1 GROUP BY anp_seq, sc1_step ORDER BY anp_seq DESC LIMIT 10"
    }
    
    results = {}
    
    # Use the proper context manager
    async with db_manager.get_async_session() as session:
        for query_name, sql in test_queries.items():
            try:
                result = await session.execute(text(sql))
                if "sample_" in query_name:
                    # For sample queries, get all rows
                    rows = result.fetchall()
                    results[query_name] = [dict(row._mapping) for row in rows]
                else:
                    # For count queries, get single value
                    row = result.fetchone()
                    count = row[0] if row else 0
                    results[query_name] = count
                logger.info(f"{query_name}: {results[query_name]}")
            except Exception as e:
                logger.error(f"Error executing {query_name}: {e}")
                results[query_name] = f"ERROR: {e}"
    
    return results

async def test_simple_query_executor():
    """Test the SimpleQueryExecutor with anp_seq 18240"""
    from etl.simple_query_executor import SimpleQueryExecutor
    
    executor = SimpleQueryExecutor()
    try:
        logger.info("Testing SimpleQueryExecutor with anp_seq 18240...")
        results = executor.execute_core_queries(18240)
        
        print("\n=== SimpleQueryExecutor Results ===")
        for query_name, result in results.items():
            status = "SUCCESS" if result.success else "FAILED"
            row_count = result.row_count if result.success else 0
            print(f"{query_name}: {status} ({row_count} rows)")
            
            if result.success and result.data and len(result.data) > 0:
                print(f"  Sample data: {result.data[0]}")
            elif not result.success:
                print(f"  Error: {result.error}")
        
        return results
        
    finally:
        executor.cleanup()

async def check_connection_leak():
    """Check for connection leaks by monitoring active connections"""
    from database.connection import db_manager
    
    print("\n=== Connection Leak Check ===")
    
    # Check current connection count
    async with db_manager.get_async_session() as session:
        try:
            result = await session.execute(text("""
                SELECT count(*) as active_connections 
                FROM pg_stat_activity 
                WHERE state = 'active' AND datname = current_database()
            """))
            row = result.fetchone()
            active_connections = row[0] if row else 0
            print(f"Active database connections: {active_connections}")
            
            # Check for idle connections
            result = await session.execute(text("""
                SELECT count(*) as idle_connections 
                FROM pg_stat_activity 
                WHERE state = 'idle' AND datname = current_database()
            """))
            row = result.fetchone()
            idle_connections = row[0] if row else 0
            print(f"Idle database connections: {idle_connections}")
            
        except Exception as e:
            print(f"Error checking connections: {e}")

async def suggest_fixes():
    """Suggest fixes based on the diagnosis"""
    
    print("\n=== Suggested Fixes ===")
    
    fixes = [
        "1. Connection Management:",
        "   - Ensure all database sessions are properly closed",
        "   - Use context managers for session handling",
        "   - Add explicit session.close() calls in finally blocks",
        "",
        "2. Data Issues:",
        "   - Check if anp_seq 18240 actually exists in the database",
        "   - Verify that test completion data was properly saved",
        "   - Add fallback data generation for missing queries",
        "",
        "3. Query Optimization:",
        "   - Add data validation before query execution",
        "   - Implement graceful handling of empty results",
        "   - Add mock data for development/testing",
        "",
        "4. ETL Process Improvements:",
        "   - Add retry logic for failed queries",
        "   - Implement better error handling and logging",
        "   - Add health checks before processing"
    ]
    
    for fix in fixes:
        print(fix)

async def create_connection_fix():
    """Create a proper connection management fix"""
    
    connection_fix = '''#!/usr/bin/env python3
"""
ETL Connection Management Fix
Proper implementation of connection management for ETL processes
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ETLConnectionFix:
    """
    Fixes for ETL connection management
    """
    
    @staticmethod
    def fix_simple_query_executor():
        """
        Apply connection management fix to SimpleQueryExecutor
        """
        # Read the original file
        with open('etl/simple_query_executor.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add proper cleanup method
        if 'async def cleanup(self):' not in content:
            # Add async cleanup method
            cleanup_method = """
    async def cleanup(self):
        '''리소스 정리 - 비동기 버전'''
        try:
            if hasattr(self, '_sync_sess') and self._sync_sess:
                self._sync_sess.close()
        except Exception as e:
            logger.warning(f"Error closing sync session: {e}")
        logger.info("SimpleQueryExecutor resources cleaned up")
"""
            
            # Insert before the existing cleanup method
            content = content.replace(
                '    def cleanup(self):',
                cleanup_method + '    def cleanup(self):'
            )
        
        # Write the fixed content
        with open('etl/simple_query_executor_fixed.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("Applied connection fix to SimpleQueryExecutor")

# Apply the fix
fix = ETLConnectionFix()
fix.fix_simple_query_executor()
'''
    
    with open('etl_connection_fix.py', 'w', encoding='utf-8') as f:
        f.write(connection_fix)
    
    logger.info("Created connection management fix")

async def main():
    """Main diagnostic function"""
    logger.info("Starting ETL diagnosis...")
    
    try:
        # 1. Check data availability
        print("=== Data Availability Check ===")
        data_results = await diagnose_etl_data_issues()
        
        print("\nData availability results:")
        for query, result in data_results.items():
            if isinstance(result, list):
                print(f"{query}: {len(result)} records")
                for item in result[:3]:  # Show first 3 items
                    print(f"  {item}")
            else:
                print(f"{query}: {result}")
        
        # 2. Test SimpleQueryExecutor
        print("\n=== Testing SimpleQueryExecutor ===")
        await test_simple_query_executor()
        
        # 3. Check for connection leaks
        await check_connection_leak()
        
        # 4. Suggest fixes
        await suggest_fixes()
        
        # 5. Create connection fix
        await create_connection_fix()
        
    except Exception as e:
        logger.error(f"Error during diagnosis: {e}")
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())