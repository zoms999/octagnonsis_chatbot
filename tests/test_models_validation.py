"""
Tests for Pydantic models and SQLAlchemy ORM models
"""

import pytest
from datetime import datetime
from uuid import uuid4, UUID
from typing import Dict, Any

from database.schemas import (
    DocumentType,
    ProcessingStatus,
    PersonalityProfileContent,
    ThinkingSkillsContent,
    CareerRecommendationsContent,
    ChatDocument,
    ChatDocumentCreate,
    ProcessingResult,
    TendencyInfo,
    ThinkingSkillInfo,
    CareerRecommendation
)
from database.models import (
    ChatUser,
    ChatDocument as ChatDocumentORM,
    DocumentType as DocumentTypeORM,
    ProcessingStatus as ProcessingStatusORM
)


class TestDocumentTypeEnum:
    """Test document type enumeration"""
    
    def test_document_type_values(self):
        """Test that all document types are defined correctly"""
        assert DocumentType.PERSONALITY_PROFILE == "PERSONALITY_PROFILE"
        assert DocumentType.THINKING_SKILLS == "THINKING_SKILLS"
        assert DocumentType.CAREER_RECOMMENDATIONS == "CAREER_RECOMMENDATIONS"
        assert DocumentType.LEARNING_STYLE == "LEARNING_STYLE"
        assert DocumentType.COMPETENCY_ANALYSIS == "COMPETENCY_ANALYSIS"
        assert DocumentType.PREFERENCE_ANALYSIS == "PREFERENCE_ANALYSIS"
    
    def test_orm_document_type_validation(self):
        """Test ORM document type validation"""
        assert DocumentTypeORM.is_valid("PERSONALITY_PROFILE")
        assert DocumentTypeORM.is_valid("THINKING_SKILLS")
        assert not DocumentTypeORM.is_valid("INVALID_TYPE")
        assert len(DocumentTypeORM.all_types()) == 6


class TestProcessingStatusEnum:
    """Test processing status enumeration"""
    
    def test_processing_status_values(self):
        """Test that all processing statuses are defined correctly"""
        assert ProcessingStatus.PENDING == "PENDING"
        assert ProcessingStatus.IN_PROGRESS == "IN_PROGRESS"
        assert ProcessingStatus.COMPLETED == "COMPLETED"
        assert ProcessingStatus.FAILED == "FAILED"
        assert ProcessingStatus.PARTIAL == "PARTIAL"
    
    def test_orm_processing_status_validation(self):
        """Test ORM processing status validation"""
        assert ProcessingStatusORM.is_valid("PENDING")
        assert ProcessingStatusORM.is_valid("COMPLETED")
        assert not ProcessingStatusORM.is_valid("INVALID_STATUS")
        assert len(ProcessingStatusORM.all_statuses()) == 5


