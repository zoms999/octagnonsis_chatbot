"""
Pydantic models for data validation in Aptitude Chatbot RAG System
Defines validation schemas for document types and API requests/responses
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class DocumentType(str, Enum):
    """Enumeration for document types"""
    PERSONALITY_PROFILE = "PERSONALITY_PROFILE"
    THINKING_SKILLS = "THINKING_SKILLS"
    CAREER_RECOMMENDATIONS = "CAREER_RECOMMENDATIONS"
    LEARNING_STYLE = "LEARNING_STYLE"
    COMPETENCY_ANALYSIS = "COMPETENCY_ANALYSIS"
    PREFERENCE_ANALYSIS = "PREFERENCE_ANALYSIS"


class ProcessingStatus(str, Enum):
    """Enumeration for processing status codes"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


# Base document content models
class TendencyInfo(BaseModel):
    """Model for personality tendency information"""
    name: str = Field(..., description="Tendency name in Korean")
    code: str = Field(..., description="Tendency code (e.g., tnd12000)")
    explanation: str = Field(..., description="Detailed explanation of the tendency")
    rank: int = Field(..., ge=1, le=25, description="Rank among all tendencies")
    percentage_in_total: float = Field(..., ge=0, le=100, description="Percentage in total population")
    score: Optional[int] = Field(None, ge=0, le=100, description="Individual score for this tendency")


class PersonalityProfileContent(BaseModel):
    """Content structure for personality profile documents"""
    primary_tendency: TendencyInfo = Field(..., description="Primary personality tendency")
    secondary_tendency: TendencyInfo = Field(..., description="Secondary personality tendency")
    top_tendencies: List[TendencyInfo] = Field(..., min_length=3, max_length=10, description="Top ranked tendencies")
    bottom_tendencies: List[TendencyInfo] = Field(..., min_length=3, max_length=10, description="Bottom ranked tendencies")
    overall_summary: str = Field(..., description="Overall personality summary")
    
    @field_validator('top_tendencies', 'bottom_tendencies')
    @classmethod
    def validate_tendency_lists(cls, v):
        if not v:
            raise ValueError("Tendency list cannot be empty")
        # Ensure ranks are unique within the list
        ranks = [t.rank for t in v]
        if len(ranks) != len(set(ranks)):
            raise ValueError("Tendency ranks must be unique within the list")
        return v


class ThinkingSkillInfo(BaseModel):
    """Model for individual thinking skill information"""
    skill_name: str = Field(..., description="Name of the thinking skill")
    skill_code: str = Field(..., description="Skill code identifier")
    score: int = Field(..., ge=0, le=100, description="Individual score for this skill")
    percentile: float = Field(..., ge=0, le=100, description="Percentile ranking")
    description: str = Field(..., description="Description of what this skill measures")
    strength_level: str = Field(..., description="Strength level (e.g., 상, 중, 하)")


class ThinkingSkillsContent(BaseModel):
    """Content structure for thinking skills documents"""
    cognitive_abilities: List[ThinkingSkillInfo] = Field(..., min_length=8, max_length=8, description="8 cognitive abilities")
    overall_iq_score: Optional[int] = Field(None, ge=0, le=200, description="Overall IQ score")
    overall_percentile: Optional[float] = Field(None, ge=0, le=100, description="Overall percentile")
    strengths: List[str] = Field(..., description="List of cognitive strengths")
    areas_for_improvement: List[str] = Field(..., description="Areas needing improvement")
    analysis_summary: str = Field(..., description="Overall analysis summary")
    
    @field_validator('cognitive_abilities')
    @classmethod
    def validate_eight_abilities(cls, v):
        if len(v) != 8:
            raise ValueError("Must have exactly 8 cognitive abilities")
        return v


class CareerRecommendation(BaseModel):
    """Model for individual career recommendation"""
    job_name: str = Field(..., description="Recommended job name")
    job_code: str = Field(..., description="Job code identifier")
    match_percentage: float = Field(..., ge=0, le=100, description="Match percentage with user profile")
    reasoning: str = Field(..., description="Explanation for why this career is recommended")
    required_skills: List[str] = Field(..., description="Skills required for this career")
    personality_fit: str = Field(..., description="How personality fits this career")
    growth_potential: str = Field(..., description="Career growth potential")


class CareerRecommendationsContent(BaseModel):
    """Content structure for career recommendations documents"""
    top_recommendations: List[CareerRecommendation] = Field(..., min_length=5, max_length=10, description="Top career recommendations")
    career_clusters: Dict[str, List[str]] = Field(..., description="Career clusters and related jobs")
    personality_career_mapping: Dict[str, str] = Field(..., description="Mapping of personality traits to career aspects")
    industry_preferences: List[str] = Field(..., description="Preferred industries based on profile")
    work_environment_preferences: List[str] = Field(..., description="Preferred work environments")
    recommendations_summary: str = Field(..., description="Overall career recommendations summary")


class LearningStyleContent(BaseModel):
    """Content structure for learning style documents"""
    primary_learning_style: str = Field(..., description="Primary learning style")
    secondary_learning_style: str = Field(..., description="Secondary learning style")
    study_methods: List[str] = Field(..., description="Recommended study methods")
    academic_subjects: Dict[str, str] = Field(..., description="Recommended academic subjects with explanations")
    learning_preferences: Dict[str, str] = Field(..., description="Learning preferences and explanations")
    study_environment: str = Field(..., description="Optimal study environment")
    motivation_factors: List[str] = Field(..., description="Key motivation factors for learning")


