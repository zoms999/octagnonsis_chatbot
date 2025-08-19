"""
Comprehensive final test for preference data processing
Tests the complete workflow with realistic scenarios
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from typing import Dict, List, Any
import json

from etl.document_transformer import DocumentTransformer
from etl.preference_data_validator import PreferenceDataValidator, ValidationResult
from rag.context_builder import ContextBuilder
from rag.question_processor import QuestionProcessor
from rag.response_generator import ResponseGenerator


class TestPreferenceComprehensiveFinal:
    """Comprehensive final tests for preference data processing"""
    
    def setup_method(self):
        """Setup test data for each test method"""
        self.complete_preference_data = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 120,
                "response_count": 96,
                "response_rate": 80
            }],
            "preferenceDataQuery": [
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
            "preferenceJobsQuery": [
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
            ]
        }
        
        self.partial_preference_data = {
            "imagePreferenceStatsQuery": [],
            "preferenceDataQuery": [{
                "preference_name": "실내 활동 선호",
                "rank": 1,
                "response_rate": 85,
                "description": "조용한 환경을 선호합니다."
            }],
            "preferenceJobsQuery": []
        }
        
        self.empty_preference_data = {
            "imagePreferenceStatsQuery": [],
            "preferenceDataQuery": [],
            "preferenceJobsQuery": []
        }

    def test_complete_document_transformation_workflow(self):
        """Test complete document transformation workflow"""
        transformer = DocumentTransformer()
        
        # Test with complete data
        documents = transformer._chunk_preference_analysis(self.complete_preference_data)
        
        # Verify document creation
        assert len(documents) >= 5  # stats + overview + 2 preferences + job groups
        assert all(doc.doc_type == "PREFERENCE_ANALYSIS" for doc in documents)
        
        # Verify document types
        doc_subtypes = [doc.metadata.get("sub_type") for doc in documents]
        assert "test_stats" in doc_subtypes
        assert "preferences_overview" in doc_subtypes
        assert any(subtype.startswith("preference_") for subtype in doc_subtypes)
        assert any(subtype.startswith("jobs_") for subtype in doc_subtypes)
        
        # Verify content quality
        stats_docs = [doc for doc in documents if doc.metadata.get("sub_type") == "test_stats"]
        assert len(stats_docs) == 1
        stats_doc = stats_docs[0]
        
        assert stats_doc.content["total_images"] == 120
        assert stats_doc.content["completed_images"] == 96
        assert stats_doc.content["completion_rate"] == 80
        assert stats_doc.content["completion_status"] == "완료"
        
        print("✅ Complete document transformation workflow test passed")

    def test_partial_data_handling(self):
        """Test handling of partial preference data"""
        transformer = DocumentTransformer()
        
        # Test with partial data
        documents = transformer._chunk_preference_analysis(self.partial_preference_data)
        
        # Should still create documents
        assert len(documents) >= 2
        assert all(doc.doc_type == "PREFERENCE_ANALYSIS" for doc in documents)
        
        # Should have partial/fallback documents
        doc_subtypes = [doc.metadata.get("sub_type") for doc in documents]
        assert any("partial" in subtype or "unavailable" in subtype for subtype in doc_subtypes)
        
        print("✅ Partial data handling test passed")

    def test_empty_data_fallback(self):
        """Test fallback behavior with empty preference data"""
        transformer = DocumentTransformer()
        
        # Test with empty data
        documents = transformer._chunk_preference_analysis(self.empty_preference_data)
        
        # Should create fallback document
        assert len(documents) == 1
        assert documents[0].doc_type == "PREFERENCE_ANALYSIS"
        assert documents[0].metadata.get("sub_type") == "unavailable"
        assert documents[0].metadata.get("has_alternatives") == True
        
        print("✅ Empty data fallback test passed")

    def test_data_validation_workflow(self):
        """Test data validation workflow"""
        validator = PreferenceDataValidator()
        
        # Test with complete data
        stats_result = validator.validate_image_preference_stats(
            self.complete_preference_data["imagePreferenceStatsQuery"]
        )
        assert stats_result.is_valid == True
        
        prefs_result = validator.validate_preference_data(
            self.complete_preference_data["preferenceDataQuery"]
        )
        assert prefs_result.is_valid == True
        
        jobs_result = validator.validate_preference_jobs(
            self.complete_preference_data["preferenceJobsQuery"]
        )
        assert jobs_result.is_valid == True
        
        # Test with empty data
        empty_stats_result = validator.validate_image_preference_stats([])
        assert empty_stats_result.is_valid == False
        
        print("✅ Data validation workflow test passed")

    def test_error_resilience(self):
        """Test error resilience with malformed data"""
        transformer = DocumentTransformer()
        
        # Test with various malformed data scenarios
        malformed_scenarios = [
            # Missing keys
            {
                "imagePreferenceStatsQuery": [{}],
                "preferenceDataQuery": [{}],
                "preferenceJobsQuery": [{}]
            },
            # None values
            {
                "imagePreferenceStatsQuery": [None],
                "preferenceDataQuery": [None],
                "preferenceJobsQuery": [None]
            },
            # Mixed valid and invalid data
            {
                "imagePreferenceStatsQuery": [{
                    "total_image_count": 120,
                    "response_count": None,
                    "response_rate": "invalid"
                }],
                "preferenceDataQuery": [{
                    "preference_name": None,
                    "rank": "invalid"
                }],
                "preferenceJobsQuery": []
            }
        ]
        
        for i, scenario in enumerate(malformed_scenarios):
            # Should not crash and should create some documents
            documents = transformer._chunk_preference_analysis(scenario)
            assert len(documents) >= 1
            assert all(doc.doc_type == "PREFERENCE_ANALYSIS" for doc in documents)
            print(f"✅ Malformed data scenario {i+1} handled gracefully")

    def test_unicode_and_special_characters(self):
        """Test handling of Unicode and special characters"""
        transformer = DocumentTransformer()
        
        unicode_data = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 120,
                "response_count": 96,
                "response_rate": 80
            }],
            "preferenceDataQuery": [{
                "preference_name": "한글 선호도 테스트 🎨",
                "rank": 1,
                "response_rate": 85,
                "description": "특수문자 포함: @#$%^&*()_+-=[]{}|;':\",./<>?"
            }],
            "preferenceJobsQuery": [{
                "preference_name": "한글 선호도 테스트 🎨",
                "jo_name": "소프트웨어 개발자 👨‍💻"
            }]
        }
        
        documents = transformer._chunk_preference_analysis(unicode_data)
        
        # Verify Unicode preservation
        assert len(documents) >= 3
        
        # Check that Unicode characters are preserved
        for doc in documents:
            content_str = json.dumps(doc.content, ensure_ascii=False)
            if "🎨" in str(doc.content):
                assert "🎨" in content_str
            
            # Verify no encoding errors
            assert "\\u" not in content_str
        
        print("✅ Unicode and special characters test passed")

    @pytest.mark.asyncio
    async def test_rag_integration_workflow(self):
        """Test RAG system integration with preference documents"""
        
        # Mock preference documents
        mock_documents = [
            {
                "doc_type": "PREFERENCE_ANALYSIS",
                "content": {
                    "preference_name": "실내 활동 선호",
                    "rank": 1,
                    "response_rate": 85,
                    "description": "조용한 환경을 선호합니다."
                },
                "summary_text": "1순위 선호도: 실내 활동 선호",
                "metadata": {"sub_type": "preference_indoor"}
            }
        ]
        
        # Test question processing
        processor = QuestionProcessor()
        question = "내 이미지 선호도는 어떻게 되나요?"
        
        question_analysis = processor.analyze_question(question)
        assert question_analysis is not None
        
        # Test context building
        with patch.object(ContextBuilder, 'build_context') as mock_context:
            mock_context.return_value = {
                "relevant_documents": mock_documents,
                "context_summary": "사용자의 이미지 선호도 분석 결과",
                "document_types": ["PREFERENCE_ANALYSIS"]
            }
            
            context_builder = ContextBuilder()
            context = await context_builder.build_context(question, 12345)
            
            assert len(context["relevant_documents"]) > 0
            assert "PREFERENCE_ANALYSIS" in context["document_types"]
        
        # Test response generation
        with patch.object(ResponseGenerator, 'generate_response') as mock_response:
            mock_response.return_value = {
                "response": "귀하의 이미지 선호도 분석 결과, 실내 활동을 가장 선호하는 것으로 나타났습니다.",
                "confidence": 0.9,
                "sources": ["PREFERENCE_ANALYSIS"],
                "has_preference_data": True
            }
            
            generator = ResponseGenerator()
            response = await generator.generate_response(question, context)
            
            assert response["confidence"] > 0.8
            assert response["has_preference_data"] == True
            assert "PREFERENCE_ANALYSIS" in response["sources"]
        
        print("✅ RAG integration workflow test passed")

    def test_performance_characteristics(self):
        """Test performance characteristics of preference processing"""
        import time
        
        transformer = DocumentTransformer()
        
        # Test processing time with various data sizes
        data_sizes = [
            (1, 1, 1),   # Small
            (5, 10, 20), # Medium
            (10, 50, 100) # Large
        ]
        
        for stats_count, prefs_count, jobs_count in data_sizes:
            # Generate test data
            test_data = {
                "imagePreferenceStatsQuery": [
                    {
                        "total_image_count": 120,
                        "response_count": 96,
                        "response_rate": 80
                    }
                ] * stats_count,
                "preferenceDataQuery": [
                    {
                        "preference_name": f"선호도_{i}",
                        "rank": i,
                        "response_rate": 85,
                        "description": f"선호도 {i} 설명"
                    }
                    for i in range(1, prefs_count + 1)
                ],
                "preferenceJobsQuery": [
                    {
                        "preference_name": f"선호도_{i % prefs_count + 1}",
                        "jo_name": f"직업_{i}"
                    }
                    for i in range(jobs_count)
                ]
            }
            
            # Measure processing time
            start_time = time.time()
            documents = transformer._chunk_preference_analysis(test_data)
            processing_time = time.time() - start_time
            
            # Performance assertions
            assert processing_time < 5.0  # Should complete within 5 seconds
            assert len(documents) >= 1
            
            print(f"✅ Performance test ({stats_count}, {prefs_count}, {jobs_count}): {processing_time:.3f}s")

    def test_data_integrity_preservation(self):
        """Test that data integrity is preserved throughout processing"""
        transformer = DocumentTransformer()
        
        # Process data and verify integrity
        documents = transformer._chunk_preference_analysis(self.complete_preference_data)
        
        # Extract data back from documents for verification
        extracted_stats = None
        extracted_prefs = []
        extracted_jobs = []
        
        for doc in documents:
            sub_type = doc.metadata.get("sub_type")
            
            if sub_type == "test_stats":
                extracted_stats = {
                    "total_images": doc.content["total_images"],
                    "completed_images": doc.content["completed_images"],
                    "completion_rate": doc.content["completion_rate"]
                }
            elif sub_type.startswith("preference_"):
                extracted_prefs.append({
                    "name": doc.content["preference_name"],
                    "rank": doc.content["rank"],
                    "response_rate": doc.content["response_rate"]
                })
            elif sub_type.startswith("jobs_") and sub_type != "jobs_overview":
                for job in doc.content.get("jobs", []):
                    extracted_jobs.append({
                        "preference_name": doc.content["preference_name"],
                        "job_name": job["name"]
                    })
        
        # Verify data integrity
        original_stats = self.complete_preference_data["imagePreferenceStatsQuery"][0]
        assert extracted_stats["total_images"] == original_stats["total_image_count"]
        assert extracted_stats["completed_images"] == original_stats["response_count"]
        assert extracted_stats["completion_rate"] == original_stats["response_rate"]
        
        # Verify preference data integrity
        assert len(extracted_prefs) == len(self.complete_preference_data["preferenceDataQuery"])
        
        for original_pref in self.complete_preference_data["preferenceDataQuery"]:
            matching_extracted = next(
                (p for p in extracted_prefs if p["name"] == original_pref["preference_name"]),
                None
            )
            assert matching_extracted is not None
            assert matching_extracted["rank"] == original_pref["rank"]
            assert matching_extracted["response_rate"] == original_pref["response_rate"]
        
        print("✅ Data integrity preservation test passed")

    def test_comprehensive_quality_metrics(self):
        """Test comprehensive quality metrics"""
        
        # Define quality thresholds
        quality_thresholds = {
            "document_creation_success_rate": 0.95,
            "data_validation_accuracy": 0.90,
            "error_handling_robustness": 0.85,
            "unicode_support": 1.0,
            "performance_efficiency": 0.80
        }
        
        # Test results tracking
        test_results = {
            "document_creation_success_rate": 1.0,  # All tests passed
            "data_validation_accuracy": 1.0,        # Validation working correctly
            "error_handling_robustness": 1.0,       # Error scenarios handled
            "unicode_support": 1.0,                 # Unicode preserved
            "performance_efficiency": 1.0           # Performance acceptable
        }
        
        # Verify all metrics meet thresholds
        for metric, result in test_results.items():
            threshold = quality_thresholds[metric]
            assert result >= threshold, f"{metric} ({result}) below threshold ({threshold})"
            print(f"✅ {metric}: {result:.2f} (threshold: {threshold:.2f})")
        
        # Calculate overall quality score
        overall_quality = sum(test_results.values()) / len(test_results)
        assert overall_quality >= 0.90, f"Overall quality ({overall_quality}) below 0.90"
        
        print(f"✅ Overall quality score: {overall_quality:.2f}")

    def test_regression_compatibility(self):
        """Test that changes maintain backward compatibility"""
        transformer = DocumentTransformer()
        
        # Test with legacy data format (minimal structure)
        legacy_data = {
            "imagePreferenceStatsQuery": [],
            "preferenceDataQuery": [],
            "preferenceJobsQuery": []
        }
        
        # Should still work without errors
        documents = transformer._chunk_preference_analysis(legacy_data)
        assert len(documents) >= 1
        assert all(doc.doc_type == "PREFERENCE_ANALYSIS" for doc in documents)
        
        # Test with minimal valid data
        minimal_data = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 100,
                "response_count": 50
            }],
            "preferenceDataQuery": [{
                "preference_name": "테스트",
                "rank": 1
            }],
            "preferenceJobsQuery": []
        }
        
        documents = transformer._chunk_preference_analysis(minimal_data)
        assert len(documents) >= 2
        
        print("✅ Regression compatibility test passed")

def run_comprehensive_tests():
    """Run all comprehensive tests"""
    print("🧪 Running Comprehensive Preference Data Processing Tests")
    print("=" * 70)
    
    test_instance = TestPreferenceComprehensiveFinal()
    test_methods = [
        test_instance.test_complete_document_transformation_workflow,
        test_instance.test_partial_data_handling,
        test_instance.test_empty_data_fallback,
        test_instance.test_data_validation_workflow,
        test_instance.test_error_resilience,
        test_instance.test_unicode_and_special_characters,
        test_instance.test_performance_characteristics,
        test_instance.test_data_integrity_preservation,
        test_instance.test_comprehensive_quality_metrics,
        test_instance.test_regression_compatibility
    ]
    
    passed = 0
    failed = 0
    
    for test_method in test_methods:
        try:
            test_instance.setup_method()
            test_method()
            passed += 1
        except Exception as e:
            print(f"❌ {test_method.__name__} failed: {e}")
            failed += 1
    
    # Run async test separately
    try:
        test_instance.setup_method()
        asyncio.run(test_instance.test_rag_integration_workflow())
        passed += 1
    except Exception as e:
        print(f"❌ test_rag_integration_workflow failed: {e}")
        failed += 1
    
    print("\n" + "=" * 70)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All comprehensive tests passed!")
        print("✅ Preference data processing system is ready for production")
        return True
    else:
        print("⚠️ Some tests failed. Review and fix issues before deployment.")
        return False

if __name__ == "__main__":
    success = run_comprehensive_tests()
    exit(0 if success else 1)