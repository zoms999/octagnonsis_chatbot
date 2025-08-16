"""
Repository layer for document storage and retrieval operations
Implements CRUD operations, batch processing, versioning, and data integrity validation
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
import uuid
from uuid import UUID

from sqlalchemy import select, update, delete, func, and_, or_
# [수정] PostgreSQL의 UPSERT 기능을 사용하기 위해 sqlalchemy.dialects.postgresql에서 insert를 임포트합니다.
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload
from pgvector.sqlalchemy import Vector

from database.models import ChatDocument, ChatUser, DocumentType
from database.cache import DocumentCache
from database.schemas import ChatDocumentCreate, ChatDocumentResponse, ProcessingResult, ProcessingStatus
from database.connection import get_async_session

# TransformedDocument import 추가
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from etl.document_transformer import TransformedDocument

logger = logging.getLogger(__name__)


class DocumentRepositoryError(Exception):
    """Custom exception for document repository operations"""
    pass


class DocumentRepository:
    """Repository for chat document operations with CRUD, batch processing, and versioning"""
    
    def __init__(self, session: AsyncSession, document_cache: Optional[DocumentCache] = None):
        self.session = session
        # Shared application-level cache (can be injected)
        self.cache = document_cache or DocumentRepository.get_global_cache()

    _global_cache: Optional[DocumentCache] = None

    @staticmethod
    def get_global_cache() -> DocumentCache:
        if DocumentRepository._global_cache is None:
            # Default: 5000 entries, 1 hour TTL
            DocumentRepository._global_cache = DocumentCache(capacity=5000, ttl_seconds=3600)
        return DocumentRepository._global_cache
    
    async def create_document(
        self, 
        document_data: ChatDocumentCreate,
        embedding_vector: List[float]
    ) -> ChatDocument:
        """
        Create a new document with validation and integrity checks
        """
        try:
            # Validate document type
            if not DocumentType.is_valid(document_data.doc_type):
                raise DocumentRepositoryError(f"Invalid document type: {document_data.doc_type}")
            
            # Validate embedding vector
            if not embedding_vector or len(embedding_vector) != 768:
                raise DocumentRepositoryError("Embedding vector must be 768-dimensional")
            
            # Validate user exists
            user_exists = await self._check_user_exists(document_data.user_id)
            if not user_exists:
                raise DocumentRepositoryError(f"User {document_data.user_id} does not exist")
            
            # Create document instance
            document = ChatDocument(
                user_id=document_data.user_id,
                doc_type=document_data.doc_type,
                content=document_data.content,
                summary_text=document_data.summary_text,
                embedding_vector=embedding_vector,
                doc_metadata=document_data.metadata or {}
            )
            
            # Validate content structure
            await self._validate_document_content(document)
            
            self.session.add(document)
            await self.session.flush()
            
            logger.info(f"Created document {document.doc_id} for user {document.user_id}")
            if self.cache and document.doc_id:
                await self.cache.invalidate_document(str(document.doc_id))
            return document
            
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Integrity error creating document: {e}")
            raise DocumentRepositoryError(f"Database integrity error: {str(e)}")
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Database error creating document: {e}")
            raise DocumentRepositoryError(f"Database error: {str(e)}")
    
    async def get_document_by_id(self, doc_id: UUID) -> Optional[ChatDocument]:
        """
        Retrieve a document by its ID
        """
        try:
            if self.cache:
                cached = await self.cache.get_document(str(doc_id))
                if cached is not None:
                    return cached
            stmt = select(ChatDocument).where(ChatDocument.doc_id == doc_id)
            result = await self.session.execute(stmt)
            doc = result.scalar_one_or_none()
            if doc and self.cache:
                await self.cache.set_document(str(doc_id), doc)
            return doc
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving document {doc_id}: {e}")
            raise DocumentRepositoryError(f"Error retrieving document: {str(e)}")
    
    async def get_documents_by_user(
        self, 
        user_id: UUID, 
        doc_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[ChatDocument]:
        """
        Retrieve documents for a specific user with optional filtering
        """
        try:
            stmt = select(ChatDocument).where(ChatDocument.user_id == user_id)
            
            if doc_type:
                stmt = stmt.where(ChatDocument.doc_type == doc_type)
            
            stmt = stmt.order_by(ChatDocument.created_at.desc())
            
            if offset:
                stmt = stmt.offset(offset)
            if limit:
                stmt = stmt.limit(limit)
            
            result = await self.session.execute(stmt)
            return result.scalars().all()
            
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving documents for user {user_id}: {e}")
            raise DocumentRepositoryError(f"Error retrieving documents: {str(e)}")
    
    async def update_document(
        self, 
        doc_id: UUID, 
        content: Optional[Dict[str, Any]] = None,
        summary_text: Optional[str] = None,
        embedding_vector: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[ChatDocument]:
        """
        Update an existing document with versioning support
        """
        try:
            document = await self.get_document_by_id(doc_id)
            if not document:
                return None
            
            version_info = {
                'previous_version': {
                    'content': document.content,
                    'summary_text': document.summary_text,
                    'updated_at': document.updated_at.isoformat()
                },
                'version_count': document.doc_metadata.get('version_count', 0) + 1
            }
            
            update_data = {'updated_at': datetime.utcnow()}
            
            if content is not None:
                update_data['content'] = content
            if summary_text is not None:
                update_data['summary_text'] = summary_text
            if embedding_vector is not None:
                if len(embedding_vector) != 768:
                    raise DocumentRepositoryError("Embedding vector must be 768-dimensional")
                update_data['embedding_vector'] = embedding_vector
            if metadata is not None:
                merged_metadata = {**metadata, **version_info}
                update_data['doc_metadata'] = merged_metadata
            else:
                merged_metadata = {**document.doc_metadata, **version_info}
                update_data['doc_metadata'] = merged_metadata
            
            stmt = update(ChatDocument).where(ChatDocument.doc_id == doc_id).values(**update_data)
            await self.session.execute(stmt)
            
            updated = await self.get_document_by_id(doc_id)
            if self.cache:
                await self.cache.invalidate_document(str(doc_id))
                if updated:
                    await self.cache.set_document(str(doc_id), updated)
            return updated
            
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Error updating document {doc_id}: {e}")
            raise DocumentRepositoryError(f"Error updating document: {str(e)}")
    
    async def delete_document(self, doc_id: UUID) -> bool:
        """
        Delete a document by ID
        """
        try:
            stmt = delete(ChatDocument).where(ChatDocument.doc_id == doc_id)
            result = await self.session.execute(stmt)
            
            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"Deleted document {doc_id}")
                if self.cache:
                    await self.cache.invalidate_document(str(doc_id))
            
            return deleted
            
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Error deleting document {doc_id}: {e}")
            raise DocumentRepositoryError(f"Error deleting document: {str(e)}")

    async def upsert(self, document_data: Dict[str, Any]) -> None:
        """
        청킹 전략에 맞게 문서를 저장합니다.
        기존 UPSERT 대신 단순 INSERT를 사용합니다.
        """
        try:
            # 단순 INSERT 방식으로 변경 (청킹된 문서들은 모두 새로운 문서로 처리)
            document = ChatDocument(
                user_id=document_data['user_id'],
                doc_type=document_data['doc_type'],
                content=document_data['content'],
                summary_text=document_data['summary_text'],
                embedding_vector=document_data['embedding_vector'],
                doc_metadata=document_data.get('doc_metadata', {})
            )
            
            self.session.add(document)
            await self.session.flush()
            logger.info(f"Document inserted successfully for user_id={document_data.get('user_id')}, doc_type={document_data.get('doc_type')}")
            
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Insert failed for (user_id={document_data.get('user_id')}, doc_type={document_data.get('doc_type')}): {e}")
            raise DocumentRepositoryError(f"Insert error: {str(e)}")

    # Compatibility/alias methods used by ETL orchestrator and tasks
    async def create(self, document: ChatDocument) -> ChatDocument:
        """Alias for creating a ChatDocument instance directly (used by ETL orchestrator)."""
        try:
            if not DocumentType.is_valid(document.doc_type):
                raise DocumentRepositoryError(f"Invalid document type: {document.doc_type}")
            if not document.embedding_vector or len(document.embedding_vector) != 768:
                raise DocumentRepositoryError("Embedding vector must be 768-dimensional")
            if not await self._check_user_exists(document.user_id):
                raise DocumentRepositoryError(f"User {document.user_id} does not exist")

            self.session.add(document)
            await self.session.flush()
            if self.cache and document.doc_id:
                await self.cache.invalidate_document(str(document.doc_id))
            return document
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Database error creating document (alias): {e}")
            raise DocumentRepositoryError(f"Database error: {str(e)}")

    async def delete(self, doc_id: UUID | str) -> bool:
        """Alias to delete document by id (used by ETL orchestrator rollback)."""
        try:
            if isinstance(doc_id, str):
                doc_id = UUID(doc_id)
            return await self.delete_document(doc_id)
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            raise

    async def get_by_user_id(self, user_id: UUID) -> List[ChatDocument]:
        """Alias to get documents by user (used in tasks)."""
        return await self.get_documents_by_user(user_id)
    
    # ... (Other methods like batch_create, get_count, etc. can be kept as is) ...
    async def get_document_count_by_user(self, user_id: UUID) -> int:
        """
        Get total document count for a user
        """
        try:
            stmt = select(func.count(ChatDocument.doc_id)).where(ChatDocument.user_id == user_id)
            result = await self.session.execute(stmt)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting documents for user {user_id}: {e}")
            raise DocumentRepositoryError(f"Error counting documents: {str(e)}")
            
    # Private helper methods
    async def _check_user_exists(self, user_id: UUID) -> bool:
        """Check if user exists in database"""
        try:
            stmt = select(func.count(ChatUser.user_id)).where(ChatUser.user_id == user_id)
            result = await self.session.execute(stmt)
            return (result.scalar() or 0) > 0
        except SQLAlchemyError:
            return False
    
    async def _validate_document_content(self, document: ChatDocument) -> None:
        """Validate document content structure based on doc_type"""
        if not document.content:
            raise DocumentRepositoryError("Document content cannot be empty")
        
        if not document.summary_text or len(document.summary_text.strip()) < 10:
            raise DocumentRepositoryError("Summary text must be at least 10 characters")
        
        doc_type = document.doc_type
        content = document.content
        
        if doc_type == DocumentType.PERSONALITY_PROFILE:
            required_fields = ['primary_tendency', 'secondary_tendency', 'top_tendencies']
            for field in required_fields:
                if field not in content:
                    raise DocumentRepositoryError(f"Missing required field '{field}' for personality profile")
        
        elif doc_type == DocumentType.THINKING_SKILLS:
            # [확인] 요청하신 대로 'core_thinking_skills'로 검증 필드를 수정했습니다.
            if 'core_thinking_skills' not in content:
                raise DocumentRepositoryError("Missing 'core_thinking_skills' field for thinking skills document")
            if not isinstance(content['core_thinking_skills'], list):
                raise DocumentRepositoryError("Thinking skills must have a list of core skills")
        
        elif doc_type == DocumentType.CAREER_RECOMMENDATIONS:
            # [확인] 요청하신 대로 'recommended_careers'로 검증 필드를 수정하고, 최소 1개 이상을 확인합니다.
            if 'recommended_careers' not in content:
                raise DocumentRepositoryError("Missing 'recommended_careers' field for career recommendations")
            if not isinstance(content['recommended_careers'], list) or len(content['recommended_careers']) < 1:
                raise DocumentRepositoryError("Career recommendations must have at least 1 recommendation")

class UserRepository:
    """Repository for user operations (used by ETL orchestrator and tasks)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: UUID | str) -> Optional[ChatUser]:
        try:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            stmt = select(ChatUser).where(ChatUser.user_id == user_id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving user {user_id}: {e}")
            return None

    async def get_by_anp_seq(self, anp_seq: int) -> Optional[ChatUser]:
        try:
            stmt = select(ChatUser).where(ChatUser.anp_seq == anp_seq)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving user by anp_seq {anp_seq}: {e}")
            return None

    async def create(self, user: ChatUser) -> ChatUser:
        try:
            self.session.add(user)
            await self.session.flush()
            return user
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Error creating user: {e}")
            raise

    async def delete(self, user_id: UUID | str) -> bool:
        try:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            stmt = delete(ChatUser).where(ChatUser.user_id == user_id)
            result = await self.session.execute(stmt)
            return result.rowcount > 0
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Error deleting user {user_id}: {e}")
            raise


async def save_chunked_documents(session: AsyncSession, user_id: str, documents: List['TransformedDocument']):
    """
    특정 사용자의 기존 문서를 모두 삭제한 후, 새로 청킹된 문서들을 삽입합니다.
    """
    from etl.document_transformer import TransformedDocument  # 런타임 import로 순환 참조 방지
    
    try:
        # 1. [선 삭제] 이 ETL 작업으로 생성될 사용자의 기존 문서를 모두 삭제
        logger.info(f"Deleting existing documents for user_id: {user_id}")
        delete_statement = delete(ChatDocument).where(ChatDocument.user_id == user_id)
        await session.execute(delete_statement)
        
        # 2. [후 삽입] 새로 생성된 문서들을 모두 INSERT
        logger.info(f"Inserting {len(documents)} new chunked documents for user_id: {user_id}")
        new_db_documents = []
        
        for doc in documents:
            # embedding_vector가 None인 경우 임시 더미 벡터 사용 (768차원)
            embedding_vector = doc.embedding_vector
            if embedding_vector is None:
                # 768차원의 0으로 채워진 더미 벡터 생성
                embedding_vector = [0.0] * 768
                logger.warning(f"Using dummy embedding vector for document {doc.doc_type}")
            
            # TransformedDocument 객체를 DB 모델 객체로 변환
            new_db_documents.append(ChatDocument(
                user_id=UUID(user_id),  # str을 UUID로 변환
                doc_type=doc.doc_type,  # DocumentType enum 멤버를 사용
                content=doc.content,
                summary_text=doc.summary_text,
                embedding_vector=embedding_vector,  # 임베딩 단계에서 추가되어야 함
                doc_metadata=doc.metadata
            ))
        
        if new_db_documents:
            session.add_all(new_db_documents)
            await session.commit()
            logger.info("Successfully saved new documents.")
        else:
            logger.warning("No documents to save.")
            
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Error saving chunked documents for user {user_id}: {e}")
        raise DocumentRepositoryError(f"Error saving chunked documents: {str(e)}")
    except Exception as e:
        await session.rollback()
        logger.error(f"Unexpected error saving chunked documents for user {user_id}: {e}")
        raise DocumentRepositoryError(f"Unexpected error: {str(e)}")


async def get_document_repository(session: AsyncSession) -> DocumentRepository:
    """Factory function to create document repository with session"""
    return DocumentRepository(session)