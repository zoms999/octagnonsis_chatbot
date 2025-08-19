"""
Unit tests for enhanced preference document creation with missing data scenarios
Tests the new informative document templates and fallback logic
"""

import pytest
from datetime import datetime
from unittest.mock import patch
from etl.document_transformer import DocumentTransformer, TransformedDocument


class TestEnhancedPreferenceDocuments:
    """Test suite for enhanced preference document creation with missing data scenarios"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.transformer = DocumentTransformer()
    
    def test_complete_preference_data_with_summary(self):
        """Test document creation with complete preference data including summary document"""
        query_results = {
            "imagePreferenceStatsQuery": [{
                "total_image_count": 120,
                "response_count": 108,
                "response_rate": 90
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
        
        documents = self.transformer._chunk_preference_analysis(query_results)
        
        # Should create completion summary + stats + preferences overview + individual prefs + jobs overview + job details
        assert len(documents) >= 6
        
        # Check completion summary document
        summary_docs = [d for d in documents if d.metadata.get("sub_type") == "completion_summary"]
        assert len(summary_docs) == 1
        summary_doc = summary_docs[0]
        assert summary_doc.content["completion_status"] == "완료"
        assert summary_doc.content["response_rate"] == 90
        assert summary_doc.content["preference_count"] == 2
        assert summary_doc.content["job_count"] == 1
        assert "quality_score" in summary_doc.content
        assert summary_doc.metadata["completion_level"] == "complete"

    def test_no_preference_data_comprehensive_fallback(self):
        """Test comprehensive fallback document when no preference data is available"""
        query_results = {
            "imagePreferenceStatsQuery": [],
            "preferenceDataQuery": [],
            "preferenceJobsQuery": []
        }
        
        documents = self.transformer._chunk_preference_analysis(query_results)
        
        # Should create single comprehensive fallback document
        assert len(documents) == 1
        
        fallback_doc = documents[0]
        assert fallback_doc.metadata["sub_type"] == "unavailable"
        assert fallback_doc.metadata["completion_level"] == "none"
        assert fallback_doc.metadata["missing_count"] == 3
        
        # Check enhanced content structure
        content = fallback_doc.content
        assert "missing_components" in content
        assert "explanation" in content
        assert "alternatives" in content
        assert "recommendation" in content
        assert "data_availability" in content
        assert "next_steps" in content
        
        # Check that all components are marked as missing
        assert len(content["missing_components"]) == 3
        assert "이미지 선호도 검사 통계" in content["missing_components"]
        assert "선호도 분석 결과" in content["missing_components"]
        assert "선호도 기반 직업 추천" in content["missing_components"]
        
        # Check data availability assessment
        availability = content["data_availability"]
        assert availability["검사_통계"] == "처리 중"
        assert availability["선호도_분석"] == "처리 중"
        assert availability["직업_추천"] == "처리 중"
        
        # Check next steps are provided
        assert isinstance(content["next_steps"], list)
        assert len(content["next_steps"]) > 0

    def test_partial_preference_data_with_partial_document(self):
        """Test partial document creation when some preference data is available"""
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
            "preferenceJobsQuery": []  # Missing jobs data
        }
        
        documents = self.transformer._chunk_preference_analysis(query_results)
        
        # Should create partial document + available data documents
        assert len(documents) >= 3  # partial + stats + preferences overview + individual pref
        
        # Check partial document
        partial_docs = [d for d in documents if d.metadata.get("sub_type") == "partial_available"]
        assert len(partial_docs) == 1
        partial_doc = partial_docs[0]
        
        assert partial_doc.content["status"] == "부분 완료"
        assert partial_doc.content["completion_percentage"] == (2/3) * 100  # 2 out of 3 available
        assert len(partial_doc.content["available_components"]) == 2
        assert len(partial_doc.content["missing_components"]) == 1
        assert "선호도 기반 직업 추천" in partial_doc.content["missing_components"]
        
        # Check metadata
        assert partial_doc.metadata["completion_level"] == "partial"
        assert partial_doc.metadata["available_count"] == 2
        assert partial_doc.metadata["missing_count"] == 1

    def test_enhanced_stats_document_with_detailed_interpretation(self):
        """Test enhanced stats document with detailed interpretation and recommendations"""
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
        
        # Find stats document
        stats_docs = [d for d in documents if d.metadata.get("sub_type") == "test_stats"]
        assert len(stats_docs) == 1
        stats_doc = stats_docs[0]
        
        # Check enhanced content
        content = stats_doc.content
        assert "interpretation" in content
        assert "recommendations" in content
        assert "quality_indicator" in content
        assert "next_steps" in content
        
        # Check high response rate interpretation
        assert "매우 충실히 완료" in content["interpretation"]
        assert "🟢 매우 높음" == content["quality_indicator"]
        
        # Check recommendations are provided
        assert isinstance(content["recommendations"], list)
        assert len(content["recommendations"]) > 0
        
        # Check next steps are provided
        assert isinstance(content["next_steps"], list)
        assert len(content["next_steps"]) > 0

    def test_enhanced_preference_data_documents_with_insights(self):
        """Test enhanced preference data documents with insights and career implications"""
        query_results = {
            "imagePreferenceStatsQuery": [],
            "preferenceDataQuery": [
                {
                    "preference_name": "실내 활동 선호",
                    "rank": 1,
                    "response_rate": 85,
                    "description": "조용하고 집중할 수 있는 환경을 선호합니다."
                },
                {
                    "preference_name": "창의적 활동 선호",
                    "rank": 2,
                    "response_rate": 78,
                    "description": "새로운 아이디어를 만들어내는 활동을 좋아합니다."
                }
            ],
            "preferenceJobsQuery": []
        }
        
        documents = self.transformer._chunk_preference_analysis(query_results)
        
        # Find preferences overview document
        overview_docs = [d for d in documents if d.metadata.get("sub_type") == "preferences_overview"]
        assert len(overview_docs) == 1
        overview_doc = overview_docs[0]
        
        # Check enhanced overview content
        content = overview_doc.content
        assert "insights" in content
        assert "preference_distribution" in content
        assert "recommendations" in content
        
        # Check insights are generated
        assert isinstance(content["insights"], list)
        assert len(content["insights"]) > 0
        
        # Check preference distribution analysis
        distribution = content["preference_distribution"]
        assert "strong_preferences" in distribution
        assert "concentration_level" in distribution
        
        # Find individual preference documents
        pref_docs = [d for d in documents if d.metadata.get("sub_type", "").startswith("preference_")]
        assert len(pref_docs) == 2
        
        # Check enhanced individual preference content
        rank1_doc = next(d for d in pref_docs if d.content["rank"] == 1)
        content = rank1_doc.content
        assert "career_implications" in content
        assert "development_suggestions" in content
        assert "related_activities" in content
        
        # Check career implications are provided
        assert isinstance(content["career_implications"], list)
        assert len(content["career_implications"]) > 0

    def test_enhanced_job_documents_with_comprehensive_analysis(self):
        """Test enhanced job documents with comprehensive analysis and career paths"""
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
                },
                {
                    "preference_name": "실내 활동 선호",
                    "preference_type": "rimg1",
                    "jo_name": "데이터 분석가",
                    "jo_outline": "데이터 분석",
                    "jo_mainbusiness": "데이터 수집 및 분석",
                    "majors": "통계학, 데이터사이언스"
                }
            ]
        }
        
        documents = self.transformer._chunk_preference_analysis(query_results)
        
        # Find jobs overview document
        overview_docs = [d for d in documents if d.metadata.get("sub_type") == "jobs_overview"]
        assert len(overview_docs) == 1
        overview_doc = overview_docs[0]
        
        # Check enhanced overview content
        content = overview_doc.content
        assert "overview_insights" in content
        assert "career_diversity" in content
        assert "recommendations" in content
        
        # Find individual job preference documents
        job_docs = [d for d in documents if d.metadata.get("sub_type", "").startswith("jobs_")]
        job_detail_docs = [d for d in job_docs if d.metadata.get("sub_type") != "jobs_overview"]
        assert len(job_detail_docs) == 1  # One preference type
        
        job_doc = job_detail_docs[0]
        content = job_doc.content
        
        # Check enhanced job content
        assert "career_paths" in content
        assert "industry_analysis" in content
        assert "skill_requirements" in content
        assert "education_recommendations" in content
        assert "next_steps" in content
        
        # Check career paths are suggested
        assert isinstance(content["career_paths"], list)
        
        # Check industry analysis
        industry_analysis = content["industry_analysis"]
        assert "industry_count" in industry_analysis
        assert "industries" in industry_analysis

    def test_quality_score_calculation(self):
        """Test quality score calculation for preference analysis completeness"""
        # Test high quality scenario
        high_score = self.transformer._calculate_preference_quality_score(95, 8, 15)
        assert high_score == 100.0
        
        # Test medium quality scenario
        medium_score = self.transformer._calculate_preference_quality_score(75, 5, 8)
        assert 70 <= medium_score <= 85
        
        # Test low quality scenario
        low_score = self.transformer._calculate_preference_quality_score(30, 2, 3)
        assert low_score <= 50

    def test_missing_data_explanation_generation(self):
        """Test generation of detailed explanations for missing data"""
        # Test all data missing
        all_missing = ["이미지 선호도 검사 통계", "선호도 분석 결과", "선호도 기반 직업 추천"]
        explanation = self.transformer._generate_missing_data_explanation(all_missing)
        assert "모든 데이터를 이용할 수 없습니다" in explanation
        assert "검사를 아직 시작하지 않았거나" in explanation
        
        # Test partial data missing
        partial_missing = ["선호도 분석 결과"]
        explanation = self.transformer._generate_missing_data_explanation(partial_missing)
        assert "선호도 분석 결과 데이터를 이용할 수 없습니다" in explanation
        
        # Test two components missing
        two_missing = ["이미지 선호도 검사 통계", "선호도 기반 직업 추천"]
        explanation = self.transformer._generate_missing_data_explanation(two_missing)
        assert "다음 선호도 분석 데이터를 이용할 수 없습니다" in explanation

    def test_alternative_suggestions_generation(self):
        """Test generation of alternative test result suggestions"""
        alternatives = self.transformer._generate_alternative_suggestions()
        
        # Check that all major alternative categories are included
        assert "성향 분석" in alternatives
        assert "사고력 분석" in alternatives
        assert "역량 분석" in alternatives
        assert "직업 추천" in alternatives
        assert "학습 스타일" in alternatives
        
        # Check formatting includes emojis and structure
        assert "🔍" in alternatives
        assert "🧠" in alternatives
        assert "💪" in alternatives
        assert "💼" in alternatives
        assert "📚" in alternatives

    def test_specific_recommendations_generation(self):
        """Test generation of specific recommendations based on missing components"""
        # Test all missing
        all_missing = ["이미지 선호도 검사 통계", "선호도 분석 결과", "선호도 기반 직업 추천"]
        recommendation = self.transformer._generate_specific_recommendations(all_missing)
        assert "검사를 완료하지 않으셨다면" in recommendation
        
        # Test partial missing
        partial_missing = ["선호도 분석 결과", "선호도 기반 직업 추천"]
        recommendation = self.transformer._generate_specific_recommendations(partial_missing)
        assert "일부 선호도 데이터는 처리 중" in recommendation
        
        # Test single missing
        single_missing = ["선호도 기반 직업 추천"]
        recommendation = self.transformer._generate_specific_recommendations(single_missing)
        assert "대부분의 선호도 분석 결과는 이용 가능" in recommendation

    def test_data_availability_assessment(self):
        """Test assessment of data availability for each component"""
        available_data = {"stats": True, "preferences": False, "jobs": True}
        assessment = self.transformer._assess_data_availability(available_data)
        
        assert assessment["검사_통계"] == "이용 가능"
        assert assessment["선호도_분석"] == "처리 중"
        assert assessment["직업_추천"] == "이용 가능"

    def test_next_steps_suggestions(self):
        """Test generation of specific next steps based on missing data"""
        # Test all missing
        all_missing = ["이미지 선호도 검사 통계", "선호도 분석 결과", "선호도 기반 직업 추천"]
        steps = self.transformer._suggest_next_steps(all_missing)
        assert len(steps) >= 3
        assert any("검사 완료 여부를 확인" in step for step in steps)
        
        # Test stats missing
        stats_missing = ["이미지 선호도 검사 통계"]
        steps = self.transformer._suggest_next_steps(stats_missing)
        assert any("이용 가능한 선호도 분석" in step for step in steps)

    def test_low_response_rate_handling_enhanced(self):
        """Test enhanced handling of low response rate scenarios"""
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
        
        # Find stats document
        stats_docs = [d for d in documents if d.metadata.get("sub_type") == "test_stats"]
        assert len(stats_docs) == 1
        stats_doc = stats_docs[0]
        
        # Check low response rate handling
        content = stats_doc.content
        assert content["completion_status"] == "미완료"
        assert content["quality_indicator"] == "🔴 매우 낮음"
        assert "정확히 파악하기 어려우며" in content["interpretation"]
        
        # Check recommendations focus on completing the test
        recommendations = content["recommendations"]
        assert any("검사를 더 완료" in rec for rec in recommendations)

    @patch('etl.document_transformer.datetime')
    def test_metadata_consistency_enhanced(self, mock_datetime):
        """Test that all enhanced documents have consistent metadata structure"""
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
            ],
            "preferenceJobsQuery": [
                {
                    "preference_name": "실내 활동 선호",
                    "jo_name": "소프트웨어 개발자"
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
            
            # Check enhanced metadata fields based on document type
            if doc.metadata["sub_type"] == "completion_summary":
                assert "quality_score" in doc.metadata
            elif doc.metadata["sub_type"] == "test_stats":
                assert "response_rate" in doc.metadata
            elif doc.metadata["sub_type"] == "partial_available":
                assert "available_count" in doc.metadata
                assert "missing_count" in doc.metadata

    def test_malformed_data_resilience_enhanced(self):
        """Test enhanced resilience to malformed preference data"""
        query_results = {
            "imagePreferenceStatsQuery": [{}],  # Empty stats
            "preferenceDataQuery": [
                {"preference_name": None},  # None name
                {"preference_name": ""},    # Empty name
                None,                       # None object
                {"preference_name": "Valid Preference", "rank": 1}  # Valid data
            ],
            "preferenceJobsQuery": [
                {"jo_name": "Developer"},   # Missing preference_name
                None,                       # None object
                {"preference_name": "Valid", "jo_name": "Designer"}  # Valid data
            ]
        }
        
        documents = self.transformer._chunk_preference_analysis(query_results)
        
        # Should handle gracefully and create appropriate documents
        assert len(documents) >= 1
        
        # Should create partial document since some data is available
        partial_docs = [d for d in documents if d.metadata.get("sub_type") == "partial_available"]
        assert len(partial_docs) == 1
        
        # Should filter out invalid preference data but keep valid ones
        pref_docs = [d for d in documents if d.metadata.get("sub_type", "").startswith("preference_")]
        assert len(pref_docs) == 1  # Only the valid preference should create a document

    def test_edge_case_empty_query_results(self):
        """Test handling of completely empty query results"""
        query_results = {}
        
        documents = self.transformer._chunk_preference_analysis(query_results)
        
        # Should create fallback document
        assert len(documents) == 1
        assert documents[0].metadata["sub_type"] == "unavailable"
        assert documents[0].metadata["completion_level"] == "none"
        assert documents[0].metadata["missing_count"] == 3