"""
Integration tests for enhanced preference document creation
Tests document transformer integration with various preference data scenarios
"""

import pytest
from unittest.mock import patch, MagicMock
from etl.document_transformer import DocumentTransformer
from database.models import DocumentType


class TestPreferenceDocumentIntegration:
    """Integration tests for preference document creation"""
    
    def test_complete_preference_document_creation(self):
        """Test document creation with complete preference data"""
        transformer = DocumentTransformer()
        
        # Mock query results with complete preference data
        query_results = {
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
                }
            ]
        }
        
        # Test document creation
        documents = transformer._chunk_preference_analysis(query_results)
        
        # Verify preference documents were created
        assert len(documents) >= 4  # stats + overview + 2 preferences + 1 job group
        
        # Verify document types
        doc_subtypes = [doc.metadata.get("sub_type") for doc in documents]
        assert "test_stats" in doc_subtypes
        assert "preferences_overview" in doc_subtypes
        assert any(subtype.startswith("preference_") for subtype in doc_subtypes)
        assert any(subtype.startswith("jobs_") for subtype in doc_subtypes)
        
        # Verify all documents have PREFERENCE_ANALYSIS type
        for doc in documents:
            assert doc.doc_type == "PREFERENCE_ANALYSIS"

    def test_partial_preference_document_creation(self):
        """Test document creation with partial preference data"""
        transformer = DocumentTransformer()
        
        # Mock query results with only preference data (no stats or jobs)
        query_results = {
            "imagePreferenceStatsQuery": [],
            "preferenceDataQuery": [
                {
                    "preference_name": "실내 활동 선호",
                    "question_count": 15,
                    "response_rate": 85,
                    "rank": 1,
                    "description": "조용하고 집중할 수 있는 환경을 선호합니다."
                }
            ],
            "preferenceJobsQuery": []
        }
        
        # Test document creation
        documents = transformer._chunk_preference_analysis(query_results)
        
        # Verify preference documents were created with partial data handling
        assert len(documents) >= 2  # partial stats + overview + preference
        
        # Verify partial document was created (enhanced version uses "partial_available")
        partial_docs = [doc for doc in documents 
                       if doc.metadata.get("sub_type") in ["partial_stats", "partial_available"]]
        assert len(partial_docs) >= 1
        
        # Verify preference documents were created
        pref_docs = [doc for doc in documents if doc.metadata.get("sub_type", "").startswith("preference_")]
        assert len(pref_docs) == 1

    def test_no_preference_data_fallback(self):
        """Test fallback document creation when no preference data is available"""
        transformer = DocumentTransformer()
        
        # Mock query results with no preference data
        query_results = {
            "imagePreferenceStatsQuery": [],
            "preferenceDataQuery": [],
            "preferenceJobsQuery": []
        }
        
        # Test document creation
        documents = transformer._chunk_preference_analysis(query_results)
        
        # Verify fallback document was created
        assert len(documents) == 1
        
        # Verify it's the fallback document
        fallback_doc = documents[0]
        assert fallback_doc.metadata.get("sub_type") == "unavailable"
        assert fallback_doc.metadata.get("has_alternatives") == True
        assert "다른 분석 결과 이용 가능" in fallback_doc.summary_text

    def test_preference_document_content_quality(self):
        """Test that preference documents have high-quality, informative content"""
        transformer = DocumentTransformer()
        
        query_results = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 120,
                "response_count": 48,  # Low response rate
                "response_rate": 40
            }],
            "preferenceDataQuery": [
                {
                    "preference_name": "실내 활동 선호",
                    "question_count": 15,
                    "response_rate": 85,
                    "rank": 1,
                    "description": "조용하고 집중할 수 있는 환경을 선호합니다."
                }
            ],
            "preferenceJobsQuery": []
        }
        
        # Test document creation
        documents = transformer._chunk_preference_analysis(query_results)
        
        # Verify stats document has quality interpretation
        stats_docs = [doc for doc in documents if doc.metadata.get("sub_type") == "test_stats"]
        assert len(stats_docs) == 1
        stats_doc = stats_docs[0]
        
        # Check low response rate handling
        assert stats_doc.content["completion_status"] == "미완료"
        assert "정확도는 제한적" in stats_doc.content["interpretation"]
        assert stats_doc.metadata["completion_level"] == "low"
        
        # Verify preference document has analysis
        pref_docs = [doc for doc in documents 
                    if doc.metadata.get("sub_type", "").startswith("preference_")]
        assert len(pref_docs) == 1
        pref_doc = pref_docs[0]
        
        # Check preference analysis content
        assert "analysis" in pref_doc.content
        assert "preference_strength" in pref_doc.content
        assert pref_doc.content["preference_strength"] == "강함"  # Rank 1
        assert "가장 강한 선호" in pref_doc.content["analysis"]

    def test_document_transformer_integration(self):
        """Test document transformer integration with various preference scenarios"""
        transformer = DocumentTransformer()
        
        # Test scenario with mixed data quality
        query_results = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 120,
                "response_count": 96,
                "response_rate": 80
            }],
            "preferenceDataQuery": [
                {
                    "preference_name": "실내 활동 선호",
                    "rank": 1,
                    "response_rate": 85,
                    "description": "조용한 환경 선호"
                },
                {
                    "preference_name": "",  # Empty name - should be filtered
                    "rank": 2,
                    "response_rate": 70
                },
                {
                    "preference_name": "창의적 활동 선호",
                    "rank": 3,
                    "response_rate": 65,
                    "description": "창의적 사고 선호"
                }
            ],
            "preferenceJobsQuery": [
                {
                    "preference_name": "실내 활동 선호",
                    "preference_type": "rimg1",
                    "jo_name": "소프트웨어 개발자"
                },
                {
                    "preference_name": None,  # Missing name - should get default
                    "preference_type": "rimg2",
                    "jo_name": "데이터 분석가"
                }
            ]
        }
        
        documents = transformer._chunk_preference_analysis(query_results)
        
        # Verify robust handling of mixed data quality
        assert len(documents) >= 4  # stats + overview + valid preferences + job groups
        
        # Verify only valid preferences were processed
        pref_docs = [doc for doc in documents if doc.metadata.get("sub_type", "").startswith("preference_")]
        assert len(pref_docs) == 2  # Only non-empty preference names
        
        # Verify job grouping handled missing names (enhanced version creates overview + detail docs)
        job_docs = [doc for doc in documents if doc.metadata.get("sub_type", "").startswith("jobs_")]
        assert len(job_docs) >= 2  # At least overview + detail documents
        
        # Check that default name was used for missing preference name (check detail docs only)
        job_detail_docs = [doc for doc in job_docs if doc.metadata.get("sub_type") != "jobs_overview"]
        job_pref_names = [doc.content.get("preference_name", "") for doc in job_detail_docs]
        assert "실내 활동 선호" in job_pref_names
        assert any("선호도 rimg2" in name for name in job_pref_names)

    @patch('etl.document_transformer.datetime')
    def test_full_document_transformation_with_preferences(self, mock_datetime):
        """Test full document transformation including preference documents"""
        mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"
        
        transformer = DocumentTransformer()
        
        # Complete query results including preference data
        query_results = {
            # Minimal data for other document types
            "personalInfoQuery": [{
                "user_name": "테스트사용자",
                "age": 25,
                "gender": "남성"
            }],
            "tendencyQuery": [{
                "Tnd1": "분석형",
                "Tnd2": "창의형"
            }],
            # Preference data
            "imagePreferenceStatsQuery": [{
                "total_image_count": 120,
                "response_count": 96,
                "response_rate": 80
            }],
            "preferenceDataQuery": [
                {
                    "preference_name": "실내 활동 선호",
                    "rank": 1,
                    "response_rate": 85,
                    "description": "조용한 환경 선호"
                }
            ],
            "preferenceJobsQuery": [
                {
                    "preference_name": "실내 활동 선호",
                    "preference_type": "rimg1",
                    "jo_name": "소프트웨어 개발자"
                }
            ]
        }
        
        # Test full transformation
        all_documents = transformer._chunk_preference_analysis(query_results)
        
        # Verify preference documents were created
        assert len(all_documents) >= 3  # stats + overview + preference + job
        
        # Verify all documents have consistent metadata
        for doc in all_documents:
            assert doc.doc_type == "PREFERENCE_ANALYSIS"
            assert "created_at" in doc.metadata
            assert "sub_type" in doc.metadata
            assert "completion_level" in doc.metadata
            assert doc.metadata["created_at"] == "2024-01-01T12:00:00"

    def test_preference_document_searchability(self):
        """Test that preference documents are optimized for search and retrieval"""
        transformer = DocumentTransformer()
        
        query_results = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 120,
                "response_count": 96,
                "response_rate": 80
            }],
            "preferenceDataQuery": [
                {
                    "preference_name": "실내 활동 선호",
                    "rank": 1,
                    "response_rate": 85,
                    "description": "조용하고 집중할 수 있는 환경을 선호합니다."
                }
            ],
            "preferenceJobsQuery": []
        }
        
        documents = transformer._chunk_preference_analysis(query_results)
        
        # Verify documents have meaningful summary text for search
        for doc in documents:
            assert doc.summary_text is not None
            assert len(doc.summary_text.strip()) > 0
            
            # Verify Korean content is properly handled
            if doc.metadata.get("sub_type") == "test_stats":
                assert "이미지 선호도 검사" in doc.summary_text
                assert "80%" in doc.summary_text
            elif doc.metadata.get("sub_type", "").startswith("preference_"):
                assert "실내 활동 선호" in doc.summary_text
                assert "1순위" in doc.summary_text

    def test_preference_document_error_resilience(self):
        """Test that preference document creation is resilient to data errors"""
        transformer = DocumentTransformer()
        
        # Test with various error conditions
        error_scenarios = [
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
                    "response_count": None,  # Invalid
                    "response_rate": 80
                }],
                "preferenceDataQuery": [
                    {"preference_name": "실내 활동 선호", "rank": 1},  # Valid
                    {"preference_name": None, "rank": None}  # Invalid
                ],
                "preferenceJobsQuery": []
            }
        ]
        
        for scenario in error_scenarios:
            # Should not crash and should create some documents
            documents = transformer._chunk_preference_analysis(scenario)
            assert len(documents) >= 1  # At least fallback document
            
            # All documents should have valid structure
            for doc in documents:
                assert doc.doc_type == "PREFERENCE_ANALYSIS"
                assert doc.summary_text is not None
                assert doc.content is not None
                assert doc.metadata is not None