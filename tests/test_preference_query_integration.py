"""
Integration tests for preference query error handling and validation
Tests the complete flow from async executor to preference query validation
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from sqlalchemy.exc import DisconnectionError, OperationalError

from etl.legacy_query_executor import LegacyQueryExecutor, QueryResult


class TestPreferenceQueryIntegration:
    """Integration tests for preference query error handling"""
    
    @pytest.fixture
    def executor(self):
        """Create LegacyQueryExecutor instance for testing"""
        return LegacyQueryExecutor(max_retries=1, retry_delay=0.1, query_timeout=2.0)
    
    @pytest.fixture
    def mock_session(self):
        """Create mock database session"""
        return Mock(spec=Session)

    @pytest.mark.asyncio
    async def test_preference_query_success_flow(self, executor, mock_session):
        """Test successful preference query execution flow"""
        
        # Mock successful query execution
        mock_data = {
            "imagePreferenceStatsQuery": [
                {"total_image_count": 100, "response_count": 85, "response_rate": 85}
            ]
        }
        
        with patch('etl.legacy_query_executor.AptitudeTestQueries') as MockQueries:
            mock_instance = MockQueries.return_value
            mock_instance.execute_all_queries.return_value = mock_data
            
            result = await executor._execute_single_query_with_retry(
                mock_session, 12345, "imagePreferenceStatsQuery"
            )
            
            assert result.success is True
            assert result.data is not None
            assert len(result.data) == 1
            assert result.data[0]["response_rate"] == 85

    @pytest.mark.asyncio
    async def test_preference_query_connection_retry_flow(self, executor, mock_session):
        """Test connection error retry flow for preference queries"""
        
        with patch('etl.legacy_query_executor.AptitudeTestQueries') as MockQueries:
            mock_instance = MockQueries.return_value
            
            # First call fails with connection error, second succeeds
            mock_instance.execute_all_queries.side_effect = [
                DisconnectionError("Connection lost", None, None),
                {"imagePreferenceStatsQuery": [{"total_image_count": 50, "response_count": 40, "response_rate": 80}]}
            ]
            
            result = await executor._execute_single_query_with_retry(
                mock_session, 12345, "imagePreferenceStatsQuery"
            )
            
            assert result.success is True
            assert result.data is not None
            assert mock_instance.execute_all_queries.call_count == 2

    @pytest.mark.asyncio
    async def test_preference_query_validation_failure_flow(self, executor, mock_session):
        """Test validation failure flow for preference queries"""
        
        # Mock query returning invalid data
        invalid_data = {
            "imagePreferenceStatsQuery": [
                {"invalid_field": "value"}  # Missing required fields
            ]
        }
        
        with patch('etl.legacy_query_executor.AptitudeTestQueries') as MockQueries:
            mock_instance = MockQueries.return_value
            mock_instance.execute_all_queries.return_value = invalid_data
            
            result = await executor._execute_single_query_with_retry(
                mock_session, 12345, "imagePreferenceStatsQuery"
            )
            
            assert result.success is False
            assert "validation failed" in result.error.lower()
            # Should not retry on validation errors
            assert mock_instance.execute_all_queries.call_count == 1

    @pytest.mark.asyncio
    async def test_preference_query_timeout_retry_flow(self, executor, mock_session):
        """Test timeout retry flow for preference queries"""
        
        with patch('etl.legacy_query_executor.AptitudeTestQueries') as MockQueries, \
             patch('asyncio.wait_for') as mock_wait_for:
            
            mock_instance = MockQueries.return_value
            
            # First two calls timeout, third succeeds
            mock_wait_for.side_effect = [
                asyncio.TimeoutError(),
                asyncio.TimeoutError(),
                [{"total_image_count": 75, "response_count": 60, "response_rate": 80}]
            ]
            
            result = await executor._execute_single_query_with_retry(
                mock_session, 12345, "imagePreferenceStatsQuery"
            )
            
            assert result.success is True
            assert mock_wait_for.call_count == 3

    @pytest.mark.asyncio
    async def test_preference_query_max_retries_exhausted_flow(self, executor, mock_session):
        """Test behavior when max retries are exhausted"""
        
        with patch('etl.legacy_query_executor.AptitudeTestQueries') as MockQueries:
            mock_instance = MockQueries.return_value
            mock_instance.execute_all_queries.side_effect = OperationalError("Database error", None, None)
            
            result = await executor._execute_single_query_with_retry(
                mock_session, 12345, "imagePreferenceStatsQuery"
            )
            
            assert result.success is False
            assert "connection error" in result.error.lower()
            # Should retry max_retries + 2 times for preference queries (enhanced retry)
            assert mock_instance.execute_all_queries.call_count == executor.max_retries + 3

    @pytest.mark.asyncio
    async def test_multiple_preference_queries_execution(self, executor, mock_session):
        """Test execution of multiple preference queries"""
        
        mock_data = {
            "imagePreferenceStatsQuery": [{"total_image_count": 100, "response_count": 85, "response_rate": 85}],
            "preferenceDataQuery": [
                {"preference_name": "Visual", "question_count": 20, "response_rate": 80, "rank": 1, "description": "Test"}
            ],
            "preferenceJobsQuery": [
                {"preference_name": "Visual", "preference_type": "rimg1", "jo_name": "Designer", 
                 "jo_outline": "Test", "jo_mainbusiness": "Test", "majors": "Art"}
            ]
        }
        
        with patch('etl.legacy_query_executor.AptitudeTestQueries') as MockQueries:
            mock_instance = MockQueries.return_value
            mock_instance.execute_all_queries.return_value = mock_data
            
            # Execute all preference queries
            tasks = [
                executor._execute_single_query_with_retry(mock_session, 12345, "imagePreferenceStatsQuery"),
                executor._execute_single_query_with_retry(mock_session, 12345, "preferenceDataQuery"),
                executor._execute_single_query_with_retry(mock_session, 12345, "preferenceJobsQuery")
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert all(result.success for result in results)
            assert len(results) == 3
            
            # Verify each query type returned expected data
            stats_result = next(r for r in results if r.query_name == "imagePreferenceStatsQuery")
            assert stats_result.data[0]["response_rate"] == 85
            
            data_result = next(r for r in results if r.query_name == "preferenceDataQuery")
            assert data_result.data[0]["preference_name"] == "Visual"
            
            jobs_result = next(r for r in results if r.query_name == "preferenceJobsQuery")
            assert jobs_result.data[0]["preference_type"] == "rimg1"

    @pytest.mark.asyncio
    async def test_preference_query_diagnostics_integration(self, executor, mock_session):
        """Test preference query diagnostics integration"""
        
        # Create a real report object to return
        from etl.legacy_query_executor import PreferenceDataReport, PreferenceQueryDiagnostics
        
        mock_report = PreferenceDataReport(
            anp_seq=12345,
            total_queries=3,
            successful_queries=2,
            failed_queries=1,
            total_execution_time=1.5,
            data_availability={
                "imagePreferenceStatsQuery": True,
                "preferenceDataQuery": False,
                "preferenceJobsQuery": False
            },
            diagnostics=[
                PreferenceQueryDiagnostics(
                    anp_seq=12345,
                    query_name="imagePreferenceStatsQuery",
                    execution_time=0.5,
                    success=True,
                    row_count=1
                )
            ],
            recommendations=["Test recommendation"]
        )
        
        # Mock the diagnostics method to return our mock report
        with patch('etl.legacy_query_executor.AptitudeTestQueries') as MockQueries:
            mock_instance = MockQueries.return_value
            mock_instance.diagnose_preference_queries.return_value = mock_report
            
            report = await executor.diagnose_preference_queries_async(mock_session, 12345)
            
            assert report.anp_seq == 12345
            assert report.total_queries == 3
            assert report.failed_queries >= 1  # At least the connection error
            assert len(report.recommendations) > 0

    @pytest.mark.asyncio
    async def test_preference_query_empty_results_handling(self, executor, mock_session):
        """Test handling of empty results from preference queries"""
        
        # Mock empty results for all preference queries
        empty_data = {
            "imagePreferenceStatsQuery": [],
            "preferenceDataQuery": [],
            "preferenceJobsQuery": []
        }
        
        with patch('etl.legacy_query_executor.AptitudeTestQueries') as MockQueries:
            mock_instance = MockQueries.return_value
            mock_instance.execute_all_queries.return_value = empty_data
            
            tasks = [
                executor._execute_single_query_with_retry(mock_session, 12345, "imagePreferenceStatsQuery"),
                executor._execute_single_query_with_retry(mock_session, 12345, "preferenceDataQuery"),
                executor._execute_single_query_with_retry(mock_session, 12345, "preferenceJobsQuery")
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Empty results should still be considered successful
            assert all(result.success for result in results)
            assert all(len(result.data) == 0 for result in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])