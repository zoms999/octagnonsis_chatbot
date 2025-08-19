"""
Performance tests for preference queries under various load conditions
Tests query optimization, connection pooling, caching, and timeout handling
"""

import pytest
import asyncio
import time
import statistics
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import random

from etl.preference_query_optimizer import PreferenceQueryOptimizer, initialize_preference_query_optimizer
from database.preference_index_recommendations import PreferenceIndexAnalyzer
from database.connection import db_manager
from etl.legacy_query_executor import LegacyQueryExecutor
import structlog

# Setup test logging
test_logger = structlog.get_logger("preference_query_performance_tests")

@pytest.fixture
async def optimizer():
    """Create preference query optimizer for testing"""
    config = db_manager.config
    optimizer = PreferenceQueryOptimizer(
        connection_string=config.sync_url,
        pool_size=10,
        max_overflow=20,
        query_timeout=30,
        cache_ttl=300,
        enable_cache=True
    )
    yield optimizer
    await optimizer.close()

@pytest.fixture
async def sample_anp_seqs():
    """Get sample anp_seq values for testing"""
    try:
        async with db_manager.get_async_session() as session:
            from sqlalchemy import text
            result = await session.execute(
                text("SELECT anp_seq FROM mwd_answer_progress LIMIT 10")
            )
            anp_seqs = [row[0] for row in result.fetchall()]
            return anp_seqs if anp_seqs else [18420]  # Fallback to known test value
    except Exception as e:
        # Fallback to known test value if database query fails
        return [18420]

