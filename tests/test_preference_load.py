"""
Load testing for preference processing under high user volume
Tests system performance and stability with concurrent preference processing
"""

import pytest
import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any
import random
from datetime import datetime, timedelta

from etl.legacy_query_executor import LegacyQueryExecutor, QueryResult
from etl.document_transformer import DocumentTransformer
from etl.preference_data_validator import PreferenceDataValidator
from database.repositories import DocumentRepository
from rag.context_builder import ContextBuilder
from rag.response_generator import ResponseGenerator


class TestPreferenceLoadTesting:
    """Load testing for preference data processing"""
    
    def generate_mock_preference_data(self, anp_seq: int, data_quality: str = "good") -> Dict[str, QueryResult]:
        """Generate mock preference data for testing"""
        
        if data_quality == "good":
            return {
                "imagePreferenceStatsQuery": QueryResult(
                    query_name="imagePreferenceStatsQuery",
                    success=True,
                    data=[{
                        "total_image_count": random.randint(100, 150),
                        "response_count": random.randint(80, 120),
                        "response_rate": random.randint(70, 90)
                    }],
                    execution_time=random.uniform(0.5, 2.0),
                    row_count=1
                ),
                "preferenceDataQuery": QueryResult(
                    query_name="preferenceDataQuery",
                    success=True,
                    data=[
                        {
                            "preference_name": f"선호도_{i}",
                            "rank": i,
                            "response_rate": random.randint(70, 95),
                            "description": f"선호도 {i} 설명"
                        }
                        for i in range(1, random.randint(3, 6))
                    ],
                    execution_time=random.uniform(1.0, 3.0),
                    row_count=random.randint(2, 5)
                ),
                "preferenceJobsQuery": QueryResult(
                    query_name="preferenceJobsQuery",
                    success=True,
                    data=[
                        {
                            "preference_name": f"선호도_{i}",
                            "preference_type": f"rimg{i}",
                            "jo_name": f"직업_{i}_{j}",
                            "jo_outline": f"직업 {i}-{j} 개요",
                            "majors": f"전공{i}, 전공{j}"
                        }
                        for i in range(1, 4)
                        for j in range(1, random.randint(2, 4))
                    ],
                    execution_time=random.uniform(1.5, 4.0),
                    row_count=random.randint(5, 15)
                )
            }
        elif data_quality == "partial":
            return {
                "imagePreferenceStatsQuery": QueryResult(
                    query_name="imagePreferenceStatsQuery",
                    success=False,
                    error="Connection timeout",
                    execution_time=5.0
                ),
                "preferenceDataQuery": QueryResult(
                    query_name="preferenceDataQuery",
                    success=True,
                    data=[{
                        "preference_name": "실내 활동 선호",
                        "rank": 1,
                        "response_rate": 85
                    }],
                    execution_time=random.uniform(1.0, 2.0),
                    row_count=1
                ),
                "preferenceJobsQuery": QueryResult(
                    query_name="preferenceJobsQuery",
                    success=True,
                    data=[],
                    execution_time=random.uniform(0.5, 1.0),
                    row_count=0
                )
            }
        else:  # "poor"
            return {
                "imagePreferenceStatsQuery": QueryResult(
                    query_name="imagePreferenceStatsQuery",
                    success=False,
                    error="Database connection failed",
                    execution_time=10.0
                ),
                "preferenceDataQuery": QueryResult(
                    query_name="preferenceDataQuery",
                    success=False,
                    error="Query timeout",
                    execution_time=15.0
                ),
                "preferenceJobsQuery": QueryResult(
                    query_name="preferenceJobsQuery",
                    success=False,
                    error="Invalid anp_seq",
                    execution_time=0.5
                )
            }

    @pytest.mark.asyncio
    async def test_concurrent_preference_query_execution(self):
        """Test concurrent preference query execution under load"""
        
        # Test parameters
        concurrent_users = 50
        anp_seqs = list(range(10000, 10000 + concurrent_users))
        
        async def process_single_user(anp_seq: int) -> Dict[str, Any]:
            """Process preference queries for a single user"""
            start_time = time.time()
            
            try:
                # Mock query execution
                mock_data = self.generate_mock_preference_data(anp_seq, "good")
                
                with patch.object(LegacyQueryExecutor, '_query_image_preference_stats') as mock_stats, \
                     patch.object(LegacyQueryExecutor, '_query_preference_data') as mock_prefs, \
                     patch.object(LegacyQueryExecutor, '_query_preference_jobs') as mock_jobs:
                    
                    mock_stats.return_value = mock_data["imagePreferenceStatsQuery"].data
                    mock_prefs.return_value = mock_data["preferenceDataQuery"].data
                    mock_jobs.return_value = mock_data["preferenceJobsQuery"].data
                    
                    executor = LegacyQueryExecutor()
                    results = {
                        "imagePreferenceStatsQuery": mock_data["imagePreferenceStatsQuery"],
                        "preferenceDataQuery": mock_data["preferenceDataQuery"],
                        "preferenceJobsQuery": mock_data["preferenceJobsQuery"]
                    }
                    
                    execution_time = time.time() - start_time
                    
                    return {
                        "anp_seq": anp_seq,
                        "success": True,
                        "execution_time": execution_time,
                        "query_count": len(results),
                        "successful_queries": sum(1 for r in results.values() if r.success)
                    }
                    
            except Exception as e:
                execution_time = time.time() - start_time
                return {
                    "anp_seq": anp_seq,
                    "success": False,
                    "execution_time": execution_time,
                    "error": str(e)
                }
        
        # Execute concurrent processing
        start_time = time.time()
        tasks = [process_single_user(anp_seq) for anp_seq in anp_seqs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_results = [r for r in results if isinstance(r, dict) and not r.get("success")]
        exception_results = [r for r in results if isinstance(r, Exception)]
        
        # Performance metrics
        execution_times = [r["execution_time"] for r in successful_results]
        
        print(f"\n=== Concurrent Query Execution Load Test Results ===")
        print(f"Total users: {concurrent_users}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Successful: {len(successful_results)}")
        print(f"Failed: {len(failed_results)}")
        print(f"Exceptions: {len(exception_results)}")
        
        if execution_times:
            print(f"Avg execution time: {statistics.mean(execution_times):.2f}s")
            print(f"Min execution time: {min(execution_times):.2f}s")
            print(f"Max execution time: {max(execution_times):.2f}s")
            print(f"95th percentile: {statistics.quantiles(execution_times, n=20)[18]:.2f}s")
        
        # Assertions
        assert len(successful_results) >= concurrent_users * 0.95  # 95% success rate
        assert total_time < concurrent_users * 2  # Should complete faster than sequential
        if execution_times:
            assert statistics.mean(execution_times) < 5.0  # Average under 5 seconds
            assert max(execution_times) < 15.0  # No single request over 15 seconds

    @pytest.mark.asyncio
    async def test_concurrent_document_transformation(self):
        """Test concurrent document transformation under load"""
        
        concurrent_transformations = 30
        
        async def transform_documents(user_id: int) -> Dict[str, Any]:
            """Transform documents for a single user"""
            start_time = time.time()
            
            try:
                # Generate mock data
                mock_data = self.generate_mock_preference_data(user_id, "good")
                formatted_data = {name: result.data for name, result in mock_data.items()}
                
                transformer = DocumentTransformer()
                documents = transformer._chunk_preference_analysis(formatted_data)
                
                execution_time = time.time() - start_time
                
                return {
                    "user_id": user_id,
                    "success": True,
                    "execution_time": execution_time,
                    "document_count": len(documents),
                    "document_types": list(set(doc.metadata.get("sub_type") for doc in documents))
                }
                
            except Exception as e:
                execution_time = time.time() - start_time
                return {
                    "user_id": user_id,
                    "success": False,
                    "execution_time": execution_time,
                    "error": str(e)
                }
        
        # Execute concurrent transformations
        start_time = time.time()
        tasks = [transform_documents(i) for i in range(concurrent_transformations)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_results = [r for r in results if isinstance(r, dict) and not r.get("success")]
        
        execution_times = [r["execution_time"] for r in successful_results]
        document_counts = [r["document_count"] for r in successful_results]
        
        print(f"\n=== Concurrent Document Transformation Load Test Results ===")
        print(f"Total transformations: {concurrent_transformations}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Successful: {len(successful_results)}")
        print(f"Failed: {len(failed_results)}")
        
        if execution_times:
            print(f"Avg execution time: {statistics.mean(execution_times):.2f}s")
            print(f"Avg documents per user: {statistics.mean(document_counts):.1f}")
            print(f"Max execution time: {max(execution_times):.2f}s")
        
        # Assertions
        assert len(successful_results) >= concurrent_transformations * 0.95
        if execution_times:
            assert statistics.mean(execution_times) < 3.0  # Average under 3 seconds
            assert all(count >= 1 for count in document_counts)  # At least 1 document per user

    @pytest.mark.asyncio
    async def test_mixed_load_scenarios(self):
        """Test system under mixed load scenarios (good/partial/poor data quality)"""
        
        total_users = 60
        scenarios = ["good", "partial", "poor"]
        users_per_scenario = total_users // len(scenarios)
        
        async def process_user_with_scenario(user_id: int, scenario: str) -> Dict[str, Any]:
            """Process user with specific data quality scenario"""
            start_time = time.time()
            
            try:
                # Generate data based on scenario
                mock_data = self.generate_mock_preference_data(user_id, scenario)
                
                with patch.object(LegacyQueryExecutor, '_query_image_preference_stats') as mock_stats, \
                     patch.object(LegacyQueryExecutor, '_query_preference_data') as mock_prefs, \
                     patch.object(LegacyQueryExecutor, '_query_preference_jobs') as mock_jobs:
                    
                    mock_stats.return_value = mock_data["imagePreferenceStatsQuery"].data
                    mock_prefs.return_value = mock_data["preferenceDataQuery"].data
                    mock_jobs.return_value = mock_data["preferenceJobsQuery"].data
                    
                    # Execute queries
                    executor = LegacyQueryExecutor()
                    query_results = {
                        "imagePreferenceStatsQuery": mock_data["imagePreferenceStatsQuery"],
                        "preferenceDataQuery": mock_data["preferenceDataQuery"],
                        "preferenceJobsQuery": mock_data["preferenceJobsQuery"]
                    }
                    
                    # Transform documents
                    formatted_data = {name: result.data if result.success else [] 
                                    for name, result in query_results.items()}
                    
                    transformer = DocumentTransformer()
                    documents = transformer._chunk_preference_analysis(formatted_data)
                    
                    # Validate data
                    validator = PreferenceDataValidator()
                    validation_report = validator.generate_validation_report(formatted_data)
                    
                    execution_time = time.time() - start_time
                    
                    return {
                        "user_id": user_id,
                        "scenario": scenario,
                        "success": True,
                        "execution_time": execution_time,
                        "query_success_count": sum(1 for r in query_results.values() if r.success),
                        "document_count": len(documents),
                        "validation_passed": validation_report.overall_valid
                    }
                    
            except Exception as e:
                execution_time = time.time() - start_time
                return {
                    "user_id": user_id,
                    "scenario": scenario,
                    "success": False,
                    "execution_time": execution_time,
                    "error": str(e)
                }
        
        # Create mixed workload
        tasks = []
        for i, scenario in enumerate(scenarios):
            for j in range(users_per_scenario):
                user_id = i * users_per_scenario + j
                tasks.append(process_user_with_scenario(user_id, scenario))
        
        # Execute mixed load
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results by scenario
        results_by_scenario = {}
        for scenario in scenarios:
            scenario_results = [r for r in results 
                              if isinstance(r, dict) and r.get("scenario") == scenario]
            
            successful = [r for r in scenario_results if r.get("success")]
            failed = [r for r in scenario_results if not r.get("success")]
            
            results_by_scenario[scenario] = {
                "total": len(scenario_results),
                "successful": len(successful),
                "failed": len(failed),
                "success_rate": len(successful) / len(scenario_results) if scenario_results else 0,
                "avg_execution_time": statistics.mean([r["execution_time"] for r in successful]) if successful else 0,
                "avg_documents": statistics.mean([r["document_count"] for r in successful]) if successful else 0
            }
        
        print(f"\n=== Mixed Load Scenarios Test Results ===")
        print(f"Total users: {total_users}")
        print(f"Total time: {total_time:.2f}s")
        
        for scenario, metrics in results_by_scenario.items():
            print(f"\n{scenario.upper()} scenario:")
            print(f"  Success rate: {metrics['success_rate']:.1%}")
            print(f"  Avg execution time: {metrics['avg_execution_time']:.2f}s")
            print(f"  Avg documents: {metrics['avg_documents']:.1f}")
        
        # Assertions
        assert results_by_scenario["good"]["success_rate"] >= 0.95
        assert results_by_scenario["partial"]["success_rate"] >= 0.90
        assert results_by_scenario["poor"]["success_rate"] >= 0.85  # Should handle gracefully
        
        # Good scenario should be fastest
        assert results_by_scenario["good"]["avg_execution_time"] <= results_by_scenario["partial"]["avg_execution_time"]

    @pytest.mark.asyncio
    async def test_sustained_load_over_time(self):
        """Test system performance under sustained load over time"""
        
        duration_minutes = 2  # 2 minute test
        users_per_minute = 20
        total_duration = duration_minutes * 60
        
        results = []
        start_time = time.time()
        
        async def process_batch(batch_start_time: float, batch_id: int) -> List[Dict[str, Any]]:
            """Process a batch of users"""
            batch_results = []
            
            async def process_user(user_id: int) -> Dict[str, Any]:
                user_start = time.time()
                
                try:
                    mock_data = self.generate_mock_preference_data(user_id, 
                                                                 random.choice(["good", "partial"]))
                    
                    with patch.object(LegacyQueryExecutor, '_query_image_preference_stats') as mock_stats, \
                         patch.object(LegacyQueryExecutor, '_query_preference_data') as mock_prefs, \
                         patch.object(LegacyQueryExecutor, '_query_preference_jobs') as mock_jobs:
                        
                        mock_stats.return_value = mock_data["imagePreferenceStatsQuery"].data
                        mock_prefs.return_value = mock_data["preferenceDataQuery"].data
                        mock_jobs.return_value = mock_data["preferenceJobsQuery"].data
                        
                        executor = LegacyQueryExecutor()
                        query_results = {
                            "imagePreferenceStatsQuery": mock_data["imagePreferenceStatsQuery"],
                            "preferenceDataQuery": mock_data["preferenceDataQuery"],
                            "preferenceJobsQuery": mock_data["preferenceJobsQuery"]
                        }
                        
                        formatted_data = {name: result.data if result.success else [] 
                                        for name, result in query_results.items()}
                        
                        transformer = DocumentTransformer()
                        documents = transformer._chunk_preference_analysis(formatted_data)
                        
                        execution_time = time.time() - user_start
                        
                        return {
                            "user_id": user_id,
                            "batch_id": batch_id,
                            "batch_time": batch_start_time - start_time,
                            "execution_time": execution_time,
                            "success": True,
                            "document_count": len(documents)
                        }
                        
                except Exception as e:
                    execution_time = time.time() - user_start
                    return {
                        "user_id": user_id,
                        "batch_id": batch_id,
                        "batch_time": batch_start_time - start_time,
                        "execution_time": execution_time,
                        "success": False,
                        "error": str(e)
                    }
            
            # Process users in batch
            batch_tasks = [process_user(batch_id * users_per_minute + i) 
                          for i in range(users_per_minute)]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            return [r for r in batch_results if isinstance(r, dict)]
        
        # Run sustained load
        batch_id = 0
        while time.time() - start_time < total_duration:
            batch_start = time.time()
            
            batch_results = await process_batch(batch_start, batch_id)
            results.extend(batch_results)
            
            batch_id += 1
            
            # Wait for next minute (if needed)
            elapsed = time.time() - batch_start
            if elapsed < 60:
                await asyncio.sleep(60 - elapsed)
        
        # Analyze sustained load results
        successful_results = [r for r in results if r.get("success")]
        failed_results = [r for r in results if not r.get("success")]
        
        # Performance over time
        time_buckets = {}
        for result in successful_results:
            minute = int(result["batch_time"] // 60)
            if minute not in time_buckets:
                time_buckets[minute] = []
            time_buckets[minute].append(result["execution_time"])
        
        print(f"\n=== Sustained Load Test Results ===")
        print(f"Duration: {duration_minutes} minutes")
        print(f"Total requests: {len(results)}")
        print(f"Successful: {len(successful_results)}")
        print(f"Failed: {len(failed_results)}")
        print(f"Overall success rate: {len(successful_results) / len(results):.1%}")
        
        print(f"\nPerformance over time:")
        for minute, times in sorted(time_buckets.items()):
            avg_time = statistics.mean(times)
            print(f"  Minute {minute}: {len(times)} requests, avg {avg_time:.2f}s")
        
        # Assertions
        assert len(successful_results) / len(results) >= 0.90  # 90% success rate
        
        # Performance should not degrade significantly over time
        if len(time_buckets) >= 2:
            first_minute_avg = statistics.mean(time_buckets[0])
            last_minute_avg = statistics.mean(time_buckets[max(time_buckets.keys())])
            
            # Performance degradation should be less than 50%
            assert last_minute_avg <= first_minute_avg * 1.5

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self):
        """Test memory usage patterns under load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        concurrent_users = 40
        memory_samples = []
        
        async def process_user_with_memory_tracking(user_id: int) -> Dict[str, Any]:
            """Process user and track memory usage"""
            
            # Sample memory before processing
            pre_memory = process.memory_info().rss / 1024 / 1024
            
            try:
                mock_data = self.generate_mock_preference_data(user_id, "good")
                
                with patch.object(LegacyQueryExecutor, '_query_image_preference_stats') as mock_stats, \
                     patch.object(LegacyQueryExecutor, '_query_preference_data') as mock_prefs, \
                     patch.object(LegacyQueryExecutor, '_query_preference_jobs') as mock_jobs:
                    
                    mock_stats.return_value = mock_data["imagePreferenceStatsQuery"].data
                    mock_prefs.return_value = mock_data["preferenceDataQuery"].data
                    mock_jobs.return_value = mock_data["preferenceJobsQuery"].data
                    
                    executor = LegacyQueryExecutor()
                    query_results = {
                        "imagePreferenceStatsQuery": mock_data["imagePreferenceStatsQuery"],
                        "preferenceDataQuery": mock_data["preferenceDataQuery"],
                        "preferenceJobsQuery": mock_data["preferenceJobsQuery"]
                    }
                    
                    formatted_data = {name: result.data if result.success else [] 
                                    for name, result in query_results.items()}
                    
                    transformer = DocumentTransformer()
                    documents = transformer._chunk_preference_analysis(formatted_data)
                    
                    # Sample memory after processing
                    post_memory = process.memory_info().rss / 1024 / 1024
                    
                    return {
                        "user_id": user_id,
                        "success": True,
                        "pre_memory": pre_memory,
                        "post_memory": post_memory,
                        "memory_delta": post_memory - pre_memory,
                        "document_count": len(documents)
                    }
                    
            except Exception as e:
                post_memory = process.memory_info().rss / 1024 / 1024
                return {
                    "user_id": user_id,
                    "success": False,
                    "pre_memory": pre_memory,
                    "post_memory": post_memory,
                    "memory_delta": post_memory - pre_memory,
                    "error": str(e)
                }
        
        # Execute with memory tracking
        tasks = [process_user_with_memory_tracking(i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        final_memory = process.memory_info().rss / 1024 / 1024
        
        # Analyze memory usage
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        memory_deltas = [r["memory_delta"] for r in successful_results]
        
        print(f"\n=== Memory Usage Load Test Results ===")
        print(f"Initial memory: {initial_memory:.1f} MB")
        print(f"Final memory: {final_memory:.1f} MB")
        print(f"Total memory increase: {final_memory - initial_memory:.1f} MB")
        print(f"Successful requests: {len(successful_results)}")
        
        if memory_deltas:
            print(f"Avg memory delta per request: {statistics.mean(memory_deltas):.2f} MB")
            print(f"Max memory delta: {max(memory_deltas):.2f} MB")
            print(f"Min memory delta: {min(memory_deltas):.2f} MB")
        
        # Assertions
        assert final_memory - initial_memory < 500  # Less than 500MB total increase
        if memory_deltas:
            assert statistics.mean(memory_deltas) < 10  # Less than 10MB per request on average

    @pytest.mark.asyncio
    async def test_error_rate_under_load(self):
        """Test error handling and recovery under load conditions"""
        
        total_requests = 100
        error_injection_rate = 0.2  # 20% of requests will have errors
        
        async def process_with_error_injection(request_id: int) -> Dict[str, Any]:
            """Process request with potential error injection"""
            start_time = time.time()
            
            # Inject errors randomly
            if random.random() < error_injection_rate:
                # Simulate various error types
                error_type = random.choice(["timeout", "connection", "data_error"])
                
                if error_type == "timeout":
                    await asyncio.sleep(random.uniform(5, 10))  # Simulate timeout
                    raise asyncio.TimeoutError("Query timeout")
                elif error_type == "connection":
                    raise ConnectionError("Database connection failed")
                else:
                    raise ValueError("Invalid data format")
            
            try:
                mock_data = self.generate_mock_preference_data(request_id, "good")
                
                with patch.object(LegacyQueryExecutor, '_query_image_preference_stats') as mock_stats, \
                     patch.object(LegacyQueryExecutor, '_query_preference_data') as mock_prefs, \
                     patch.object(LegacyQueryExecutor, '_query_preference_jobs') as mock_jobs:
                    
                    mock_stats.return_value = mock_data["imagePreferenceStatsQuery"].data
                    mock_prefs.return_value = mock_data["preferenceDataQuery"].data
                    mock_jobs.return_value = mock_data["preferenceJobsQuery"].data
                    
                    executor = LegacyQueryExecutor()
                    query_results = {
                        "imagePreferenceStatsQuery": mock_data["imagePreferenceStatsQuery"],
                        "preferenceDataQuery": mock_data["preferenceDataQuery"],
                        "preferenceJobsQuery": mock_data["preferenceJobsQuery"]
                    }
                    
                    formatted_data = {name: result.data if result.success else [] 
                                    for name, result in query_results.items()}
                    
                    transformer = DocumentTransformer()
                    documents = transformer._chunk_preference_analysis(formatted_data)
                    
                    execution_time = time.time() - start_time
                    
                    return {
                        "request_id": request_id,
                        "success": True,
                        "execution_time": execution_time,
                        "document_count": len(documents)
                    }
                    
            except Exception as e:
                execution_time = time.time() - start_time
                return {
                    "request_id": request_id,
                    "success": False,
                    "execution_time": execution_time,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
        
        # Execute with error injection
        start_time = time.time()
        tasks = [process_with_error_injection(i) for i in range(total_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze error handling
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_results = [r for r in results if isinstance(r, dict) and not r.get("success")]
        exception_results = [r for r in results if isinstance(r, Exception)]
        
        # Error type analysis
        error_types = {}
        for result in failed_results:
            error_type = result.get("error_type", "Unknown")
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        print(f"\n=== Error Rate Load Test Results ===")
        print(f"Total requests: {total_requests}")
        print(f"Expected error rate: {error_injection_rate:.1%}")
        print(f"Successful: {len(successful_results)}")
        print(f"Failed: {len(failed_results)}")
        print(f"Exceptions: {len(exception_results)}")
        print(f"Actual error rate: {(len(failed_results) + len(exception_results)) / total_requests:.1%}")
        print(f"Total time: {total_time:.2f}s")
        
        print(f"\nError types:")
        for error_type, count in error_types.items():
            print(f"  {error_type}: {count}")
        
        # Assertions
        actual_error_rate = (len(failed_results) + len(exception_results)) / total_requests
        
        # Error rate should be close to injection rate (within 10% tolerance)
        assert abs(actual_error_rate - error_injection_rate) <= 0.1
        
        # System should handle errors gracefully (no complete failures)
        assert len(successful_results) > 0
        
        # Failed requests should have reasonable execution times (not hang indefinitely)
        failed_execution_times = [r["execution_time"] for r in failed_results]
        if failed_execution_times:
            assert max(failed_execution_times) < 15.0  # No request should take more than 15 seconds