#!/usr/bin/env python3
"""
Integration test for preference query optimization
Tests the complete optimization workflow
"""

import asyncio
import time
from etl.preference_optimization_init import initialize_for_development, get_optimization_status
from etl.preference_query_optimizer import get_preference_query_optimizer
from database.connection import init_database

async def test_integration():
    """Test complete preference optimization integration"""
    print("Starting preference optimization integration test...")
    
    # Initialize database
    print("1. Initializing database...")
    db_success = await init_database()
    if not db_success:
        print("❌ Database initialization failed")
        return False
    print("✅ Database initialized")
    
    # Initialize optimization
    print("2. Initializing optimization...")
    results = await initialize_for_development()
    if results["errors"]:
        print(f"❌ Optimization initialization failed: {results['errors']}")
        return False
    print("✅ Optimization initialized")
    
    # Test optimizer functionality
    print("3. Testing optimizer functionality...")
    optimizer = get_preference_query_optimizer()
    if not optimizer:
        print("❌ Optimizer not available")
        return False
    
    # Execute test queries
    test_queries = [
        ("test_query_1", "SELECT 1 as value"),
        ("test_query_2", "SELECT 2 as value"),
        ("test_query_1", "SELECT 1 as value"),  # Should hit cache
    ]
    
    for i, (query_name, sql) in enumerate(test_queries):
        start_time = time.time()
        try:
            result = await optimizer.execute_preference_query(
                query_name=query_name,
                anp_seq=18420,
                sql=sql
            )
            execution_time = time.time() - start_time
            print(f"   Query {i+1}: {query_name} - {execution_time:.3f}s - Result: {result}")
        except Exception as e:
            print(f"❌ Query {i+1} failed: {e}")
            return False
    
    print("✅ Optimizer functionality test passed")
    
    # Test performance metrics
    print("4. Testing performance metrics...")
    metrics = optimizer.get_performance_metrics()
    cache_stats = optimizer.get_cache_stats()
    pool_metrics = optimizer.get_connection_pool_metrics()
    
    print(f"   Metrics tracked: {len(metrics)} queries")
    print(f"   Cache entries: {cache_stats['total_entries']}")
    print(f"   Cache hits: {cache_stats['total_hits']}")
    print(f"   Pool utilization: {pool_metrics.utilization_rate:.1f}%")
    
    if len(metrics) < 2:
        print("❌ Expected at least 2 different queries in metrics")
        return False
    
    if cache_stats['total_hits'] < 1:
        print("❌ Expected at least 1 cache hit")
        return False
    
    print("✅ Performance metrics test passed")
    
    # Test performance report
    print("5. Testing performance report...")
    try:
        report = optimizer.generate_performance_report()
        if not all(key in report for key in ["timestamp", "overall_stats", "query_metrics", "connection_pool", "cache_stats"]):
            print("❌ Performance report missing required keys")
            return False
        print("✅ Performance report test passed")
    except Exception as e:
        print(f"❌ Performance report failed: {e}")
        return False
    
    # Test optimization status
    print("6. Testing optimization status...")
    status = get_optimization_status()
    if not status["optimizer_enabled"]:
        print("❌ Optimizer should be enabled")
        return False
    print("✅ Optimization status test passed")
    
    print("\n🎉 All integration tests passed!")
    return True

async def main():
    """Main test function"""
    try:
        success = await test_integration()
        if success:
            print("\n✅ Integration test completed successfully")
        else:
            print("\n❌ Integration test failed")
            exit(1)
    except Exception as e:
        print(f"\n❌ Integration test error: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())