class TestPersonalityProfileContent:
    """Test personality profile content validation"""
    
    def test_valid_personality_profile(self):
        """Test valid personality profile creation"""
        primary_tendency = TendencyInfo(
            name="창의형",
            code="tnd12000",
            explanation="새로운 아이디어를 창출하고...",
            rank=1,
            percentage_in_total=15.2,
            score=85
        )
        
        secondary_tendency = TendencyInfo(
            name="분석형",
            code="tnd21000",
            explanation="논리적 사고를 통해...",
            rank=2,
            percentage_in_total=12.8,
            score=78
        )
        
        top_tendencies = [
            TendencyInfo(name="창의형", code="tnd12000", explanation="...", rank=1, percentage_in_total=15.2, score=85),
            TendencyInfo(name="분석형", code="tnd21000", explanation="...", rank=2, percentage_in_total=12.8, score=78),
            TendencyInfo(name="탐구형", code="tnd31000", explanation="...", rank=3, percentage_in_total=10.5, score=72)
        ]
        
        bottom_tendencies = [
            TendencyInfo(name="안정형", code="tnd41000", explanation="...", rank=23, percentage_in_total=2.1, score=32),
            TendencyInfo(name="보수형", code="tnd42000", explanation="...", rank=24, percentage_in_total=1.8, score=28),
            TendencyInfo(name="수동형", code="tnd43000", explanation="...", rank=25, percentage_in_total=1.5, score=25)
        ]
        
        profile = PersonalityProfileContent(
            primary_tendency=primary_tendency,
            secondary_tendency=secondary_tendency,
            top_tendencies=top_tendencies,
            bottom_tendencies=bottom_tendencies,
            overall_summary="창의적이고 분석적인 성향을 가진 사용자입니다."
        )
        
        assert profile.primary_tendency.name == "창의형"
        assert profile.secondary_tendency.name == "분석형"
        assert len(profile.top_tendencies) == 3
        assert len(profile.bottom_tendencies) == 3
    
    def test_invalid_tendency_rank(self):
        """Test validation of tendency rank bounds"""
        with pytest.raises(ValueError):
            TendencyInfo(
                name="Invalid",
                code="invalid",
                explanation="Invalid rank",
                rank=0,  # Invalid: should be >= 1
                percentage_in_total=10.0
            )
        
        with pytest.raises(ValueError):
            TendencyInfo(
                name="Invalid",
                code="invalid",
                explanation="Invalid rank",
                rank=26,  # Invalid: should be <= 25
                percentage_in_total=10.0
            )


class TestThinkingSkillsContent:
    """Test thinking skills content validation"""
    
    def test_valid_thinking_skills(self):
        """Test valid thinking skills creation"""
        cognitive_abilities = []
        for i in range(8):
            skill = ThinkingSkillInfo(
                skill_name=f"Skill {i+1}",
                skill_code=f"skill_{i+1}",
                score=70 + i * 2,  # Keep scores within 0-100 range
                percentile=60.0 + i * 3,
                description=f"Description for skill {i+1}",
                strength_level="중"
            )
            cognitive_abilities.append(skill)
        
        thinking_skills = ThinkingSkillsContent(
            cognitive_abilities=cognitive_abilities,
            overall_iq_score=120,
            overall_percentile=85.0,
            strengths=["논리적 사고", "공간 지각"],
            areas_for_improvement=["언어 이해", "수치 추론"],
            analysis_summary="전반적으로 우수한 인지 능력을 보입니다."
        )
        
        assert len(thinking_skills.cognitive_abilities) == 8
        assert thinking_skills.overall_iq_score == 120
        assert thinking_skills.overall_percentile == 85.0
    
    def test_invalid_cognitive_abilities_count(self):
        """Test validation of exactly 8 cognitive abilities"""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ThinkingSkillsContent(
                cognitive_abilities=[],  # Invalid: must have exactly 8
                strengths=[],
                areas_for_improvement=[],
                analysis_summary="Invalid"
            )


class TestCareerRecommendationsContent:
    """Test career recommendations content validation"""
    
    def test_valid_career_recommendations(self):
        """Test valid career recommendations creation"""
        recommendations = []
        for i in range(5):
            rec = CareerRecommendation(
                job_name=f"Job {i+1}",
                job_code=f"job_{i+1}",
                match_percentage=80.0 + i * 2,
                reasoning=f"Good fit because of reason {i+1}",
                required_skills=[f"Skill A", f"Skill B"],
                personality_fit="Excellent fit",
                growth_potential="High"
            )
            recommendations.append(rec)
        
        career_recs = CareerRecommendationsContent(
            top_recommendations=recommendations,
            career_clusters={"IT": ["Developer", "Analyst"]},
            personality_career_mapping={"Creative": "Design roles"},
            industry_preferences=["Technology", "Healthcare"],
            work_environment_preferences=["Collaborative", "Flexible"],
            recommendations_summary="Strong match for technology careers"
        )
        
        assert len(career_recs.top_recommendations) == 5
        assert career_recs.career_clusters["IT"] == ["Developer", "Analyst"]


