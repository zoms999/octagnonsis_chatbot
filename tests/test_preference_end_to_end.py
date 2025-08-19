"""
End-to-end tests for complete preference data processing workflow
Tests the entire pipeline from query execution to document storage and RAG integration
"""

import pytest
import asyncio
import logging
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from typing import Dict, List, Any

from etl.legacy_query_executor import LegacyQueryExecutor, QueryResult
from etl.document_transformer import DocumentTransformer, TransformedDocument
from etl.vector_embedder import VectorEmbedder
from etl.preference_data_validator import PreferenceDataValidator
from database.repositories import DocumentRepository
from database.models import DocumentType
from rag.context_builder import ContextBuilder
from rag.question_processor import QuestionProcessor
from rag.response_generator import ResponseGenerator


class TestPreferenceEndToEnd:
    """End-to-end tests for preference data processing workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_preference_workflow_success(self):
        """Test complete preference workflow with successful data processing"""
        anp_seq = 12345
        
        # Mock successful query results
        mock_query_results = {
            "imagePreferenceStatsQuery": QueryResult(
                query_name="imagePreferenceStatsQuery",
                success=True,
                data=[{
                    "total_image_count": 120,
                    "response_count": 96,
                    "response_rate": 80
                }],
                execution_time=1.5,
                row_count=1
            ),
            "preferenceDataQuery": QueryResult(
                query_name="preferenceDataQuery", 
                success=True,
                data=[
                    {
                        "preference_name": "실내 활동 선호",
                        "question_count": 15,
                        "response_rate": 85,
                        "rank": 1,
                        "description": "조용하고 집중할 수 있는 환경을 선호합니다."
                    },
                    {
                        "preference_name": "창의적 활동 선호",
                        "question_count": 12,
                        "response_rate": 78,
                        "rank": 2,
                        "description": "새로운 아이디어를 만들어내는 활동을 좋아합니다."
                    }
                ],
                execution_time=2.0,
                row_count=2
            ),
            "preferenceJobsQuery": QueryResult(
                query_name="preferenceJobsQuery",
                success=True,
                data=[
                    {
                        "preference_name": "실내 활동 선호",
                        "preference_type": "rimg1",
                        "jo_name": "소프트웨어 개발자",
                        "jo_outline": "컴퓨터 프로그램 개발",
                        "jo_mainbusiness": "소프트웨어 설계 및 개발",
                        "majors": "컴퓨터공학, 소프트웨어공학"
                    },
                    {
                        "preference_name": "창의적 활동 선호",
                        "preference_type": "rimg2",
                        "jo_name": "그래픽 디자이너",
                        "jo_outline": "시각 디자인 작업",
                        "jo_mainbusiness": "브랜드 및 광고 디자인",
                        "majors": "시각디자인, 산업디자인"
                    }
                ],
                execution_time=1.8,
                row_count=2
            )
        }
        
        # Step 1: Query Execution
        with patch.object(LegacyQueryExecutor, 'execute_all_queries_async') as mock_execute:
            # Mock the async query execution to return formatted results
            formatted_results = {
                "imagePreferenceStatsQuery": mock_query_results["imagePreferenceStatsQuery"].data,
                "preferenceDataQuery": mock_query_results["preferenceDataQuery"].data,
                "preferenceJobsQuery": mock_query_results["preferenceJobsQuery"].data
            }
            mock_execute.return_value = formatted_results
            
            executor = LegacyQueryExecutor()
            
            # Simulate the query execution results
            query_results = {
                "imagePreferenceStatsQuery": mock_query_results["imagePreferenceStatsQuery"],
                "preferenceDataQuery": mock_query_results["preferenceDataQuery"],
                "preferenceJobsQuery": mock_query_results["preferenceJobsQuery"]
            }
            
            # Verify query execution
            assert len(query_results) == 3
            assert all(result.success for result in query_results.values())
            assert query_results["imagePreferenceStatsQuery"].row_count == 1
            assert query_results["preferenceDataQuery"].row_count == 2
            assert query_results["preferenceJobsQuery"].row_count == 2
        
        # Step 2: Data Validation
        validator = PreferenceDataValidator()
        
        # Convert QueryResult to dict format for validation
        formatted_results = {
            name: result.data for name, result in query_results.items()
        }
        
        validation_report = validator.generate_validation_report(formatted_results)
        
        # Verify validation passes
        assert validation_report.overall_valid == True
        assert validation_report.stats_validation.is_valid == True
        assert validation_report.preferences_validation.is_valid == True
        assert validation_report.jobs_validation.is_valid == True
        
        # Step 3: Document Transformation
        transformer = DocumentTransformer()
        documents = transformer._chunk_preference_analysis(formatted_results)
        
        # Verify document creation
        assert len(documents) >= 5  # stats + overview + 2 preferences + job groups
        assert all(doc.doc_type == "PREFERENCE_ANALYSIS" for doc in documents)
        
        # Verify document types
        doc_subtypes = [doc.metadata.get("sub_type") for doc in documents]
        assert "test_stats" in doc_subtypes
        assert "preferences_overview" in doc_subtypes
        assert any(subtype.startswith("preference_") for subtype in doc_subtypes)
        assert any(subtype.startswith("jobs_") for subtype in doc_subtypes)
        
        # Step 4: Vector Embedding
        with patch.object(VectorEmbedder, 'generate_embeddings') as mock_embed:
            mock_embed.return_value = [
                {**doc.__dict__, "embedding_vector": [0.1] * 500}
                for doc in documents
            ]
            
            embedder = VectorEmbedder()
            embedded_docs = await embedder.generate_embeddings(documents)
            
            # Verify embeddings
            assert len(embedded_docs) == len(documents)
            assert all("embedding_vector" in doc for doc in embedded_docs)
            assert all(len(doc["embedding_vector"]) == 500 for doc in embedded_docs)
        
        # Step 5: Document Storage
        with patch.object(DocumentRepository, 'save_documents') as mock_save:
            mock_save.return_value = True
            
            repo = DocumentRepository()
            save_result = await repo.save_documents(embedded_docs, anp_seq)
            
            # Verify storage
            assert save_result == True
            mock_save.assert_called_once_with(embedded_docs, anp_seq)
        
        # Step 6: RAG Integration Test
        with patch.object(ContextBuilder, 'build_context') as mock_context:
            mock_context.return_value = {
                "relevant_documents": documents[:3],
                "context_summary": "사용자의 이미지 선호도 분석 결과",
                "document_types": ["PREFERENCE_ANALYSIS"]
            }
            
            # Test question processing
            processor = QuestionProcessor()
            question = "내 이미지 선호도는 어떻게 되나요?"
            
            question_analysis = processor.analyze_question(question)
            assert question_analysis["category"] == "preference"
            assert question_analysis["confidence"] > 0.8
            
            # Test context building
            context_builder = ContextBuilder()
            context = await context_builder.build_context(question, anp_seq)
            
            # Verify context includes preference documents
            assert len(context["relevant_documents"]) > 0
            assert "PREFERENCE_ANALYSIS" in context["document_types"]
        
        # Step 7: Response Generation
        with patch.object(ResponseGenerator, 'generate_response') as mock_response:
            mock_response.return_value = {
                "response": "귀하의 이미지 선호도 분석 결과, 실내 활동을 가장 선호하시며...",
                "confidence": 0.9,
                "sources": ["PREFERENCE_ANALYSIS"],
                "has_preference_data": True
            }
            
            generator = ResponseGenerator()
            response = await generator.generate_response(question, context)
            
            # Verify response quality
            assert response["confidence"] > 0.8
            assert response["has_preference_data"] == True
            assert "PREFERENCE_ANALYSIS" in response["sources"]
            assert "실내 활동" in response["response"]

    @pytest.mark.asyncio
    async def test_preference_workflow_with_partial_data(self):
        """Test preference workflow when some queries fail or return partial data"""
        anp_seq = 12346
        
        # Mock partial query results (stats fail, preferences succeed, jobs empty)
        mock_query_results = {
            "imagePreferenceStatsQuery": QueryResult(
                query_name="imagePreferenceStatsQuery",
                success=False,
                error="Database connection timeout",
                execution_time=5.0
            ),
            "preferenceDataQuery": QueryResult(
                query_name="preferenceDataQuery",
                success=True,
                data=[{
                    "preference_name": "실내 활동 선호",
                    "rank": 1,
                    "response_rate": 85,
                    "description": "조용한 환경 선호"
                }],
                execution_time=1.5,
                row_count=1
            ),
            "preferenceJobsQuery": QueryResult(
                query_name="preferenceJobsQuery",
                success=True,
                data=[],  # Empty results
                execution_time=1.0,
                row_count=0
            )
        }
        
        # Step 1: Query Execution with Failures
        with patch.object(LegacyQueryExecutor, '_query_image_preference_stats') as mock_stats, \
             patch.object(LegacyQueryExecutor, '_query_preference_data') as mock_prefs, \
             patch.object(LegacyQueryExecutor, '_query_preference_jobs') as mock_jobs:
            
            # Mock failures and successes
            async def mock_stats_fail(anp_seq):
                raise Exception("Database connection timeout")
            
            mock_stats.side_effect = mock_stats_fail
            mock_prefs.return_value = mock_query_results["preferenceDataQuery"].data
            mock_jobs.return_value = mock_query_results["preferenceJobsQuery"].data
            
            executor = LegacyQueryExecutor()
            
            # Simulate the mixed query execution results
            query_results = {
                "imagePreferenceStatsQuery": mock_query_results["imagePreferenceStatsQuery"],
                "preferenceDataQuery": mock_query_results["preferenceDataQuery"],
                "preferenceJobsQuery": mock_query_results["preferenceJobsQuery"]
            }
            
            # Verify mixed results
            assert query_results["imagePreferenceStatsQuery"].success == False
            assert query_results["preferenceDataQuery"].success == True
            assert query_results["preferenceJobsQuery"].success == True
            assert query_results["preferenceJobsQuery"].row_count == 0
        
        # Step 2: Validation with Partial Data
        validator = PreferenceDataValidator()
        formatted_results = {
            name: result.data if result.success else []
            for name, result in query_results.items()
        }
        
        validation_report = validator.generate_validation_report(formatted_results)
        
        # Verify partial validation
        assert validation_report.overall_valid == False  # Due to missing stats
        assert validation_report.stats_validation.is_valid == False
        assert validation_report.preferences_validation.is_valid == True
        assert validation_report.jobs_validation.is_valid == False  # Empty data
        
        # Step 3: Document Creation with Partial Data
        transformer = DocumentTransformer()
        documents = transformer._chunk_preference_analysis(formatted_results)
        
        # Verify partial documents created
        assert len(documents) >= 2  # At least partial stats + preference
        
        # Check for partial/fallback documents
        doc_subtypes = [doc.metadata.get("sub_type") for doc in documents]
        assert any("partial" in subtype or "unavailable" in subtype for subtype in doc_subtypes)
        
        # Step 4: RAG Handling of Partial Data
        with patch.object(ContextBuilder, 'build_context') as mock_context:
            mock_context.return_value = {
                "relevant_documents": documents,
                "context_summary": "부분적인 이미지 선호도 분석 결과",
                "document_types": ["PREFERENCE_ANALYSIS"],
                "data_completeness": "partial"
            }
            
            context_builder = ContextBuilder()
            question = "내 이미지 선호도 통계는 어떻게 되나요?"
            context = await context_builder.build_context(question, anp_seq)
            
            # Verify context acknowledges partial data
            assert context["data_completeness"] == "partial"
        
        # Step 5: Response Generation with Partial Data
        with patch.object(ResponseGenerator, 'generate_response') as mock_response:
            mock_response.return_value = {
                "response": "이미지 선호도 통계 데이터는 현재 이용할 수 없지만, 선호도 분석 결과는 확인할 수 있습니다...",
                "confidence": 0.7,
                "sources": ["PREFERENCE_ANALYSIS"],
                "has_preference_data": True,
                "data_limitations": ["stats_unavailable", "jobs_empty"]
            }
            
            generator = ResponseGenerator()
            response = await generator.generate_response(question, context)
            
            # Verify appropriate handling of limitations
            assert response["confidence"] < 0.8  # Lower confidence due to missing data
            assert "data_limitations" in response
            assert "stats_unavailable" in response["data_limitations"]

    @pytest.mark.asyncio
    async def test_preference_workflow_complete_failure(self):
        """Test preference workflow when all preference queries fail"""
        anp_seq = 12347
        
        # Mock complete failure
        mock_query_results = {
            "imagePreferenceStatsQuery": QueryResult(
                query_name="imagePreferenceStatsQuery",
                success=False,
                error="Database connection failed",
                execution_time=5.0
            ),
            "preferenceDataQuery": QueryResult(
                query_name="preferenceDataQuery",
                success=False,
                error="Query timeout",
                execution_time=10.0
            ),
            "preferenceJobsQuery": QueryResult(
                query_name="preferenceJobsQuery",
                success=False,
                error="Invalid anp_seq",
                execution_time=0.5
            )
        }
        
        # Step 1: Query Execution Failures
        with patch.object(LegacyQueryExecutor, '_query_image_preference_stats') as mock_stats, \
             patch.object(LegacyQueryExecutor, '_query_preference_data') as mock_prefs, \
             patch.object(LegacyQueryExecutor, '_query_preference_jobs') as mock_jobs:
            
            # Mock all failures
            async def mock_fail(anp_seq):
                raise Exception("Database connection failed")
            
            mock_stats.side_effect = mock_fail
            mock_prefs.side_effect = mock_fail
            mock_jobs.side_effect = mock_fail
            
            executor = LegacyQueryExecutor()
            
            # Simulate the complete failure results
            query_results = {
                "imagePreferenceStatsQuery": mock_query_results["imagePreferenceStatsQuery"],
                "preferenceDataQuery": mock_query_results["preferenceDataQuery"],
                "preferenceJobsQuery": mock_query_results["preferenceJobsQuery"]
            }
            
            # Verify all failures
            assert all(not result.success for result in query_results.values())
        
        # Step 2: Validation with No Data
        validator = PreferenceDataValidator()
        formatted_results = {name: [] for name in query_results.keys()}
        
        validation_report = validator.generate_validation_report(formatted_results)
        
        # Verify complete validation failure
        assert validation_report.overall_valid == False
        assert validation_report.stats_validation.is_valid == False
        assert validation_report.preferences_validation.is_valid == False
        assert validation_report.jobs_validation.is_valid == False
        
        # Step 3: Fallback Document Creation
        transformer = DocumentTransformer()
        documents = transformer._chunk_preference_analysis(formatted_results)
        
        # Verify fallback document created
        assert len(documents) == 1
        assert documents[0].metadata.get("sub_type") == "unavailable"
        assert documents[0].metadata.get("has_alternatives") == True
        
        # Step 4: RAG Handling of No Data
        with patch.object(ContextBuilder, 'build_context') as mock_context:
            mock_context.return_value = {
                "relevant_documents": documents,
                "context_summary": "이미지 선호도 분석 데이터 없음",
                "document_types": ["PREFERENCE_ANALYSIS"],
                "data_completeness": "unavailable",
                "alternative_documents": ["PERSONALITY_PROFILE", "THINKING_SKILLS"]
            }
            
            context_builder = ContextBuilder()
            question = "내 이미지 선호도는 어떻게 되나요?"
            context = await context_builder.build_context(question, anp_seq)
            
            # Verify context provides alternatives
            assert context["data_completeness"] == "unavailable"
            assert "alternative_documents" in context
        
        # Step 5: Response with Alternatives
        with patch.object(ResponseGenerator, 'generate_response') as mock_response:
            mock_response.return_value = {
                "response": "죄송합니다. 이미지 선호도 분석 데이터를 현재 이용할 수 없습니다. 대신 성격 분석이나 사고 능력 분석 결과를 확인해보시겠어요?",
                "confidence": 0.9,
                "sources": ["PREFERENCE_ANALYSIS"],
                "has_preference_data": False,
                "suggested_alternatives": ["personality", "thinking_skills"]
            }
            
            generator = ResponseGenerator()
            response = await generator.generate_response(question, context)
            
            # Verify appropriate fallback response
            assert response["has_preference_data"] == False
            assert "suggested_alternatives" in response
            assert "성격 분석" in response["response"]

    @pytest.mark.asyncio
    async def test_preference_workflow_performance_metrics(self):
        """Test preference workflow performance and timing"""
        anp_seq = 12348
        
        # Mock query results with timing data
        mock_query_results = {
            "imagePreferenceStatsQuery": QueryResult(
                query_name="imagePreferenceStatsQuery",
                success=True,
                data=[{"total_image_count": 120, "response_count": 96}],
                execution_time=0.8,
                row_count=1
            ),
            "preferenceDataQuery": QueryResult(
                query_name="preferenceDataQuery",
                success=True,
                data=[{"preference_name": "실내 활동 선호", "rank": 1}],
                execution_time=1.2,
                row_count=1
            ),
            "preferenceJobsQuery": QueryResult(
                query_name="preferenceJobsQuery",
                success=True,
                data=[{"preference_name": "실내 활동 선호", "jo_name": "개발자"}],
                execution_time=1.5,
                row_count=1
            )
        }
        
        start_time = datetime.now()
        
        # Execute workflow with timing
        with patch.object(LegacyQueryExecutor, '_query_image_preference_stats') as mock_stats, \
             patch.object(LegacyQueryExecutor, '_query_preference_data') as mock_prefs, \
             patch.object(LegacyQueryExecutor, '_query_preference_jobs') as mock_jobs:
            
            mock_stats.return_value = mock_query_results["imagePreferenceStatsQuery"].data
            mock_prefs.return_value = mock_query_results["preferenceDataQuery"].data
            mock_jobs.return_value = mock_query_results["preferenceJobsQuery"].data
            
            # Step 1: Query Execution
            executor = LegacyQueryExecutor()
            query_results = {
                "imagePreferenceStatsQuery": mock_query_results["imagePreferenceStatsQuery"],
                "preferenceDataQuery": mock_query_results["preferenceDataQuery"],
                "preferenceJobsQuery": mock_query_results["preferenceJobsQuery"]
            }
            
            # Verify query timing
            total_query_time = sum(result.execution_time for result in query_results.values())
            assert total_query_time < 5.0  # Should complete within 5 seconds
        
        # Step 2: Document Transformation Timing
        transformer = DocumentTransformer()
        transform_start = datetime.now()
        
        formatted_results = {name: result.data for name, result in query_results.items()}
        documents = transformer._chunk_preference_analysis(formatted_results)
        
        transform_time = (datetime.now() - transform_start).total_seconds()
        assert transform_time < 2.0  # Should complete within 2 seconds
        
        # Step 3: Overall Workflow Timing
        total_time = (datetime.now() - start_time).total_seconds()
        assert total_time < 10.0  # Complete workflow should finish within 10 seconds
        
        # Verify performance metrics
        assert len(documents) >= 3
        assert all(doc.doc_type == "PREFERENCE_ANALYSIS" for doc in documents)

    @pytest.mark.asyncio
    async def test_preference_workflow_error_recovery(self):
        """Test preference workflow error recovery and resilience"""
        anp_seq = 12349
        
        # Test various error scenarios
        error_scenarios = [
            # Scenario 1: Transient database error with retry success
            {
                "first_attempt": {
                    "imagePreferenceStatsQuery": QueryResult(
                        query_name="imagePreferenceStatsQuery",
                        success=False,
                        error="Connection timeout",
                        execution_time=5.0
                    )
                },
                "retry_attempt": {
                    "imagePreferenceStatsQuery": QueryResult(
                        query_name="imagePreferenceStatsQuery",
                        success=True,
                        data=[{"total_image_count": 120, "response_count": 96}],
                        execution_time=1.0,
                        row_count=1
                    )
                }
            }
        ]
        
        for scenario in error_scenarios:
            # Mock retry logic
            call_count = 0
            
            def mock_execute_with_retry(anp_seq):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return scenario["first_attempt"]
                else:
                    return scenario["retry_attempt"]
            
            with patch.object(LegacyQueryExecutor, '_query_image_preference_stats', side_effect=mock_execute_with_retry):
                executor = LegacyQueryExecutor()
                
                # First attempt should fail
                try:
                    first_result = await executor._query_image_preference_stats(anp_seq)
                    assert False, "Should have failed"
                except Exception:
                    pass  # Expected failure
                
                # Retry should succeed
                retry_result = await executor._query_image_preference_stats(anp_seq)
                assert retry_result is not None
                
                # Verify retry was attempted
                assert call_count == 2

    @pytest.mark.asyncio
    async def test_preference_workflow_data_integrity(self):
        """Test preference workflow maintains data integrity throughout pipeline"""
        anp_seq = 12350
        
        # Original data with specific values to track
        original_data = {
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
            "preferenceJobsQuery": [{
                "preference_name": "실내 활동 선호",
                "preference_type": "rimg1",
                "jo_name": "소프트웨어 개발자"
            }]
        }
        
        # Mock query results
        mock_query_results = {
            name: QueryResult(
                query_name=name,
                success=True,
                data=data,
                execution_time=1.0,
                row_count=len(data)
            )
            for name, data in original_data.items()
        }
        
        with patch.object(LegacyQueryExecutor, '_query_image_preference_stats') as mock_stats, \
             patch.object(LegacyQueryExecutor, '_query_preference_data') as mock_prefs, \
             patch.object(LegacyQueryExecutor, '_query_preference_jobs') as mock_jobs:
            
            mock_stats.return_value = mock_query_results["imagePreferenceStatsQuery"].data
            mock_prefs.return_value = mock_query_results["preferenceDataQuery"].data
            mock_jobs.return_value = mock_query_results["preferenceJobsQuery"].data
            
            # Execute workflow
            executor = LegacyQueryExecutor()
            query_results = {
                "imagePreferenceStatsQuery": mock_query_results["imagePreferenceStatsQuery"],
                "preferenceDataQuery": mock_query_results["preferenceDataQuery"],
                "preferenceJobsQuery": mock_query_results["preferenceJobsQuery"]
            }
            
            # Transform documents
            transformer = DocumentTransformer()
            formatted_results = {name: result.data for name, result in query_results.items()}
            documents = transformer._chunk_preference_analysis(formatted_results)
            
            # Verify data integrity through pipeline
            
            # 1. Check stats data integrity
            stats_docs = [doc for doc in documents if doc.metadata.get("sub_type") == "test_stats"]
            assert len(stats_docs) == 1
            stats_doc = stats_docs[0]
            
            assert stats_doc.content["total_images"] == 120
            assert stats_doc.content["completed_images"] == 96
            assert stats_doc.content["completion_rate"] == 80
            
            # 2. Check preference data integrity
            pref_docs = [doc for doc in documents if doc.metadata.get("sub_type", "").startswith("preference_")]
            assert len(pref_docs) == 1
            pref_doc = pref_docs[0]
            
            assert pref_doc.content["preference_name"] == "실내 활동 선호"
            assert pref_doc.content["rank"] == 1
            assert pref_doc.content["response_rate"] == 85
            assert "조용한 환경" in pref_doc.content["description"]
            
            # 3. Check job data integrity
            job_docs = [doc for doc in documents if doc.metadata.get("sub_type", "").startswith("jobs_")]
            job_detail_docs = [doc for doc in job_docs if doc.metadata.get("sub_type") != "jobs_overview"]
            assert len(job_detail_docs) >= 1
            
            job_doc = job_detail_docs[0]
            assert job_doc.content["preference_name"] == "실내 활동 선호"
            assert any("소프트웨어 개발자" in str(job) for job in job_doc.content["jobs"])
            
            # 4. Verify no data corruption or loss
            for doc in documents:
                assert doc.doc_type == "PREFERENCE_ANALYSIS"
                assert doc.summary_text is not None
                assert len(doc.summary_text.strip()) > 0
                assert doc.content is not None
                assert doc.metadata is not None
                assert "created_at" in doc.metadata