#!/usr/bin/env python3
"""
Simple ETL Diagnosis
Quick diagnosis of ETL issues without complex string manipulation
"""

import asyncio
import logging
from typing import Dict, Any, List
from sqlalchemy import text

logger = logging.getLogger(__name__)

async def check_database_data():
    """Check what data exists in the database"""
    from database.connection import db_manager
    
    print("=== Database Data Check ===")
    
    async with db_manager.get_async_session() as session:
        try:
            # Check anp_seq 18240 specifically
            result = await session.execute(text("SELECT COUNT(*) FROM mwd_answer_progress WHERE anp_seq = 18240"))
            count = result.scalar()
            print(f"anp_seq 18240 in mwd_answer_progress: {count} records")
            
            # Check what anp_seq values exist
            result = await session.execute(text("SELECT anp_seq, COUNT(*) FROM mwd_answer_progress GROUP BY anp_seq ORDER BY anp_seq DESC LIMIT 5"))
            rows = result.fetchall()
            print("Recent anp_seq values:")
            for row in rows:
                print(f"  anp_seq {row[0]}: {row[1]} records")
            
            # Check mwd_resval for anp_seq 18240
            result = await session.execute(text("SELECT COUNT(*) FROM mwd_resval WHERE anp_seq = 18240"))
            count = result.scalar()
            print(f"anp_seq 18240 in mwd_resval: {count} records")
            
            # Check mwd_score1 for anp_seq 18240
            result = await session.execute(text("SELECT COUNT(*) FROM mwd_score1 WHERE anp_seq = 18240"))
            count = result.scalar()
            print(f"anp_seq 18240 in mwd_score1: {count} records")
            
            if count > 0:
                # Check what steps exist
                result = await session.execute(text("SELECT sc1_step, COUNT(*) FROM mwd_score1 WHERE anp_seq = 18240 GROUP BY sc1_step"))
                rows = result.fetchall()
                print("Score1 steps for anp_seq 18240:")
                for row in rows:
                    print(f"  {row[0]}: {row[1]} records")
            
        except Exception as e:
            print(f"Database check error: {e}")

async def test_simple_queries():
    """Test the simple query executor"""
    print("\n=== Testing Simple Query Executor ===")
    
    try:
        from etl.simple_query_executor import SimpleQueryExecutor
        
        executor = SimpleQueryExecutor()
        results = executor.execute_core_queries(18240)
        
        print("Query execution results:")
        for query_name, result in results.items():
            status = "✓" if result.success else "✗"
            rows = result.row_count if result.success else 0
            print(f"{status} {query_name}: {rows} rows")
            
            if not result.success:
                print(f"    Error: {result.error}")
            elif result.data and len(result.data) > 0:
                # Show first record keys
                keys = list(result.data[0].keys())
                print(f"    Columns: {', '.join(keys[:5])}")
        
        # Clean up
        executor.cleanup()
        
    except Exception as e:
        print(f"Query executor test error: {e}")

async def check_connections():
    """Check database connections"""
    print("\n=== Connection Check ===")
    
    from database.connection import db_manager
    
    try:
        async with db_manager.get_async_session() as session:
            # Check active connections
            result = await session.execute(text("""
                SELECT count(*) as active_connections 
                FROM pg_stat_activity 
                WHERE state = 'active' AND datname = current_database()
            """))
            active = result.scalar()
            print(f"Active connections: {active}")
            
            # Check idle connections
            result = await session.execute(text("""
                SELECT count(*) as idle_connections 
                FROM pg_stat_activity 
                WHERE state = 'idle' AND datname = current_database()
            """))
            idle = result.scalar()
            print(f"Idle connections: {idle}")
            
    except Exception as e:
        print(f"Connection check error: {e}")

def analyze_log_issues():
    """Analyze the issues from the log"""
    print("\n=== Log Analysis ===")
    
    issues = [
        "1. Connection Leak Warning:",
        "   - SQLAlchemy garbage collector cleaning up non-checked-in connection",
        "   - Need to ensure all connections are properly closed",
        "",
        "2. Empty Query Results:",
        "   - 23 out of 30 queries returned no data",
        "   - This suggests either:",
        "     a) anp_seq 18240 doesn't have complete data",
        "     b) Query logic needs adjustment",
        "     c) Test data is incomplete",
        "",
        "3. Document Creation:",
        "   - Only 8 documents created from available data",
        "   - Document types: USER_PROFILE(3), PERSONALITY_PROFILE(3), CAREER_RECOMMENDATIONS(1), LEARNING_STYLE(1)",
        "   - Missing: THINKING_SKILLS, COMPETENCY_ANALYSIS, PREFERENCE_ANALYSIS",
        "",
        "4. Processing Success:",
        "   - ETL completed successfully in 2.84s",
        "   - All stages completed without errors",
        "   - Documents were stored successfully"
    ]
    
    for issue in issues:
        print(issue)

def suggest_solutions():
    """Suggest solutions for the identified issues"""
    print("\n=== Suggested Solutions ===")
    
    solutions = [
        "1. Fix Connection Leak:",
        "   - Add explicit session.close() in finally blocks",
        "   - Use async context managers properly",
        "   - Review SimpleQueryExecutor cleanup method",
        "",
        "2. Handle Missing Data:",
        "   - Add data validation before query execution",
        "   - Generate mock data for missing queries during development",
        "   - Implement graceful fallbacks for empty results",
        "",
        "3. Improve ETL Robustness:",
        "   - Add retry logic for failed queries",
        "   - Better error handling and logging",
        "   - Health checks before processing",
        "",
        "4. Monitor and Debug:",
        "   - Add connection pool monitoring",
        "   - Log query execution details",
        "   - Track document creation statistics"
    ]
    
    for solution in solutions:
        print(solution)

async def main():
    """Main diagnostic function"""
    print("ETL Diagnosis Report")
    print("=" * 50)
    
    try:
        await check_database_data()
        await test_simple_queries()
        await check_connections()
        analyze_log_issues()
        suggest_solutions()
        
        print("\n" + "=" * 50)
        print("Diagnosis complete!")
        
    except Exception as e:
        logger.error(f"Diagnosis failed: {e}")
        print(f"Diagnosis failed: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())