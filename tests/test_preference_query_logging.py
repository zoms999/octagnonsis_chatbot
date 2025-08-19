"""
Unit tests for preference query logging and diagnostics functionality
Tests the enhanced logging and diagnostic methods added to legacy_query_executor.py
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any, List

from etl.legacy_query_executor import (
    AptitudeTestQueries, 
    LegacyQueryExecutor, 
    PreferenceQueryDiagnostics,
    PreferenceDataReport,
    QueryResult
)


def create_mock_aptitude_queries(mock_session):
    """Helper function to create AptitudeTestQueries with proper mocking"""
    with patch('database.connection.db_manager') as mock_db_manager:
        mock_db_manager.get_sync_session.return_value = mock_session
        return AptitudeTestQueries(mock_session)


class TestPreferenceQueryLogging:
    """Test preference query logging functionality"""
    
    @pytest.fixture
    def mock_session(self):
        """Mock database session"""
        session = Mock()
        return session
    
    @pytest.fixture
    def aptitude_queries(self, mock_session):
        """Create AptitudeTestQueries instance with mocked session"""
        return create_mock_aptitude_queries(mock_session)
    
    @pytest.fixture
    def legacy_executor(self):
        """Create LegacyQueryExecutor instance"""
        return LegacyQueryExecutor(max_retries=1, retry_delay=0.1, query_timeout=5.0)
    
    def test_image_preference_stats_query_logging_success(self, aptitude_queries, mock_session):
        """Test successful execution logging for image preference stats query"""
        # Mock database response
        mock_result = [
            {
                "total_image_count": 100,
                "response_count": 85,
                "response_rate": 85
            }
        ]
        
        with patch.object(aptitude_queries, '_run', return_value=mock_result) as mock_run:
            with patch('etl.legacy_query_executor.preference_logger') as mock_logger:
                result = aptitude_queries._query_image_preference_stats(12345)
                
                # Verify query was called correctly
                assert mock_run.call_count == 1
                call_args = mock_run.call_args
                assert call_args[0][1] == {"anp_seq": 12345}  # Check parameters
                assert "SELECT" in call_args[0][0]  # Check SQL contains SELECT
                
                # Verify result
                assert result == mock_result
                
                # Verify logging calls
                assert mock_logger.info.call_count == 2  # Start and completion logs
                
                # Check start log
                start_call = mock_logger.info.call_args_list[0]
                assert "Starting preference query execution" in start_call[0][0]
                assert start_call[1]["anp_seq"] == 12345
                assert start_call[1]["query_name"] == "imagePreferenceStatsQuery"
                
                # Check completion log
                completion_call = mock_logger.info.call_args_list[1]
                assert "Preference query completed successfully" in completion_call[0][0]
                assert completion_call[1]["anp_seq"] == 12345
                assert completion_call[1]["query_name"] == "imagePreferenceStatsQuery"
                assert completion_call[1]["row_count"] == 1
                assert completion_call[1]["has_data"] is True
                assert "execution_time" in completion_call[1]
    
    def test_image_preference_stats_query_logging_failure(self, aptitude_queries):
        """Test failure logging for image preference stats query"""
        # Mock database error
        mock_error = Exception("Database connection failed")
        
        with patch.object(aptitude_queries, '_run', side_effect=mock_error):
            with patch('etl.legacy_query_executor.preference_logger') as mock_logger:
                with pytest.raises(Exception):
                    aptitude_queries._query_image_preference_stats(12345)
                
                # Verify logging calls
                assert mock_logger.info.call_count == 1  # Start log only
                assert mock_logger.error.call_count == 1  # Error log
                
                # Check error log
                error_call = mock_logger.error.call_args_list[0]
                assert "Preference query failed" in error_call[0][0]
                assert error_call[1]["anp_seq"] == 12345
                assert error_call[1]["query_name"] == "imagePreferenceStatsQuery"
                assert error_call[1]["error_type"] == "Exception"
                assert "Database connection failed" in error_call[1]["error_message"]
    
    def test_preference_data_query_logging_with_quality_info(self, aptitude_queries, mock_session):
        """Test preference data query logging with data quality information"""
        # Mock database response with preference data
        mock_result = [
            {
                "preference_name": "창의적 성향",
                "question_count": 20,
                "response_rate": 85,
                "rank": 1,
                "description": "창의적 사고를 선호합니다"
            },
            {
                "preference_name": "논리적 성향",
                "question_count": 18,
                "response_rate": 78,
                "rank": 2,
                "description": "논리적 분석을 선호합니다"
            },
            {
                "preference_name": "협력적 성향",
                "question_count": 22,
                "response_rate": 92,
                "rank": 3,
                "description": "팀워크를 선호합니다"
            }
        ]
        
        with patch.object(aptitude_queries, '_run', return_value=mock_result):
            with patch('etl.legacy_query_executor.preference_logger') as mock_logger:
                result = aptitude_queries._query_preference_data(12345)
                
                # Verify result
                assert result == mock_result
                
                # Check completion log with data quality info
                completion_call = mock_logger.info.call_args_list[1]
                data_quality = completion_call[1]["data_quality"]
                
                assert data_quality["preferences_found"] == 3
                assert data_quality["has_top_3_preferences"] is True
                assert data_quality["response_rates"] == [85, 78, 92]
                assert data_quality["avg_response_rate"] == 85.0
    
    def test_preference_jobs_query_logging_with_type_analysis(self, aptitude_queries, mock_session):
        """Test preference jobs query logging with preference type analysis"""
        # Mock database response with job data for different preference types
        mock_result = [
            {
                "preference_name": "창의적 성향",
                "preference_type": "rimg1",
                "jo_name": "그래픽 디자이너",
                "jo_outline": "시각 디자인 업무",
                "jo_mainbusiness": "광고, 웹 디자인",
                "majors": "시각디자인, 멀티미디어"
            },
            {
                "preference_name": "논리적 성향",
                "preference_type": "rimg2",
                "jo_name": "소프트웨어 개발자",
                "jo_outline": "프로그램 개발",
                "jo_mainbusiness": "시스템 개발, 앱 개발",
                "majors": "컴퓨터공학, 소프트웨어공학"
            },
            {
                "preference_name": "협력적 성향",
                "preference_type": "rimg3",
                "jo_name": "프로젝트 매니저",
                "jo_outline": "프로젝트 관리",
                "jo_mainbusiness": "팀 관리, 일정 관리",
                "majors": "경영학, 산업공학"
            }
        ]
        
        with patch.object(aptitude_queries, '_run', return_value=mock_result):
            with patch('etl.legacy_query_executor.preference_logger') as mock_logger:
                result = aptitude_queries._query_preference_jobs(12345)
                
                # Verify result
                assert result == mock_result
                
                # Check completion log with data quality info
                completion_call = mock_logger.info.call_args_list[1]
                data_quality = completion_call[1]["data_quality"]
                
                assert data_quality["total_jobs"] == 3
                assert set(data_quality["preference_types_found"]) == {"rimg1", "rimg2", "rimg3"}
                assert data_quality["jobs_by_preference_type"]["rimg1"] == 1
                assert data_quality["jobs_by_preference_type"]["rimg2"] == 1
                assert data_quality["jobs_by_preference_type"]["rimg3"] == 1
                assert data_quality["has_all_preference_types"] is True


class TestPreferenceDiagnostics:
    """Test preference query diagnostics functionality"""
    
    @pytest.fixture
    def mock_session(self):
        """Mock database session"""
        return Mock()
    
    @pytest.fixture
    def aptitude_queries(self, mock_session):
        """Create AptitudeTestQueries instance with mocked session"""
        return create_mock_aptitude_queries(mock_session)
    
    def test_diagnose_preference_queries_all_successful(self, aptitude_queries):
        """Test diagnostic method when all preference queries succeed"""
        # Mock successful query results
        mock_stats_result = [{"total_image_count": 100, "response_count": 85, "response_rate": 85}]
        mock_data_result = [
            {"preference_name": "창의적", "question_count": 20, "response_rate": 85, "rank": 1, "description": "설명1"},
            {"preference_name": "논리적", "question_count": 18, "response_rate": 78, "rank": 2, "description": "설명2"},
            {"preference_name": "협력적", "question_count": 22, "response_rate": 92, "rank": 3, "description": "설명3"}
        ]
        mock_jobs_result = [
            {"preference_name": "창의적", "preference_type": "rimg1", "jo_name": "디자이너", "jo_outline": "디자인", "jo_mainbusiness": "광고", "majors": "디자인"},
            {"preference_name": "논리적", "preference_type": "rimg2", "jo_name": "개발자", "jo_outline": "개발", "jo_mainbusiness": "소프트웨어", "majors": "컴공"},
            {"preference_name": "협력적", "preference_type": "rimg3", "jo_name": "매니저", "jo_outline": "관리", "jo_mainbusiness": "프로젝트", "majors": "경영"}
        ]
        
        with patch.object(aptitude_queries, '_query_image_preference_stats', return_value=mock_stats_result):
            with patch.object(aptitude_queries, '_query_preference_data', return_value=mock_data_result):
                with patch.object(aptitude_queries, '_query_preference_jobs', return_value=mock_jobs_result):
                    with patch('etl.legacy_query_executor.preference_logger'):
                        report = aptitude_queries.diagnose_preference_queries(12345)
        
        # Verify report structure
        assert isinstance(report, PreferenceDataReport)
        assert report.anp_seq == 12345
        assert report.total_queries == 3
        assert report.successful_queries == 3
        assert report.failed_queries == 0
        assert report.total_execution_time > 0
        
        # Verify data availability
        assert report.data_availability["imagePreferenceStatsQuery"] is True
        assert report.data_availability["preferenceDataQuery"] is True
        assert report.data_availability["preferenceJobsQuery"] is True
        
        # Verify diagnostics
        assert len(report.diagnostics) == 3
        for diagnostic in report.diagnostics:
            assert isinstance(diagnostic, PreferenceQueryDiagnostics)
            assert diagnostic.success is True
            assert diagnostic.row_count > 0
            assert diagnostic.data_quality_score is not None
            assert diagnostic.data_quality_score > 0
        
        # Verify recommendations
        assert len(report.recommendations) > 0
        assert "All preference queries are functioning correctly" in report.recommendations
    
    def test_diagnose_preference_queries_with_failures(self, aptitude_queries):
        """Test diagnostic method when some preference queries fail"""
        # Mock mixed results - some success, some failure
        mock_stats_result = [{"total_image_count": 100, "response_count": 85, "response_rate": 85}]
        mock_error = Exception("Database connection failed")
        
        with patch.object(aptitude_queries, '_query_image_preference_stats', return_value=mock_stats_result):
            with patch.object(aptitude_queries, '_query_preference_data', side_effect=mock_error):
                with patch.object(aptitude_queries, '_query_preference_jobs', side_effect=mock_error):
                    with patch('etl.legacy_query_executor.preference_logger'):
                        report = aptitude_queries.diagnose_preference_queries(12345)
        
        # Verify report shows mixed results
        assert report.anp_seq == 12345
        assert report.total_queries == 3
        assert report.successful_queries == 1
        assert report.failed_queries == 2
        
        # Verify data availability
        assert report.data_availability["imagePreferenceStatsQuery"] is True
        assert report.data_availability["preferenceDataQuery"] is False
        assert report.data_availability["preferenceJobsQuery"] is False
        
        # Verify diagnostics include both success and failure
        successful_diagnostics = [d for d in report.diagnostics if d.success]
        failed_diagnostics = [d for d in report.diagnostics if not d.success]
        
        assert len(successful_diagnostics) == 1
        assert len(failed_diagnostics) == 2
        
        # Verify error details in failed diagnostics
        for diagnostic in failed_diagnostics:
            assert diagnostic.error_details is not None
            assert "Database connection failed" in diagnostic.error_details
        
        # Verify recommendations include failure-related suggestions
        recommendations_text = " ".join(report.recommendations)
        assert "database connectivity issues" in recommendations_text.lower()
        assert "missing preference data" in recommendations_text.lower()
    
    def test_calculate_data_quality_score_image_stats(self, aptitude_queries):
        """Test data quality score calculation for image preference stats"""
        # Test high quality data
        high_quality_data = [{"total_image_count": 100, "response_count": 85, "response_rate": 85}]
        score = aptitude_queries._calculate_data_quality_score("imagePreferenceStatsQuery", high_quality_data)
        assert score == 1.0  # Perfect score
        
        # Test medium quality data
        medium_quality_data = [{"total_image_count": 100, "response_count": 40, "response_rate": 40}]
        score = aptitude_queries._calculate_data_quality_score("imagePreferenceStatsQuery", medium_quality_data)
        assert 0.5 < score < 1.0
        
        # Test low quality data
        low_quality_data = [{"total_image_count": 0, "response_count": 0, "response_rate": 0}]
        score = aptitude_queries._calculate_data_quality_score("imagePreferenceStatsQuery", low_quality_data)
        assert score == 0.0
        
        # Test empty data
        empty_data = []
        score = aptitude_queries._calculate_data_quality_score("imagePreferenceStatsQuery", empty_data)
        assert score == 0.0
    
    def test_identify_validation_issues_preference_data(self, aptitude_queries):
        """Test validation issue identification for preference data"""
        # Test data with no issues
        good_data = [
            {"preference_name": "창의적", "question_count": 20, "response_rate": 85, "rank": 1, "description": "설명1"},
            {"preference_name": "논리적", "question_count": 18, "response_rate": 78, "rank": 2, "description": "설명2"},
            {"preference_name": "협력적", "question_count": 22, "response_rate": 92, "rank": 3, "description": "설명3"}
        ]
        issues = aptitude_queries._identify_validation_issues("preferenceDataQuery", good_data)
        assert len(issues) == 0
        
        # Test data with missing preferences
        incomplete_data = [
            {"preference_name": "창의적", "question_count": 20, "response_rate": 85, "rank": 1, "description": "설명1"}
        ]
        issues = aptitude_queries._identify_validation_issues("preferenceDataQuery", incomplete_data)
        assert "Expected 3 preferences, got 1" in issues
        
        # Test data with low response rates
        low_response_data = [
            {"preference_name": "창의적", "question_count": 20, "response_rate": 15, "rank": 1, "description": "설명1"},
            {"preference_name": "논리적", "question_count": 18, "response_rate": 25, "rank": 2, "description": "설명2"},
            {"preference_name": "협력적", "question_count": 22, "response_rate": 20, "rank": 3, "description": "설명3"}
        ]
        issues = aptitude_queries._identify_validation_issues("preferenceDataQuery", low_response_data)
        low_response_issues = [issue for issue in issues if "Low response rate" in issue]
        assert len(low_response_issues) == 3  # All three have low response rates
        
        # Test empty data
        empty_data = []
        issues = aptitude_queries._identify_validation_issues("preferenceDataQuery", empty_data)
        assert "No data returned" in issues


class TestLegacyExecutorPreferenceLogging:
    """Test preference logging in LegacyQueryExecutor"""
    
    @pytest.fixture
    def legacy_executor(self):
        """Create LegacyQueryExecutor instance"""
        return LegacyQueryExecutor(max_retries=1, retry_delay=0.1, query_timeout=5.0)
    
    @pytest.fixture
    def mock_session(self):
        """Mock database session"""
        return Mock()
    
    @pytest.mark.asyncio
    async def test_diagnose_preference_queries_async(self, legacy_executor, mock_session):
        """Test async preference diagnostics method"""
        # Mock the synchronous diagnose method
        mock_report = PreferenceDataReport(
            anp_seq=12345,
            total_queries=3,
            successful_queries=3,
            failed_queries=0,
            total_execution_time=1.5,
            data_availability={
                "imagePreferenceStatsQuery": True,
                "preferenceDataQuery": True,
                "preferenceJobsQuery": True
            },
            diagnostics=[],
            recommendations=["All preference queries are functioning correctly"]
        )
        
        with patch('etl.legacy_query_executor.AptitudeTestQueries') as mock_queries_class:
            mock_queries_instance = Mock()
            mock_queries_instance.diagnose_preference_queries.return_value = mock_report
            mock_queries_class.return_value = mock_queries_instance
            
            report = await legacy_executor.diagnose_preference_queries_async(mock_session, 12345)
            
            # Verify the report was returned correctly
            assert isinstance(report, PreferenceDataReport)
            assert report.anp_seq == 12345
            assert report.successful_queries == 3
            assert report.failed_queries == 0
    
    @pytest.mark.asyncio
    async def test_diagnose_preference_queries_async_failure(self, legacy_executor, mock_session):
        """Test async preference diagnostics method when it fails"""
        # Mock the synchronous diagnose method to raise an exception
        with patch('etl.legacy_query_executor.AptitudeTestQueries') as mock_queries_class:
            mock_queries_class.side_effect = Exception("Database error")
            
            report = await legacy_executor.diagnose_preference_queries_async(mock_session, 12345)
            
            # Verify fallback report is returned
            assert isinstance(report, PreferenceDataReport)
            assert report.anp_seq == 12345
            assert report.successful_queries == 0
            assert report.failed_queries == 3
            assert "Failed to execute preference diagnostics" in report.recommendations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])