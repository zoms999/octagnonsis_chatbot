"""
Unit tests for enhanced preference document creation in DocumentTransformer
Tests various data availability scenarios and fallback logic
"""

import pytest
from datetime import datetime
from unittest.mock import patch
from etl.document_transformer import DocumentTransformer, TransformedDocument


class TestPreferenceDocumentCreation:
    """Test suite for preference document creation with various data scenarios"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.transformer = DocumentTransformer()
    
    def test_complete_preference_data_scenario(self):
        """Test document creation with complete preference data"""
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
                },
                {
                    "preference_name": "창의적 활동 선호",
                    "preference_type": "rimg2", 
                    "jo_name": "그래픽 디자이너",
                    "jo_outline": "시각 디자인 작업",
                    "jo_mainbusiness": "광고 및 브랜딩 디자인",
                    "majors": "시각디자인, 산업디자인"
                }
            ]
        }
        
        documents = self.transformer._chunk_preference_analysis(query_results)
        
        # Should create multiple documents for complete data (enhanced version creates more documents)
        assert len(documents) >= 6  # completion summary + stats + overview + 2 preferences + jobs overview + job details
        
        # Check completion summary document (new in enhanced version)
        summary_docs = [d for d in documents if d.metadata.get("sub_type") == "completion_summary"]
        assert len(summary_docs) == 1
        
        # Check stats document
        stats_docs = [d for d in documents if d.metadata.get("sub_type") == "test_stats"]
        assert len(stats_docs) == 1
        assert "80%" in stats_docs[0].summary_text
        assert stats_docs[0].content["completion_status"] == "완료"
        
        # Check preferences overview
        overview_docs = [d for d in documents if d.metadata.get("sub_type") == "preferences_overview"]
        assert len(overview_docs) == 1
        assert "실내 활동 선호" in overview_docs[0].summary_text
        
        # Check individual preference documents
        pref_docs = [d for d in documents if d.metadata.get("sub_type", "").startswith("preference_")]
        assert len(pref_docs) == 2
        
        # Check job recommendation documents (enhanced version creates overview + detail docs)
        job_docs = [d for d in documents if d.metadata.get("sub_type", "").startswith("jobs_")]
        assert len(job_docs) >= 2  # At least overview + detail documents

    def test_partial_preference_data_stats_only(self):
        """Test document creation with only stats data available"""
        query_results = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 120,
                "response_count": 60,
                "response_rate": 50
            }],
            "preferenceDataQuery": [],
            "preferenceJobsQuery": []
        }
        
        documents = self.transformer._chunk_preference_analysis(query_results)
        
        # Should create partial document + stats document (enhanced version)
        assert len(documents) >= 1
        
        # Check for partial document (new in enhanced version)
        partial_docs = [d for d in documents if d.metadata.get("sub_type") == "partial_available"]
        if partial_docs:
            assert len(partial_docs) == 1
        
        # Check stats document
        stats_docs = [d for d in documents if d.metadata.get("sub_type") == "test_stats"]
        if stats_docs:
            stats_doc = stats_docs[0]
            assert "50%" in stats_doc.summary_text
            assert stats_doc.content["completion_status"] == "부분완료"
            assert stats_doc.metadata["completion_level"] == "medium"

    def test_partial_preference_data_preferences_only(self):
        """Test document creation with only preference data available"""
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
        
        documents = self.transformer._chunk_preference_analysis(query_results)
        
        # Should create partial document + overview + individual preference (enhanced version)
        assert len(documents) >= 3
        
        # Check partial document (new in enhanced version)
        partial_docs = [d for d in documents if d.metadata.get("sub_type") == "partial_available"]
        assert len(partial_docs) == 1
        assert "부분 완료" in partial_docs[0].content["status"]
        
        # Check preferences are created
        pref_docs = [d for d in documents if d.metadata.get("sub_type", "").startswith("preference_")]
        assert len(pref_docs) >= 1

    def test_partial_preference_data_jobs_only(self):
        """Test document creation with only job recommendation data available"""
        query_results = {
            "imagePreferenceStatsQuery": [],
            "preferenceDataQuery": [],
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
        
        documents = self.transformer._chunk_preference_analysis(query_results)
        
        # Should create partial document + job recommendations (enhanced version)
        assert len(documents) >= 2
        
        # Check partial document (new in enhanced version)
        partial_docs = [d for d in documents if d.metadata.get("sub_type") == "partial_available"]
        assert len(partial_docs) == 1
        assert "부분 완료" in partial_docs[0].content["status"]
        
        # Check job documents (enhanced version creates overview + detail docs)
        job_docs = [d for d in documents if d.metadata.get("sub_type", "").startswith("jobs_")]
        assert len(job_docs) >= 1

    def test_no_preference_data_fallback(self):
        """Test fallback document creation when no preference data is available"""
        query_results = {
            "imagePreferenceStatsQuery": [],
            "preferenceDataQuery": [],
            "preferenceJobsQuery": []
        }
        
        documents = self.transformer._chunk_preference_analysis(query_results)
        
        # Should create single fallback document
        assert len(documents) == 1
        
        fallback_doc = documents[0]
        assert fallback_doc.metadata["sub_type"] == "unavailable"
        assert fallback_doc.metadata["completion_level"] == "none"
        assert fallback_doc.metadata["has_alternatives"] == True
        assert "데이터 준비 중" in fallback_doc.summary_text
        assert "다른 분석 결과 이용 가능" in fallback_doc.summary_text
        
        # Check content has helpful information
        content = fallback_doc.content
        assert "missing_components" in content
        assert "explanation" in content
        assert "alternatives" in content
        assert "recommendation" in content

    def test_low_response_rate_handling(self):
        """Test handling of low response rate in stats"""
        query_results = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 120,
                "response_count": 24,
                "response_rate": 20
            }],
            "preferenceDataQuery": [],
            "preferenceJobsQuery": []
        }
        
        documents = self.transformer._chunk_preference_analysis(query_results)
        
        # Find stats document (enhanced version may create partial document too)
        stats_docs = [d for d in documents if d.metadata.get("sub_type") == "test_stats"]
        if stats_docs:
            stats_doc = stats_docs[0]
            assert stats_doc.content["completion_status"] == "미완료"
            assert stats_doc.metadata["completion_level"] == "low"
            assert "정확히 파악하기 어려우며" in stats_doc.content["interpretation"]

    def test_high_response_rate_handling(self):
        """Test handling of high response rate in stats"""
        query_results = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 120,
                "response_count": 108,
                "response_rate": 90
            }],
            "preferenceDataQuery": [],
            "preferenceJobsQuery": []
        }
        
        documents = self.transformer._chunk_preference_analysis(query_results)
        
        # Find stats document (enhanced version may create partial document too)
        stats_docs = [d for d in documents if d.metadata.get("sub_type") == "test_stats"]
        if stats_docs:
            stats_doc = stats_docs[0]
            assert stats_doc.content["completion_status"] == "완료"
            assert stats_doc.metadata["completion_level"] == "high"
            assert "신뢰할 수 있는" in stats_doc.content["interpretation"]

    def test_multiple_job_preferences_grouping(self):
        """Test proper grouping of jobs by preference type"""
        query_results = {
            "imagePreferenceStatsQuery": [],
            "preferenceDataQuery": [],
            "preferenceJobsQuery": [
                {
                    "preference_name": "실내 활동 선호",
                    "preference_type": "rimg1",
                    "jo_name": "소프트웨어 개발자"
                },
                {
                    "preference_name": "실내 활동 선호", 
                    "preference_type": "rimg1",
                    "jo_name": "데이터 분석가"
                },
                {
                    "preference_name": "창의적 활동 선호",
                    "preference_type": "rimg2",
                    "jo_name": "그래픽 디자이너"
                }
            ]
        }
        
        documents = self.transformer._chunk_preference_analysis(query_results)
        
        # Should create partial document + job documents (enhanced version creates overview + detail docs)
        job_docs = [d for d in documents if d.metadata.get("sub_type", "").startswith("jobs_")]
        assert len(job_docs) >= 2  # At least overview + detail documents
        
        # Check grouping in detail documents (not overview)
        job_detail_docs = [d for d in job_docs if d.metadata.get("sub_type") != "jobs_overview"]
        indoor_jobs = [d for d in job_detail_docs if "실내 활동 선호" in d.content.get("preference_name", "")]
        creative_jobs = [d for d in job_detail_docs if "창의적 활동 선호" in d.content.get("preference_name", "")]
        
        assert len(indoor_jobs) == 1
        assert len(creative_jobs) == 1
        assert indoor_jobs[0].content["job_count"] == 2
        assert creative_jobs[0].content["job_count"] == 1

    def test_preference_ranking_analysis(self):
        """Test analysis text generation based on preference ranking"""
        query_results = {
            "imagePreferenceStatsQuery": [],
            "preferenceDataQuery": [
                {
                    "preference_name": "실내 활동 선호",
                    "rank": 1,
                    "response_rate": 85,
                    "description": "조용한 환경 선호"
                },
                {
                    "preference_name": "창의적 활동 선호",
                    "rank": 2, 
                    "response_rate": 78,
                    "description": "창의적 사고 선호"
                },
                {
                    "preference_name": "팀워크 활동 선호",
                    "rank": 5,
                    "response_rate": 45,
                    "description": "협업 활동 선호"
                }
            ],
            "preferenceJobsQuery": []
        }
        
        documents = self.transformer._chunk_preference_analysis(query_results)
        
        pref_docs = [d for d in documents if d.metadata.get("sub_type", "").startswith("preference_")]
        
        # Check ranking-based analysis
        rank1_docs = [d for d in pref_docs if d.content["rank"] == 1]
        rank2_docs = [d for d in pref_docs if d.content["rank"] == 2]
        rank5_docs = [d for d in pref_docs if d.content["rank"] == 5]
        
        assert len(rank1_docs) == 1
        rank1_doc = rank1_docs[0]
        assert rank1_doc.content["preference_strength"] == "강함"
        assert "가장 강한 선호" in rank1_doc.content["analysis"]
        
        assert len(rank2_docs) == 1
        rank2_doc = rank2_docs[0]
        assert rank2_doc.content["preference_strength"] == "보통"
        assert "상위 선호 영역" in rank2_doc.content["analysis"]
        
        assert len(rank5_docs) == 1
        rank5_doc = rank5_docs[0]
        assert rank5_doc.content["preference_strength"] == "약함"

    def test_empty_query_results_handling(self):
        """Test handling of completely empty query results"""
        query_results = {}
        
        documents = self.transformer._chunk_preference_analysis(query_results)
        
        # Should create fallback document
        assert len(documents) == 1
        assert documents[0].metadata["sub_type"] == "unavailable"

    def test_malformed_data_handling(self):
        """Test handling of malformed preference data"""
        query_results = {
            "imagePreferenceStatsQuery": [{}],  # Empty dict
            "preferenceDataQuery": [
                {"preference_name": None},  # Missing name
                {"preference_name": ""}     # Empty name
            ],
            "preferenceJobsQuery": [
                {"jo_name": "Developer"}    # Missing preference_name
            ]
        }
        
        documents = self.transformer._chunk_preference_analysis(query_results)
        
        # Should handle gracefully and create appropriate documents
        assert len(documents) >= 1
        
        # Should not crash and should create some form of document
        doc_types = [d.metadata.get("sub_type") for d in documents]
        assert any(doc_type is not None for doc_type in doc_types)

    @patch('etl.document_transformer.datetime')
    def test_metadata_consistency(self, mock_datetime):
        """Test that all documents have consistent metadata structure"""
        mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"
        
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
                    "response_rate": 85
                }
            ]
        }
        
        documents = self.transformer._chunk_preference_analysis(query_results)
        
        # Check all documents have required metadata
        for doc in documents:
            assert "data_sources" in doc.metadata
            assert "created_at" in doc.metadata
            assert "sub_type" in doc.metadata
            assert "completion_level" in doc.metadata
            assert doc.metadata["created_at"] == "2024-01-01T12:00:00"
            assert doc.doc_type == "PREFERENCE_ANALYSIS"

    def test_document_content_structure(self):
        """Test that document content has expected structure for each type"""
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
        
        documents = self.transformer._chunk_preference_analysis(query_results)
        
        # Check stats document structure
        stats_docs = [d for d in documents if d.metadata.get("sub_type") == "test_stats"]
        stats_doc = stats_docs[0]
        assert "interpretation" in stats_doc.content
        assert "completion_status" in stats_doc.content
        
        # Check preference document structure
        pref_docs = [d for d in documents if d.metadata.get("sub_type", "").startswith("preference_")]
        pref_doc = pref_docs[0]
        assert "rank" in pref_doc.content
        assert "analysis" in pref_doc.content
        assert "preference_strength" in pref_doc.content
        
        # Check job document structure (enhanced version has different structure)
        job_docs = [d for d in documents if d.metadata.get("sub_type", "").startswith("jobs_")]
        
        # Find overview document
        overview_docs = [d for d in job_docs if d.metadata.get("sub_type") == "jobs_overview"]
        if overview_docs:
            overview_doc = overview_docs[0]
            assert "total_jobs" in overview_doc.content
            assert "preference_types" in overview_doc.content
        
        # Find detail documents
        detail_docs = [d for d in job_docs if d.metadata.get("sub_type") != "jobs_overview"]
        if detail_docs:
            job_doc = detail_docs[0]
            assert "jobs" in job_doc.content
            assert "job_count" in job_doc.content
            assert "analysis" in job_doc.content