class TestPreferenceQueryPerformance:
    """Performance tests for preference queries"""
    
    @pytest.mark.asyncio
    async def test_single_query_performance(self, optimizer, sample_anp_seqs):
        """Test performance of individual preference queries"""
        anp_seqs = await sample_anp_seqs
        anp_seq = anp_seqs[0]
        
        # Test image preference stats query
        start_time = time.time()
        result = await optimizer.execute_preference_query(
            query_name="imagePreferenceStatsQuery",
            anp_seq=anp_seq,
            sql="""
            SELECT
              rv.rv_imgtcnt AS total_image_count,
              rv.rv_imgrcnt AS response_count,
              (rv.rv_imgresrate * 100)::int AS response_rate
            FROM mwd_resval rv
            WHERE rv.anp_seq = :anp_seq
            """
        )
        execution_time = time.time() - start_time
        
        assert isinstance(result, list)
        assert execution_time < 5.0  # Should complete within 5 seconds
        
        test_logger.info(
            "Single query performance test completed",
            query_name="imagePreferenceStatsQuery",
            anp_seq=anp_seq,
            execution_time=execution_time,
            result_count=len(result)
        )
    
    @pytest.mark.asyncio
    async def test_concurrent_query_performance(self, optimizer, sample_anp_seqs):
        """Test performance under concurrent load"""
        concurrent_requests = 20
        anp_seqs = await sample_anp_seqs
        anp_seq = anp_seqs[0]
        
        async def execute_query():
            return await optimizer.execute_preference_query(
                query_name="preferenceDataQuery",
                anp_seq=anp_seq,
                sql="""
                SELECT
                    qa.qua_name as preference_name,
                    sc1.sc1_qcnt as question_count,
                    (round(sc1.sc1_resrate * 100))::int AS response_rate,
                    sc1.sc1_rank as rank,
                    qe.que_explain as description
                FROM mwd_score1 sc1
                JOIN mwd_question_attr qa ON qa.qua_code = sc1.qua_code
                JOIN mwd_question_explain qe ON qe.qua_code = qa.qua_code AND qe.que_switch = 1
                WHERE sc1.anp_seq = :anp_seq
                  AND sc1.sc1_step = 'img'
                  AND sc1.sc1_rank <= 3
                ORDER BY sc1.sc1_rank
                """
            )
        
        # Execute concurrent requests
        start_time = time.time()
        tasks = [execute_query() for _ in range(concurrent_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        failed_results = [r for r in results if isinstance(r, Exception)]
        
        assert len(successful_results) >= concurrent_requests * 0.8  # At least 80% success rate
        assert total_time < 30.0  # Should complete within 30 seconds
        
        avg_time_per_request = total_time / concurrent_requests
        
        test_logger.info(
            "Concurrent query performance test completed",
            concurrent_requests=concurrent_requests,
            successful_results=len(successful_results),
            failed_results=len(failed_results),
            total_time=total_time,
            avg_time_per_request=avg_time_per_request
        )
    
    @pytest.mark.asyncio
    async def test_cache_performance(self, optimizer, sample_anp_seqs):
        """Test query caching performance"""
        anp_seqs = await sample_anp_seqs
        anp_seq = anp_seqs[0]
        query_sql = """
        SELECT
          rv.rv_imgtcnt AS total_image_count,
          rv.rv_imgrcnt AS response_count,
          (rv.rv_imgresrate * 100)::int AS response_rate
        FROM mwd_resval rv
        WHERE rv.anp_seq = :anp_seq
        """
        
        # First execution (cache miss)
        start_time = time.time()
        result1 = await optimizer.execute_preference_query(
            query_name="imagePreferenceStatsQuery",
            anp_seq=anp_seq,
            sql=query_sql
        )
        first_execution_time = time.time() - start_time
        
        # Second execution (cache hit)
        start_time = time.time()
        result2 = await optimizer.execute_preference_query(
            query_name="imagePreferenceStatsQuery",
            anp_seq=anp_seq,
            sql=query_sql
        )
        second_execution_time = time.time() - start_time
        
        # Verify cache effectiveness
        assert result1 == result2  # Results should be identical
        assert second_execution_time < first_execution_time * 0.1  # Cache should be much faster
        
        # Check cache statistics
        cache_stats = optimizer.get_cache_stats()
        assert cache_stats["total_entries"] > 0
        assert cache_stats["total_hits"] > 0
        
        test_logger.info(
            "Cache performance test completed",
            first_execution_time=first_execution_time,
            second_execution_time=second_execution_time,
            cache_speedup=first_execution_time / second_execution_time,
            cache_stats=cache_stats
        )
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, optimizer, sample_anp_seqs):
        """Test query timeout handling"""
        anp_seqs = await sample_anp_seqs
        anp_seq = anp_seqs[0]
        
        # Create a slow query that should timeout
        slow_query = """
        SELECT
            rv.rv_imgtcnt AS total_image_count,
            rv.rv_imgrcnt AS response_count,
            (rv.rv_imgresrate * 100)::int AS response_rate,
            pg_sleep(35) -- Force timeout (optimizer has 30s timeout)
        FROM mwd_resval rv
        WHERE rv.anp_seq = :anp_seq
        """
        
        start_time = time.time()
        with pytest.raises((TimeoutError, asyncio.TimeoutError)):
            await optimizer.execute_preference_query(
                query_name="slowQuery",
                anp_seq=anp_seq,
                sql=slow_query
            )
        execution_time = time.time() - start_time
        
        # Should timeout within reasonable time (30s + buffer)
        assert execution_time < 40.0
        
        # Check that timeout was recorded in metrics
        metrics = optimizer.get_performance_metrics()
        slow_query_metrics = metrics.get("slowQuery")
        if slow_query_metrics:
            assert slow_query_metrics.timeout_count > 0
        
        test_logger.info(
            "Timeout handling test completed",
            execution_time=execution_time,
            timeout_recorded=slow_query_metrics.timeout_count if slow_query_metrics else 0
        )
    
    @pytest.mark.asyncio
    async def test_connection_pool_performance(self, optimizer, sample_anp_seqs):
        """Test connection pool performance under load"""
        concurrent_connections = 15  # More than pool size (10) but less than max (30)
        anp_seqs = await sample_anp_seqs
        anp_seq = anp_seqs[0]
        
        async def execute_with_delay():
            # Add small delay to simulate real-world processing
            await asyncio.sleep(random.uniform(0.1, 0.5))
            return await optimizer.execute_preference_query(
                query_name="poolTestQuery",
                anp_seq=anp_seq,
                sql="SELECT rv.rv_imgtcnt FROM mwd_resval rv WHERE rv.anp_seq = :anp_seq"
            )
        
        start_time = time.time()
        tasks = [execute_with_delay() for _ in range(concurrent_connections)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        successful_results = [r for r in results if not isinstance(r, Exception)]
        
        # Check connection pool metrics
        pool_metrics = optimizer.get_connection_pool_metrics()
        
        assert len(successful_results) >= concurrent_connections * 0.9  # 90% success rate
        assert pool_metrics.utilization_rate <= 100  # Should not exceed 100%
        
        test_logger.info(
            "Connection pool performance test completed",
            concurrent_connections=concurrent_connections,
            successful_results=len(successful_results),
            total_time=total_time,
            pool_utilization=pool_metrics.utilization_rate,
            pool_metrics=pool_metrics.__dict__
        )
    
    @pytest.mark.asyncio
    async def test_multiple_anp_seq_performance(self, optimizer, sample_anp_seqs):
        """Test performance with multiple different anp_seq values"""
        anp_seqs = await sample_anp_seqs
        if len(anp_seqs) < 3:
            pytest.skip("Need at least 3 anp_seq values for this test")
        
        execution_times = []
        
        for anp_seq in anp_seqs[:5]:  # Test with up to 5 different users
            start_time = time.time()
            result = await optimizer.execute_preference_query(
                query_name="multiUserTest",
                anp_seq=anp_seq,
                sql="""
                SELECT
                    qa.qua_name as preference_name,
                    sc1.sc1_rank as rank
                FROM mwd_score1 sc1
                JOIN mwd_question_attr qa ON qa.qua_code = sc1.qua_code
                WHERE sc1.anp_seq = :anp_seq
                  AND sc1.sc1_step = 'img'
                  AND sc1.sc1_rank <= 3
                ORDER BY sc1.sc1_rank
                """
            )
            execution_time = time.time() - start_time
            execution_times.append(execution_time)
            
            assert isinstance(result, list)
        
        # Analyze performance consistency
        avg_time = statistics.mean(execution_times)
        std_dev = statistics.stdev(execution_times) if len(execution_times) > 1 else 0
        
        # Performance should be consistent (low standard deviation)
        assert std_dev < avg_time * 0.5  # Standard deviation should be less than 50% of mean
        
        test_logger.info(
            "Multiple anp_seq performance test completed",
            anp_seqs_tested=len(anp_seqs[:5]),
            avg_execution_time=avg_time,
            std_deviation=std_dev,
            execution_times=execution_times
        )
    
    @pytest.mark.asyncio
    async def test_error_recovery_performance(self, optimizer, sample_anp_seqs):
        """Test performance of error recovery and retry logic"""
        anp_seqs = await sample_anp_seqs
        anp_seq = anp_seqs[0]
        
        # Test with invalid query that should fail and retry
        invalid_query = """
        SELECT
            rv.nonexistent_column  -- This will cause an error
        FROM mwd_resval rv
        WHERE rv.anp_seq = :anp_seq
        """
        
        start_time = time.time()
        with pytest.raises(Exception):  # Should eventually fail after retries
            await optimizer.execute_preference_query(
                query_name="errorRecoveryTest",
                anp_seq=anp_seq,
                sql=invalid_query
            )
        execution_time = time.time() - start_time
        
        # Should fail relatively quickly (not hang)
        assert execution_time < 10.0
        
        # Check that errors were recorded in metrics
        metrics = optimizer.get_performance_metrics()
        error_metrics = metrics.get("errorRecoveryTest")
        if error_metrics:
            assert error_metrics.error_count > 0
            assert error_metrics.total_executions > 1  # Should have retried
        
        test_logger.info(
            "Error recovery performance test completed",
            execution_time=execution_time,
            error_count=error_metrics.error_count if error_metrics else 0,
            retry_attempts=error_metrics.total_executions if error_metrics else 0
        )
    
    @pytest.mark.asyncio
    async def test_performance_metrics_accuracy(self, optimizer, sample_anp_seqs):
        """Test accuracy of performance metrics collection"""
        anp_seqs = await sample_anp_seqs
        anp_seq = anp_seqs[0]
        query_name = "metricsAccuracyTest"
        
        # Execute multiple queries
        num_executions = 5
        for i in range(num_executions):
            await optimizer.execute_preference_query(
                query_name=query_name,
                anp_seq=anp_seq,
                sql="SELECT rv.rv_imgtcnt FROM mwd_resval rv WHERE rv.anp_seq = :anp_seq"
            )
        
        # Check metrics accuracy
        metrics = optimizer.get_performance_metrics()
        query_metrics = metrics.get(query_name)
        
        assert query_metrics is not None
        assert query_metrics.total_executions == num_executions
        assert query_metrics.avg_execution_time > 0
        assert query_metrics.min_execution_time <= query_metrics.max_execution_time
        assert query_metrics.last_execution is not None
        
        test_logger.info(
            "Performance metrics accuracy test completed",
            expected_executions=num_executions,
            recorded_executions=query_metrics.total_executions,
            avg_time=query_metrics.avg_execution_time,
            min_time=query_metrics.min_execution_time,
            max_time=query_metrics.max_execution_time
        )

class TestPreferenceIndexRecommendations:
    """Tests for database index recommendations"""
    
    @pytest.mark.asyncio
    async def test_index_analysis_performance(self):
        """Test performance of index analysis"""
        analyzer = PreferenceIndexAnalyzer()
        
        start_time = time.time()
        recommendations = await analyzer.analyze_preference_queries()
        analysis_time = time.time() - start_time
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert analysis_time < 30.0  # Should complete within 30 seconds
        
        # Verify recommendation quality
        high_priority_recs = [r for r in recommendations if r.priority == "high"]
        assert len(high_priority_recs) > 0  # Should have high priority recommendations
        
        test_logger.info(
            "Index analysis performance test completed",
            analysis_time=analysis_time,
            total_recommendations=len(recommendations),
            high_priority_recommendations=len(high_priority_recs)
        )
    
    @pytest.mark.asyncio
    async def test_index_creation_dry_run(self):
        """Test dry run index creation performance"""
        analyzer = PreferenceIndexAnalyzer()
        recommendations = await analyzer.analyze_preference_queries()
        
        start_time = time.time()
        result = await analyzer.create_recommended_indexes(
            recommendations=recommendations[:3],  # Test with first 3 recommendations
            dry_run=True
        )
        creation_time = time.time() - start_time
        
        assert result["dry_run"] is True
        assert len(result["skipped"]) == 3
        assert len(result["created"]) == 0
        assert len(result["failed"]) == 0
        assert creation_time < 5.0  # Dry run should be fast
        
        test_logger.info(
            "Index creation dry run test completed",
            creation_time=creation_time,
            recommendations_tested=3,
            result=result
        )

class TestPreferenceQueryComparison:
    """Compare optimized vs unoptimized query performance"""
    
    @pytest.mark.asyncio
    async def test_optimized_vs_legacy_performance(self, optimizer, sample_anp_seqs):
        """Compare optimized queries vs legacy implementation"""
        anp_seqs = await sample_anp_seqs
        anp_seq = anp_seqs[0]
        
        # Test with legacy query executor
        async with db_manager.get_async_session() as session:
            legacy_executor = LegacyQueryExecutor(session)
            
            # Time legacy execution
            start_time = time.time()
            try:
                legacy_result = await legacy_executor.execute_preference_queries(anp_seq)
                legacy_time = time.time() - start_time
                legacy_success = True
            except Exception as e:
                legacy_time = time.time() - start_time
                legacy_success = False
                legacy_result = None
        
        # Time optimized execution
        start_time = time.time()
        try:
            optimized_result = await optimizer.execute_preference_query(
                query_name="imagePreferenceStatsQuery",
                anp_seq=anp_seq,
                sql="""
                SELECT
                  rv.rv_imgtcnt AS total_image_count,
                  rv.rv_imgrcnt AS response_count,
                  (rv.rv_imgresrate * 100)::int AS response_rate
                FROM mwd_resval rv
                WHERE rv.anp_seq = :anp_seq
                """
            )
            optimized_time = time.time() - start_time
            optimized_success = True
        except Exception as e:
            optimized_time = time.time() - start_time
            optimized_success = False
            optimized_result = None
        
        # Compare performance (if both succeeded)
        if legacy_success and optimized_success:
            # Optimized should be faster or at least not significantly slower
            performance_ratio = optimized_time / legacy_time
            assert performance_ratio <= 2.0  # Optimized should not be more than 2x slower
        
        test_logger.info(
            "Optimized vs legacy performance comparison completed",
            legacy_time=legacy_time,
            legacy_success=legacy_success,
            optimized_time=optimized_time,
            optimized_success=optimized_success,
            performance_ratio=optimized_time / legacy_time if legacy_success and optimized_success else None
        )

@pytest.mark.asyncio
async def test_comprehensive_performance_report(optimizer, sample_anp_seqs):
    """Generate comprehensive performance report"""
    anp_seqs = await sample_anp_seqs
    anp_seq = anp_seqs[0]
    
    # Execute various queries to populate metrics
    queries = [
        ("imagePreferenceStatsQuery", "SELECT rv.rv_imgtcnt FROM mwd_resval rv WHERE rv.anp_seq = :anp_seq"),
        ("preferenceDataQuery", "SELECT COUNT(*) FROM mwd_score1 WHERE anp_seq = :anp_seq AND sc1_step = 'img'"),
        ("preferenceJobsQuery", "SELECT COUNT(*) FROM mwd_resjob WHERE anp_seq = :anp_seq")
    ]
    
    for query_name, sql in queries:
        try:
            await optimizer.execute_preference_query(query_name, anp_seq, sql)
        except Exception:
            pass  # Ignore errors for report generation test
    
    # Generate performance report
    report = optimizer.generate_performance_report()
    
    assert "timestamp" in report
    assert "overall_stats" in report
    assert "query_metrics" in report
    assert "connection_pool" in report
    assert "cache_stats" in report
    
    # Verify report structure
    overall_stats = report["overall_stats"]
    assert "total_executions" in overall_stats
    assert "overall_cache_hit_rate" in overall_stats
    assert "avg_execution_time" in overall_stats
    
    test_logger.info(
        "Comprehensive performance report generated",
        report_keys=list(report.keys()),
        total_executions=overall_stats["total_executions"],
        cache_hit_rate=overall_stats["overall_cache_hit_rate"]
    )