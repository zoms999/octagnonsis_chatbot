"""
SQLAlchemy ORM models for Aptitude Chatbot RAG System
Defines database models for chat_users, chat_documents, chat_jobs, chat_majors, and chat_conversations
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid

from database.connection import Base

class ChatETLJob(Base):
    """Background ETL job tracking model"""
    __tablename__ = 'chat_etl_jobs'

    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('chat_users.user_id', ondelete='CASCADE'), nullable=False)
    anp_seq: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default='pending')
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0)  # store as integer percentage 0-100
    current_step: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    completed_steps: Mapped[int] = mapped_column(Integer, default=0)
    total_steps: Mapped[int] = mapped_column(Integer, default=7)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    failed_stage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    query_results_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    documents_created: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String(100)), nullable=True)

    # Relationship back to user
    user: Mapped["ChatUser"] = relationship("ChatUser")

    def __repr__(self):
        return f"<ChatETLJob(job_id={self.job_id}, user_id={self.user_id}, status='{self.status}', progress={self.progress_percentage})>"

class ChatUser(Base):
    """User model for chat system"""
    __tablename__ = 'chat_users'
    
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    anp_seq: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    test_completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    documents: Mapped[List["ChatDocument"]] = relationship("ChatDocument", back_populates="user", cascade="all, delete-orphan")
    conversations: Mapped[List["ChatConversation"]] = relationship("ChatConversation", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ChatUser(user_id={self.user_id}, anp_seq={self.anp_seq}, name='{self.name}')>"
    
    def get_documents_by_type(self, doc_type: str) -> List["ChatDocument"]:
        """Get all documents of a specific type for this user"""
        return [doc for doc in self.documents if doc.doc_type == doc_type]
    
    def has_document_type(self, doc_type: str) -> bool:
        """Check if user has any documents of the specified type"""
        return any(doc.doc_type == doc_type for doc in self.documents)
    
    def get_latest_conversation(self) -> Optional["ChatConversation"]:
        """Get the most recent conversation for this user"""
        if not self.conversations:
            return None
        return max(self.conversations, key=lambda c: c.created_at)

class ChatDocument(Base):
    """Document model with vector embeddings"""
    __tablename__ = 'chat_documents'
    
    doc_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('chat_users.user_id', ondelete='CASCADE'), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_vector: Mapped[List[float]] = mapped_column(Vector(768), nullable=False)
    doc_metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    user: Mapped["ChatUser"] = relationship("ChatUser", back_populates="documents")
    
    def __repr__(self):
        return f"<ChatDocument(doc_id={self.doc_id}, user_id={self.user_id}, doc_type='{self.doc_type}')>"
    
    def validate_doc_type(self) -> bool:
        """Validate that doc_type is one of the allowed types"""
        return DocumentType.is_valid(self.doc_type)
    
    def get_content_summary(self, max_length: int = 100) -> str:
        """Get a truncated summary of the document content"""
        if len(self.summary_text) <= max_length:
            return self.summary_text
        return self.summary_text[:max_length-3] + "..."
    
    def update_metadata(self, key: str, value: Any) -> None:
        """Update a specific metadata field"""
        if self.doc_metadata is None:
            self.doc_metadata = {}
        self.doc_metadata[key] = value

class ChatJob(Base):
    """Job information model with vector embeddings"""
    __tablename__ = 'chat_jobs'
    
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    job_name: Mapped[str] = mapped_column(String(200), nullable=False)
    job_outline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    main_business: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding_vector: Mapped[Optional[List[float]]] = mapped_column(Vector(768), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())
    
    def __repr__(self):
        return f"<ChatJob(job_id={self.job_id}, job_code='{self.job_code}', job_name='{self.job_name}')>"

class ChatMajor(Base):
    """Academic major information model with vector embeddings"""
    __tablename__ = 'chat_majors'
    
    major_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    major_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    major_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding_vector: Mapped[Optional[List[float]]] = mapped_column(Vector(768), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())
    
    def __repr__(self):
        return f"<ChatMajor(major_id={self.major_id}, major_code='{self.major_code}', major_name='{self.major_name}')>"

class ChatConversation(Base):
    """Conversation history model"""
    __tablename__ = 'chat_conversations'
    
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('chat_users.user_id', ondelete='CASCADE'), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_doc_ids: Mapped[List[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=[])
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())
    # Analytics fields
    confidence_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    quality_label: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    processing_time: Mapped[Optional[float]] = mapped_column(nullable=True)
    question_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    question_intent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ab_variant: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    prompt_template: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Relationships
    user: Mapped["ChatUser"] = relationship("ChatUser", back_populates="conversations")
    
    def __repr__(self):
        return f"<ChatConversation(conversation_id={self.conversation_id}, user_id={self.user_id})>"

class ChatFeedback(Base):
    """User feedback for conversations"""
    __tablename__ = 'chat_feedback'

    feedback_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('chat_conversations.conversation_id', ondelete='CASCADE'))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('chat_users.user_id', ondelete='CASCADE'))
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    helpful: Mapped[Optional[bool]] = mapped_column(nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String(50)), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())

# Document type enumeration for validation
class DocumentType(str, Enum):
    USER_PROFILE = "USER_PROFILE"
    PERSONALITY_PROFILE = "PERSONALITY_PROFILE"
    THINKING_SKILLS = "THINKING_SKILLS"
    CAREER_RECOMMENDATIONS = "CAREER_RECOMMENDATIONS"
    LEARNING_STYLE = "LEARNING_STYLE"
    COMPETENCY_ANALYSIS = "COMPETENCY_ANALYSIS"
    PREFERENCE_ANALYSIS = "PREFERENCE_ANALYSIS"
    
    @classmethod
    def all_types(cls) -> List[str]:
        return [item.value for item in cls]
    
    @classmethod
    def is_valid(cls, doc_type: str) -> bool:
        return any(doc_type == item.value for item in cls)


# Processing status enumeration
class ProcessingStatus:
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    
    @classmethod
    def all_statuses(cls) -> List[str]:
        return [cls.PENDING, cls.IN_PROGRESS, cls.COMPLETED, cls.FAILED, cls.PARTIAL]
    
    @classmethod
    def is_valid(cls, status: str) -> bool:
        return status in cls.all_statuses()