class CompetencyInfo(BaseModel):
    """Model for individual competency information"""
    competency_name: str = Field(..., description="Name of the competency")
    competency_code: str = Field(..., description="Competency code identifier")
    score: int = Field(..., ge=0, le=100, description="Competency score")
    percentile: float = Field(..., ge=0, le=100, description="Percentile ranking")
    description: str = Field(..., description="Description of the competency")
    development_suggestions: List[str] = Field(..., description="Suggestions for developing this competency")


class CompetencyAnalysisContent(BaseModel):
    """Content structure for competency analysis documents"""
    top_competencies: List[CompetencyInfo] = Field(..., min_length=5, max_length=5, description="Top 5 competencies")
    competency_profile: Dict[str, Any] = Field(..., description="Overall competency profile")
    development_priorities: List[str] = Field(..., description="Priority areas for development")
    competency_gaps: List[str] = Field(..., description="Identified competency gaps")
    action_plan: List[str] = Field(..., description="Action plan for competency development")


class PreferenceAnalysisContent(BaseModel):
    """Content structure for preference analysis documents"""
    image_preferences: Dict[str, Any] = Field(..., description="Image preference test results")
    preference_patterns: List[str] = Field(..., description="Identified preference patterns")
    related_careers: List[str] = Field(..., description="Careers related to preferences")
    personality_insights: List[str] = Field(..., description="Personality insights from preferences")
    aesthetic_preferences: Dict[str, str] = Field(..., description="Aesthetic preferences and meanings")


# Main document models
class ChatDocument(BaseModel):
    """Main document model with content validation"""
    user_id: UUID = Field(..., description="User identifier")
    doc_type: DocumentType = Field(..., description="Type of document")
    content: Union[
        PersonalityProfileContent,
        ThinkingSkillsContent,
        CareerRecommendationsContent,
        LearningStyleContent,
        CompetencyAnalysisContent,
        PreferenceAnalysisContent
    ] = Field(..., description="Document content based on type")
    summary_text: str = Field(..., min_length=10, description="Summary text for embedding and search")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @model_validator(mode='after')
    def validate_content_type(self):
        """Validate that content matches document type"""
        doc_type = self.doc_type
        content = self.content
        
        if not doc_type or not content:
            return self
            
        type_mapping = {
            DocumentType.PERSONALITY_PROFILE: PersonalityProfileContent,
            DocumentType.THINKING_SKILLS: ThinkingSkillsContent,
            DocumentType.CAREER_RECOMMENDATIONS: CareerRecommendationsContent,
            DocumentType.LEARNING_STYLE: LearningStyleContent,
            DocumentType.COMPETENCY_ANALYSIS: CompetencyAnalysisContent,
            DocumentType.PREFERENCE_ANALYSIS: PreferenceAnalysisContent,
        }
        
        expected_type = type_mapping.get(doc_type)
        if expected_type and not isinstance(content, expected_type):
            raise ValueError(f"Content type {type(content)} does not match document type {doc_type}")
            
        return self

    model_config = ConfigDict(use_enum_values=True)


# API request/response models
class ChatDocumentCreate(BaseModel):
    """Model for creating new chat documents"""
    user_id: UUID
    doc_type: DocumentType
    content: Dict[str, Any]
    summary_text: str = Field(..., min_length=10)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatDocumentResponse(BaseModel):
    """Model for chat document API responses"""
    doc_id: UUID
    user_id: UUID
    doc_type: DocumentType
    content: Dict[str, Any]
    summary_text: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProcessingResult(BaseModel):
    """Model for ETL processing results"""
    user_id: UUID
    status: ProcessingStatus
    documents_created: int = Field(default=0, ge=0)
    documents_failed: int = Field(default=0, ge=0)
    error_messages: List[str] = Field(default_factory=list)
    processing_time_seconds: Optional[float] = Field(None, ge=0)
    created_at: datetime = Field(default_factory=datetime.now)


# User models
class ChatUserCreate(BaseModel):
    """Model for creating new chat users"""
    anp_seq: int = Field(..., gt=0, description="ANP sequence number")
    name: str = Field(..., min_length=1, max_length=100, description="User name")
    email: Optional[str] = Field(None, max_length=255, description="User email")
    test_completed_at: datetime = Field(..., description="Test completion timestamp")


class ChatUserResponse(BaseModel):
    """Model for chat user API responses"""
    user_id: UUID
    anp_seq: int
    name: str
    email: Optional[str]
    test_completed_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Conversation models
class ChatConversationCreate(BaseModel):
    """Model for creating new conversations"""
    user_id: UUID
    question: str = Field(..., min_length=1, description="User question")
    response: str = Field(..., min_length=1, description="System response")
    retrieved_doc_ids: List[UUID] = Field(default_factory=list, description="IDs of documents used for response")


class ChatConversationResponse(BaseModel):
    """Model for conversation API responses"""
    conversation_id: UUID
    user_id: UUID
    question: str
    response: str
    retrieved_doc_ids: List[UUID]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Job and Major models
class ChatJobCreate(BaseModel):
    """Model for creating job entries"""
    job_code: str = Field(..., max_length=20, description="Job code")
    job_name: str = Field(..., max_length=200, description="Job name")
    job_outline: Optional[str] = Field(None, description="Job outline")
    main_business: Optional[str] = Field(None, description="Main business description")


class ChatJobResponse(BaseModel):
    """Model for job API responses"""
    job_id: UUID
    job_code: str
    job_name: str
    job_outline: Optional[str]
    main_business: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatMajorCreate(BaseModel):
    """Model for creating major entries"""
    major_code: str = Field(..., max_length=20, description="Major code")
    major_name: str = Field(..., max_length=200, description="Major name")
    description: Optional[str] = Field(None, description="Major description")


class ChatMajorResponse(BaseModel):
    """Model for major API responses"""
    major_id: UUID
    major_code: str
    major_name: str
    description: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)