class TestChatDocument:
    """Test main ChatDocument model"""
    
    def test_valid_chat_document_creation(self):
        """Test valid chat document creation"""
        user_id = uuid4()
        
        # Create personality profile content
        primary_tendency = TendencyInfo(
            name="창의형", code="tnd12000", explanation="...", 
            rank=1, percentage_in_total=15.2, score=85
        )
        secondary_tendency = TendencyInfo(
            name="분석형", code="tnd21000", explanation="...", 
            rank=2, percentage_in_total=12.8, score=78
        )
        top_tendencies = [primary_tendency, secondary_tendency, 
                         TendencyInfo(name="탐구형", code="tnd31000", explanation="...", 
                                    rank=3, percentage_in_total=10.5, score=72)]
        bottom_tendencies = [
            TendencyInfo(name="안정형", code="tnd41000", explanation="...", 
                        rank=23, percentage_in_total=2.1, score=32),
            TendencyInfo(name="보수형", code="tnd42000", explanation="...", 
                        rank=24, percentage_in_total=1.8, score=28),
            TendencyInfo(name="수동형", code="tnd43000", explanation="...", 
                        rank=25, percentage_in_total=1.5, score=25)
        ]
        
        content = PersonalityProfileContent(
            primary_tendency=primary_tendency,
            secondary_tendency=secondary_tendency,
            top_tendencies=top_tendencies,
            bottom_tendencies=bottom_tendencies,
            overall_summary="창의적이고 분석적인 성향"
        )
        
        document = ChatDocument(
            user_id=user_id,
            doc_type=DocumentType.PERSONALITY_PROFILE,
            content=content,
            summary_text="사용자는 창의적이고 분석적인 성향을 가지고 있습니다.",
            metadata={"version": "1.0", "source": "aptitude_test"}
        )
        
        assert document.user_id == user_id
        assert document.doc_type == DocumentType.PERSONALITY_PROFILE
        assert isinstance(document.content, PersonalityProfileContent)
        assert len(document.summary_text) >= 10


class TestProcessingResult:
    """Test processing result model"""
    
    def test_valid_processing_result(self):
        """Test valid processing result creation"""
        user_id = uuid4()
        
        result = ProcessingResult(
            user_id=user_id,
            status=ProcessingStatus.COMPLETED,
            documents_created=6,
            documents_failed=0,
            error_messages=[],
            processing_time_seconds=45.2
        )
        
        assert result.user_id == user_id
        assert result.status == ProcessingStatus.COMPLETED
        assert result.documents_created == 6
        assert result.documents_failed == 0
        assert result.processing_time_seconds == 45.2
    
    def test_processing_result_with_errors(self):
        """Test processing result with errors"""
        user_id = uuid4()
        
        result = ProcessingResult(
            user_id=user_id,
            status=ProcessingStatus.PARTIAL,
            documents_created=4,
            documents_failed=2,
            error_messages=["Failed to process thinking skills", "Vector embedding failed"],
            processing_time_seconds=120.5
        )
        
        assert result.status == ProcessingStatus.PARTIAL
        assert result.documents_failed == 2
        assert len(result.error_messages) == 2


class TestChatDocumentCreate:
    """Test chat document creation model"""
    
    def test_valid_document_create(self):
        """Test valid document creation request"""
        user_id = uuid4()
        
        doc_create = ChatDocumentCreate(
            user_id=user_id,
            doc_type=DocumentType.PERSONALITY_PROFILE,
            content={"primary_tendency": {"name": "창의형"}},
            summary_text="창의적인 성향의 사용자",
            metadata={"version": "1.0"}
        )
        
        assert doc_create.user_id == user_id
        assert doc_create.doc_type == DocumentType.PERSONALITY_PROFILE
        assert len(doc_create.summary_text) >= 10
    
    def test_invalid_short_summary(self):
        """Test validation of minimum summary text length"""
        user_id = uuid4()
        
        with pytest.raises(ValueError):
            ChatDocumentCreate(
                user_id=user_id,
                doc_type=DocumentType.PERSONALITY_PROFILE,
                content={"test": "data"},
                summary_text="short",  # Invalid: too short
                metadata={}
            )