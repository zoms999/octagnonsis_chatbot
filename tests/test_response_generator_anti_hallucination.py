"""
Unit tests for anti-hallucination measures in response generator.

Tests the response generator's ability to validate preference data availability,
detect hallucination patterns, and provide appropriate disclaimers and alternatives.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime
import json

from rag.response_generator import ResponseGenerator, GeneratedResponse, ResponseQuality
from rag.context_builder import ConstructedContext, PromptTemplate, RetrievedDocument
from database.models import ChatDocument


class TestResponseGeneratorAntiHallucination:
    """Test anti-hallucination measures in response generator."""
    
    @pytest.fixture
    def response_generator(self):
        """Response generator instance for testing."""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
            generator = ResponseGenerator()
            # Mock the Gemini API call
            generator._call_gemini_api = AsyncMock()
            return generator
    
    def create_preference_document(self, completion_level="complete", content=None, metadata=None):
        """Helper to create preference documents for testing."""
        if content is None:
            if completion_level == "complete":
                content = {
                    "completion_status": "완료",
                    "preferences": [
                        {"preference_name": "창의적 활동", "rank": 1, "score": 85},
                        {"preference_name": "분석적 사고", "rank": 2, "score": 78}
                    ],
                    "stats": {"response_rate": 95, "total_image_count": 50},
                    "jobs": [{"job_name": "디자이너", "match_score": 90}]
                }
            elif completion_level == "partial":
                content = {
                    "completion_status": "부분 완료",
                    "preferences": [{"preference_name": "창의적 활동", "rank": 1}],
                    "stats": None,
                    "jobs": None
                }
            else:  # missing
                content = {"message": "선호도 분석 데이터를 찾을 수 없습니다"}
        
        if metadata is None:
            metadata = {"completion_level": completion_level}
        
        return ChatDocument(
            doc_id=uuid4(),
            user_id=uuid4(),
            doc_type="PREFERENCE_ANALYSIS",
            content=content,
            summary_text="선호도 분석 결과",
            metadata=metadata,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def create_constructed_context(self, template=PromptTemplate.PREFERENCE_EXPLAIN, 
                                 question="내 선호도 알려줘", documents=None):
        """Helper to create constructed context for testing."""
        if documents is None:
            documents = []
        
        retrieved_docs = [
            RetrievedDocument(
                document=doc,
                similarity_score=0.8,
                relevance_score=0.9,
                content_summary=doc.summary_text,
                key_points=["선호도 분석"]
            ) for doc in documents
        ]
        
        return ConstructedContext(
            user_question=question,
            retrieved_documents=retrieved_docs,
            prompt_template=template,
            formatted_prompt=f"사용자 질문: {question}",
            context_metadata={},
            token_count_estimate=100
        )

    def test_validate_preference_data_availability_complete(self, response_generator):
        """Test preference data availability validation with complete data."""
        complete_doc = self.create_preference_document(completion_level="complete")
        context = self.create_constructed_context(documents=[complete_doc])
        
        result = response_generator._validate_preference_data_availability(context)
        
        assert result["has_preference_docs"] is True
        assert result["completion_level"] == "complete"
        assert result["data_quality"] == "high"
        assert "stats" in result["available_components"]
        assert "preferences" in result["available_components"]
        assert "jobs" in result["available_components"]
        assert len(result["missing_components"]) == 0

    def test_validate_preference_data_availability_partial(self, response_generator):
        """Test preference data availability validation with partial data."""
        partial_doc = self.create_preference_document(completion_level="partial")
        context = self.create_constructed_context(documents=[partial_doc])
        
        result = response_generator._validate_preference_data_availability(context)
        
        assert result["has_preference_docs"] is True
        assert result["completion_level"] == "partial"
        assert result["data_quality"] in ["low", "medium"]
        assert "preferences" in result["available_components"]
        assert "stats" in result["missing_components"]
        assert "jobs" in result["missing_components"]

    def test_validate_preference_data_availability_missing(self, response_generator):
        """Test preference data availability validation with missing data."""
        context = self.create_constructed_context(documents=[])  # No preference documents
        
        result = response_generator._validate_preference_data_availability(context)
        
        assert result["has_preference_docs"] is False
        assert result["completion_level"] == "missing"
        assert result["data_quality"] == "none"
        assert len(result["available_components"]) == 0
        assert "stats" in result["missing_components"]
        assert "preferences" in result["missing_components"]
        assert "jobs" in result["missing_components"]

    def test_detect_hallucination_patterns_specific_data(self, response_generator):
        """Test detection of specific data hallucination patterns."""
        data_availability = {
            "completion_level": "missing",
            "data_quality": "none"
        }
        
        # Response with specific claims that shouldn't exist
        response = "당신의 선호도 1위는 창의적 활동이고, 응답률은 95%입니다. 선호도 점수는 85점으로 나타났습니다."
        
        patterns = response_generator._detect_preference_hallucination_patterns(response, data_availability)
        
        assert len(patterns) > 0
        pattern_types = [p["type"] for p in patterns]
        assert "specific_ranking" in pattern_types
        # The response_rate pattern matches "응답률은 95%" instead of specific_percentage
        assert "response_rate" in pattern_types or "specific_percentage" in pattern_types
        assert "specific_score" in pattern_types

    def test_detect_hallucination_patterns_definitive_claims(self, response_generator):
        """Test detection of definitive claim patterns."""
        data_availability = {
            "completion_level": "partial",
            "data_quality": "low"
        }
        
        response = "당신의 선호도는 확실히 창의적 활동입니다. 가장 선호하는 것은 예술 분야입니다."
        
        patterns = response_generator._detect_preference_hallucination_patterns(response, data_availability)
        
        assert len(patterns) > 0
        pattern_types = [p["type"] for p in patterns]
        assert any("definitive" in ptype or "certainty" in ptype or "absolute" in ptype for ptype in pattern_types)

    def test_generate_data_availability_disclaimer_missing(self, response_generator):
        """Test disclaimer generation for missing data."""
        data_availability = {
            "completion_level": "missing",
            "available_components": [],
            "missing_components": ["stats", "preferences", "jobs"]
        }
        
        detected_patterns = [
            {"type": "specific_ranking", "severity": "high"},
            {"type": "specific_percentage", "severity": "high"}
        ]
        
        disclaimer = response_generator._generate_data_availability_disclaimer(data_availability, detected_patterns)
        
        assert "⚠️ 중요" in disclaimer
        assert "데이터가 준비되지 않아" in disclaimer
        assert "일반적인 가이드라인" in disclaimer

    def test_generate_data_availability_disclaimer_partial(self, response_generator):
        """Test disclaimer generation for partial data."""
        data_availability = {
            "completion_level": "partial",
            "available_components": ["preferences"],
            "missing_components": ["stats", "jobs"]
        }
        
        detected_patterns = [
            {"type": "definitive_claim", "severity": "high"}
        ]
        
        disclaimer = response_generator._generate_data_availability_disclaimer(data_availability, detected_patterns)
        
        assert "💡 데이터 상태 안내" in disclaimer
        assert "preferences" in disclaimer
        assert "stats, jobs" in disclaimer

    def test_validate_preference_response_with_complete_data(self, response_generator):
        """Test preference response validation with complete data (should not add disclaimers)."""
        complete_doc = self.create_preference_document(completion_level="complete")
        context = self.create_constructed_context(
            template=PromptTemplate.PREFERENCE_EXPLAIN,
            documents=[complete_doc]
        )
        
        response = "당신의 선호도 1위는 창의적 활동이고, 점수는 85점입니다."
        
        validated_response = response_generator._validate_preference_response(response, context)
        
        # Should not add disclaimers for complete data
        assert "⚠️" not in validated_response
        assert "💡" not in validated_response
        assert validated_response == response

    def test_validate_preference_response_with_missing_data(self, response_generator):
        """Test preference response validation with missing data (should add disclaimers)."""
        context = self.create_constructed_context(
            template=PromptTemplate.PREFERENCE_MISSING,
            documents=[]  # No preference documents
        )
        
        response = "당신의 선호도 1위는 창의적 활동이고, 선호도 점수는 85점입니다."
        
        validated_response = response_generator._validate_preference_response(response, context)
        
        # Should add disclaimer for missing data with specific claims
        assert "⚠️ 중요" in validated_response
        assert "데이터가 준비되지 않아" in validated_response

    def test_validate_preference_response_non_preference_question(self, response_generator):
        """Test that non-preference questions are not affected by validation."""
        personality_doc = ChatDocument(
            doc_id=uuid4(),
            user_id=uuid4(),
            doc_type="PERSONALITY_PROFILE",
            content={"primary_tendency": {"name": "창의형"}},
            summary_text="성격 분석",
            metadata={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        context = self.create_constructed_context(
            template=PromptTemplate.PERSONALITY_EXPLAIN,
            question="내 성격은 어때?",
            documents=[personality_doc]
        )
        
        response = "당신은 창의적인 성격입니다."
        
        validated_response = response_generator._validate_preference_response(response, context)
        
        # Should not modify non-preference responses
        assert validated_response == response

    def test_get_preference_acknowledgment_template_missing(self, response_generator):
        """Test acknowledgment template for missing preference data."""
        data_availability = {
            "completion_level": "missing",
            "available_components": []
        }
        
        template = response_generator._get_preference_acknowledgment_template(
            data_availability, "내 선호도 알려줘"
        )
        
        assert "현재 선호도 분석 데이터가 준비되지 않았습니다" in template
        assert "다른 검사 결과를 통해" in template

    def test_get_preference_acknowledgment_template_partial(self, response_generator):
        """Test acknowledgment template for partial preference data."""
        data_availability = {
            "completion_level": "partial",
            "available_components": ["preferences", "stats"]
        }
        
        template = response_generator._get_preference_acknowledgment_template(
            data_availability, "내 선호도 분석해줘"
        )
        
        assert "선호도 순위, 통계 정보는 준비되어 있지만" in template
        assert "일부 선호도 데이터가 아직 처리 중" in template

    def test_get_alternative_analysis_suggestions_career_focus(self, response_generator):
        """Test alternative suggestions for career-focused preference questions."""
        suggestions = response_generator._get_alternative_analysis_suggestions(
            "내 선호도에 맞는 직업이 뭐야?"
        )
        
        assert "🔍 대안 분석 방법" in suggestions
        assert "내게 맞는 직업은 무엇인가요?" in suggestions
        assert "성격 분석 결과를 통해" in suggestions

    def test_get_alternative_analysis_suggestions_activity_focus(self, response_generator):
        """Test alternative suggestions for activity-focused preference questions."""
        suggestions = response_generator._get_alternative_analysis_suggestions(
            "내가 좋아하는 활동이 뭐야?"
        )
        
        assert "🔍 대안 분석 방법" in suggestions
        assert "내 강점을 활용할 수 있는 활동은?" in suggestions
        assert "어떤 취미가 나에게 맞을까요?" in suggestions

    def test_generate_preference_focused_fallback_with_personality_docs(self, response_generator):
        """Test preference-focused fallback when personality documents are available."""
        personality_doc = ChatDocument(
            doc_id=uuid4(),
            user_id=uuid4(),
            doc_type="PERSONALITY_PROFILE",
            content={"primary_tendency": {"name": "창의형"}},
            summary_text="성격 분석",
            metadata={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        context = self.create_constructed_context(
            question="내 선호도 알려줘",
            documents=[personality_doc]
        )
        
        fallback = response_generator._generate_preference_focused_fallback(context)
        
        assert "현재 선호도 분석 데이터에 접근할 수 없지만" in fallback
        assert "성격 분석 결과를 통해" in fallback
        assert "내 성격에 맞는 활동은 무엇인가요?" in fallback

    def test_generate_preference_focused_fallback_with_no_docs(self, response_generator):
        """Test preference-focused fallback when no documents are available."""
        context = self.create_constructed_context(
            question="내 선호도 알려줘",
            documents=[]
        )
        
        fallback = response_generator._generate_preference_focused_fallback(context)
        
        assert "현재 선호도 분석 데이터에 접근할 수 없지만" in fallback
        assert "다른 검사 결과가 준비되면" in fallback
        assert "적성검사를 완료하셨는지 확인" in fallback

    @pytest.mark.asyncio
    async def test_enhance_with_preference_alternatives_missing_data(self, response_generator):
        """Test enhancement with alternatives for missing preference data."""
        context = self.create_constructed_context(
            template=PromptTemplate.PREFERENCE_MISSING,
            question="내가 좋아하는 활동이 뭐야?",
            documents=[]
        )
        
        response = "현재 선호도 데이터가 없습니다."
        
        enhanced = await response_generator._enhance_with_preference_alternatives(response, context)
        
        assert "🔍 대안 분석 방법" in enhanced
        assert "내 강점을 활용할 수 있는 활동은?" in enhanced
        assert "어떤 취미가 나에게 맞을까요?" in enhanced

    @pytest.mark.asyncio
    async def test_enhance_with_preference_alternatives_partial_data(self, response_generator):
        """Test enhancement with alternatives for partial preference data."""
        partial_doc = self.create_preference_document(completion_level="partial")
        context = self.create_constructed_context(
            template=PromptTemplate.PREFERENCE_PARTIAL,
            documents=[partial_doc]
        )
        
        response = "부분적인 선호도 데이터를 바탕으로 분석했습니다."
        
        enhanced = await response_generator._enhance_with_preference_alternatives(response, context)
        
        assert "💡 완전한 선호도 분석을 위한 팁" in enhanced
        assert "다른 검사 결과(성격, 사고능력, 역량)와 함께" in enhanced
        assert "현재 결과만으로도 의미 있는 인사이트" in enhanced

    @pytest.mark.asyncio
    async def test_generate_response_with_missing_preference_data_early_return(self, response_generator):
        """Test that generate_response returns early for missing preference data."""
        context = self.create_constructed_context(
            template=PromptTemplate.PREFERENCE_EXPLAIN,  # Not PREFERENCE_MISSING
            question="내 선호도 1위가 뭐야?",
            documents=[]  # No preference documents
        )
        
        # Should return early without calling Gemini API
        result = await response_generator.generate_response(context, "test_user")
        
        assert result.quality_score == ResponseQuality.ACCEPTABLE
        assert result.confidence_score == 0.6
        assert "현재 선호도 분석 데이터에 접근할 수 없지만" in result.content
        # Verify Gemini API was not called
        response_generator._call_gemini_api.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_response_with_complete_preference_data(self, response_generator):
        """Test normal response generation with complete preference data."""
        complete_doc = self.create_preference_document(completion_level="complete")
        context = self.create_constructed_context(
            template=PromptTemplate.PREFERENCE_EXPLAIN,
            documents=[complete_doc]
        )
        
        # Mock Gemini response
        mock_response = "당신의 선호도 1위는 창의적 활동입니다."
        response_generator._call_gemini_api.return_value = mock_response
        
        result = await response_generator.generate_response(context, "test_user")
        
        # Should proceed normally and call Gemini API
        response_generator._call_gemini_api.assert_called_once()
        assert result.quality_score in [ResponseQuality.GOOD, ResponseQuality.EXCELLENT, ResponseQuality.ACCEPTABLE]
        assert "창의적 활동" in result.content

    def test_extract_topic_from_question_preference(self, response_generator):
        """Test that preference-related questions are correctly identified."""
        test_cases = [
            ("내 선호도 알려줘", "preference"),
            ("이미지 선호도는 어떻게 나왔어?", "preference"),
            ("나는 뭘 좋아해?", "preference"),
            ("내 관심사가 뭐야?", "preference"),
            ("취향 분석 결과 보여줘", "preference"),
            ("내 성격은 어때?", "personality"),  # Should not be preference
            ("추천 직업이 뭐야?", "career"),  # Should not be preference
        ]
        
        for question, expected_topic in test_cases:
            topic = response_generator._extract_topic_from_question(question)
            assert topic == expected_topic, f"Question '{question}' should be topic '{expected_topic}', got '{topic}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])