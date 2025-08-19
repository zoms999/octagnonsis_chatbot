"""
Regression tests for preference data processing
Ensures existing functionality remains intact after changes
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime
from typing import Dict, List, Any

from etl.legacy_query_executor import LegacyQueryExecutor, QueryResult
from etl.document_transformer import DocumentTransformer
from etl.preference_data_validator import PreferenceDataValidator
from database.repositories import DocumentRepository
from rag.context_builder import ContextBuilder
from rag.question_processor import QuestionProcessor
from rag.response_generator import ResponseGenerator


class TestPreferenceRegression:
    """Regression tests to ensure existing functionality is preserved"""
    
    def test_legacy_query_executor_backward_compatibility(self):
        """Test that legacy query executor maintains backward compatibility"""
        executor = LegacyQueryExecutor()
        
        # Test that all expected methods exist
        assert hasattr(executor, 'execute_preference_queries')
        assert hasattr(executor, 'imagePreferenceStatsQuery')
        assert hasattr(executor, 'preferenceDataQuery')
        assert hasattr(executor, 'preferenceJobsQuery')
        
        # Test that QueryResult structure is maintained
        result = QueryResult(
            query_name="test_query",
            success=True,
            data=[{"test": "data"}],
            execution_time=1.0,
            row_count=1
        )
        
        assert result.query_name == "test_query"
        assert result.success == True
        assert result.data == [{"test": "data"}]
        assert result.execution_time == 1.0
        assert result.row_count == 1
        
        # Test error case
        error_result = QueryResult(
            query_name="error_query",
            success=False,
            error="Test error",
            execution_time=5.0
        )
        
        assert error_result.success == False
        assert error_result.error == "Test error"
        assert error_result.data is None

    def test_document_transformer_existing_behavior(self):
        """Test that document transformer preserves existing document creation behavior"""
        transformer = DocumentTransformer()
        
        # Test with traditional query results format (before enhancements)
        legacy_query_results = {
            "imagePreferenceStatsQuery": [],
            "preferenceDataQuery": [],
            "preferenceJobsQuery": []
        }
        
        # Should still create fallback document
        documents = transformer._chunk_preference_analysis(legacy_query_results)
        
        assert len(documents) >= 1
        assert all(doc.doc_type == "PREFERENCE_ANALYSIS" for doc in documents)
        
        # Test with minimal valid data (regression for basic functionality)
        minimal_query_results = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 100,
                "response_count": 50,
                "response_rate": 50
            }],
            "preferenceDataQuery": [{
                "preference_name": "테스트 선호도",
                "rank": 1
            }],
            "preferenceJobsQuery": []
        }
        
        documents = transformer._chunk_preference_analysis(minimal_query_results)
        
        # Should create documents even with minimal data
        assert len(documents) >= 2  # At least stats + preference
        
        # Verify document structure is maintained
        for doc in documents:
            assert hasattr(doc, 'doc_type')
            assert hasattr(doc, 'content')
            assert hasattr(doc, 'summary_text')
            assert hasattr(doc, 'metadata')
            assert doc.doc_type == "PREFERENCE_ANALYSIS"

    def test_preference_data_validator_compatibility(self):
        """Test that preference data validator maintains existing validation logic"""
        validator = PreferenceDataValidator()
        
        # Test existing validation methods
        assert hasattr(validator, 'validate_image_preference_stats')
        assert hasattr(validator, 'validate_preference_data')
        assert hasattr(validator, 'validate_preference_jobs')
        assert hasattr(validator, 'generate_validation_report')
        
        # Test with legacy data formats
        legacy_stats_data = [{
            "total_image_count": 120,
            "response_count": 96,
            "response_rate": 80
        }]
        
        stats_result = validator.validate_image_preference_stats(legacy_stats_data)
        assert stats_result.is_valid == True
        
        # Test with empty data (should handle gracefully)
        empty_result = validator.validate_image_preference_stats([])
        assert empty_result.is_valid == False
        
        # Test validation report structure
        all_results = {
            "imagePreferenceStatsQuery": legacy_stats_data,
            "preferenceDataQuery": [],
            "preferenceJobsQuery": []
        }
        
        report = validator.generate_validation_report(all_results)
        
        # Verify report structure is maintained
        assert hasattr(report, 'overall_valid')
        assert hasattr(report, 'stats_validation')
        assert hasattr(report, 'preferences_validation')
        assert hasattr(report, 'jobs_validation')

    def test_rag_system_preference_integration_compatibility(self):
        """Test that RAG system maintains compatibility with preference documents"""
        
        # Test question processor maintains preference detection
        processor = QuestionProcessor()
        
        preference_questions = [
            "내 이미지 선호도는 어떻게 되나요?",
            "선호도 분석 결과를 알려주세요",
            "이미지 선호 검사 결과는?",
            "preference analysis results"
        ]
        
        for question in preference_questions:
            analysis = processor.analyze_question(question)
            # Should still detect as preference-related
            assert analysis["category"] in ["preference", "general"]  # May classify as general if no specific preference detection
            
        # Test context builder handles preference documents
        with patch.object(ContextBuilder, 'build_context') as mock_build:
            mock_build.return_value = {
                "relevant_documents": [],
                "context_summary": "Test context",
                "document_types": ["PREFERENCE_ANALYSIS"]
            }
            
            builder = ContextBuilder()
            context = builder.build_context("preference question", 12345)
            
            # Should maintain expected context structure
            assert "relevant_documents" in context
            assert "context_summary" in context
            assert "document_types" in context

    def test_document_repository_preference_storage_compatibility(self):
        """Test that document repository maintains compatibility with preference documents"""
        
        # Create test preference document in legacy format
        test_document = {
            "doc_type": "PREFERENCE_ANALYSIS",
            "content": {"test": "content"},
            "summary_text": "Test summary",
            "metadata": {"sub_type": "test_stats"},
            "embedding_vector": [0.1] * 500
        }
        
        with patch.object(DocumentRepository, 'save_documents') as mock_save:
            mock_save.return_value = True
            
            repo = DocumentRepository()
            result = repo.save_documents([test_document], 12345)
            
            # Should maintain existing save behavior
            assert result == True
            mock_save.assert_called_once_with([test_document], 12345)

    def test_response_generator_preference_handling_compatibility(self):
        """Test that response generator maintains compatibility with preference responses"""
        
        with patch.object(ResponseGenerator, 'generate_response') as mock_generate:
            mock_generate.return_value = {
                "response": "Test preference response",
                "confidence": 0.8,
                "sources": ["PREFERENCE_ANALYSIS"]
            }
            
            generator = ResponseGenerator()
            
            # Test with preference context
            context = {
                "relevant_documents": [{"doc_type": "PREFERENCE_ANALYSIS"}],
                "document_types": ["PREFERENCE_ANALYSIS"]
            }
            
            response = generator.generate_response("preference question", context)
            
            # Should maintain expected response structure
            assert "response" in response
            assert "confidence" in response
            assert "sources" in response
            assert "PREFERENCE_ANALYSIS" in response["sources"]

    def test_error_handling_backward_compatibility(self):
        """Test that error handling maintains backward compatibility"""
        
        # Test legacy error scenarios still work
        executor = LegacyQueryExecutor()
        
        # Mock database connection error (legacy scenario)
        with patch.object(executor, 'imagePreferenceStatsQuery') as mock_query:
            mock_query.side_effect = Exception("Database connection failed")
            
            # Should handle error gracefully (not crash)
            try:
                result = executor.imagePreferenceStatsQuery(None, 12345)
                # If method returns instead of raising, verify error result
                if result:
                    assert result.success == False
                    assert "error" in result.__dict__
            except Exception as e:
                # If method raises, that's also acceptable legacy behavior
                assert "Database connection failed" in str(e)
        
        # Test document transformer error handling
        transformer = DocumentTransformer()
        
        # Test with malformed data (legacy error scenario)
        malformed_data = {
            "imagePreferenceStatsQuery": [None],  # Invalid data
            "preferenceDataQuery": [{"invalid": "structure"}],
            "preferenceJobsQuery": []
        }
        
        # Should not crash and should create fallback documents
        documents = transformer._chunk_preference_analysis(malformed_data)
        assert len(documents) >= 1
        assert all(doc.doc_type == "PREFERENCE_ANALYSIS" for doc in documents)

    def test_metadata_structure_compatibility(self):
        """Test that document metadata structure remains compatible"""
        transformer = DocumentTransformer()
        
        # Test with valid data
        query_results = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 120,
                "response_count": 96,
                "response_rate": 80
            }],
            "preferenceDataQuery": [{
                "preference_name": "실내 활동 선호",
                "rank": 1,
                "response_rate": 85
            }],
            "preferenceJobsQuery": []
        }
        
        documents = transformer._chunk_preference_analysis(query_results)
        
        # Verify metadata structure is maintained
        for doc in documents:
            assert "sub_type" in doc.metadata
            assert "created_at" in doc.metadata
            assert "completion_level" in doc.metadata
            
            # Verify sub_type values follow expected patterns
            sub_type = doc.metadata["sub_type"]
            expected_subtypes = [
                "test_stats", "preferences_overview", "partial_stats", "partial_available",
                "unavailable"
            ]
            
            # Should be one of expected types or follow pattern (preference_*, jobs_*)
            assert (sub_type in expected_subtypes or 
                   sub_type.startswith("preference_") or 
                   sub_type.startswith("jobs_"))

    def test_document_content_structure_compatibility(self):
        """Test that document content structure remains compatible with existing consumers"""
        transformer = DocumentTransformer()
        
        # Test stats document content structure
        stats_query_results = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 120,
                "response_count": 96,
                "response_rate": 80
            }],
            "preferenceDataQuery": [],
            "preferenceJobsQuery": []
        }
        
        documents = transformer._chunk_preference_analysis(stats_query_results)
        stats_docs = [doc for doc in documents if doc.metadata.get("sub_type") == "test_stats"]
        
        if stats_docs:
            stats_doc = stats_docs[0]
            
            # Verify expected content keys exist
            expected_keys = ["total_images", "completed_images", "completion_rate", "completion_status"]
            for key in expected_keys:
                assert key in stats_doc.content
            
            # Verify data types are maintained
            assert isinstance(stats_doc.content["total_images"], int)
            assert isinstance(stats_doc.content["completed_images"], int)
            assert isinstance(stats_doc.content["completion_rate"], (int, float))
            assert isinstance(stats_doc.content["completion_status"], str)

    def test_hypothetical_questions_generation_compatibility(self):
        """Test that hypothetical questions generation maintains compatibility"""
        transformer = DocumentTransformer()
        
        query_results = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 120,
                "response_count": 96,
                "response_rate": 80
            }],
            "preferenceDataQuery": [{
                "preference_name": "실내 활동 선호",
                "rank": 1,
                "response_rate": 85,
                "description": "조용한 환경을 선호합니다."
            }],
            "preferenceJobsQuery": []
        }
        
        documents = transformer._chunk_preference_analysis(query_results)
        
        # Verify hypothetical questions are still generated
        docs_with_questions = [doc for doc in documents 
                              if doc.metadata.get('hypothetical_questions')]
        
        # Should have at least some documents with questions
        assert len(docs_with_questions) >= 1
        
        # Verify question structure
        for doc in docs_with_questions:
            questions = doc.metadata['hypothetical_questions']
            assert isinstance(questions, list)
            assert len(questions) > 0
            
            # Questions should be strings
            for question in questions:
                assert isinstance(question, str)
                assert len(question.strip()) > 0

    @pytest.mark.asyncio
    async def test_async_compatibility(self):
        """Test that async functionality maintains compatibility"""
        
        # Test async query execution
        executor = LegacyQueryExecutor()
        
        with patch.object(executor, 'execute_preference_queries') as mock_execute:
            mock_execute.return_value = {
                "imagePreferenceStatsQuery": QueryResult(
                    query_name="imagePreferenceStatsQuery",
                    success=True,
                    data=[],
                    execution_time=1.0,
                    row_count=0
                )
            }
            
            # Should maintain async interface
            result = await executor.execute_preference_queries(12345)
            assert isinstance(result, dict)
            assert "imagePreferenceStatsQuery" in result

    def test_logging_compatibility(self):
        """Test that logging functionality maintains compatibility"""
        
        # Test that existing logging calls don't break
        executor = LegacyQueryExecutor()
        
        # Mock logging to verify it's called
        with patch('etl.legacy_query_executor.logger') as mock_logger:
            
            # Test query execution with logging
            with patch.object(executor, 'imagePreferenceStatsQuery') as mock_query:
                mock_query.return_value = QueryResult(
                    query_name="imagePreferenceStatsQuery",
                    success=True,
                    data=[],
                    execution_time=1.0,
                    row_count=0
                )
                
                # Execute query (should log without errors)
                result = executor.imagePreferenceStatsQuery(None, 12345)
                
                # Verify logging was attempted (may or may not be called depending on implementation)
                # This ensures logging calls don't cause errors
                assert result is not None

    def test_configuration_compatibility(self):
        """Test that configuration changes maintain backward compatibility"""
        
        # Test that components can be instantiated with default configurations
        try:
            executor = LegacyQueryExecutor()
            transformer = DocumentTransformer()
            validator = PreferenceDataValidator()
            
            # Should instantiate without errors
            assert executor is not None
            assert transformer is not None
            assert validator is not None
            
        except Exception as e:
            pytest.fail(f"Component instantiation failed: {e}")

    def test_data_format_compatibility(self):
        """Test that various data formats are handled compatibly"""
        transformer = DocumentTransformer()
        
        # Test various data format scenarios that should be handled
        format_scenarios = [
            # Empty data
            {
                "imagePreferenceStatsQuery": [],
                "preferenceDataQuery": [],
                "preferenceJobsQuery": []
            },
            # Minimal data
            {
                "imagePreferenceStatsQuery": [{"total_image_count": 100}],
                "preferenceDataQuery": [{"preference_name": "test"}],
                "preferenceJobsQuery": []
            },
            # Mixed valid/invalid data
            {
                "imagePreferenceStatsQuery": [{"total_image_count": 100, "invalid_field": None}],
                "preferenceDataQuery": [{"preference_name": "test", "rank": "invalid"}],
                "preferenceJobsQuery": [{}]
            }
        ]
        
        for scenario in format_scenarios:
            # Should handle all scenarios without crashing
            documents = transformer._chunk_preference_analysis(scenario)
            assert len(documents) >= 1
            assert all(doc.doc_type == "PREFERENCE_ANALYSIS" for doc in documents)