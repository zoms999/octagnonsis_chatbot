"""
Tests for document repository and vector search functionality
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from uuid import uuid4
from typing import List

from database.connection import DatabaseManager, get_async_session
from database.models import ChatUser, ChatDocument, DocumentType
from database.repositories import DocumentRepository, get_document_repository
from database.vector_search import VectorSearchService, SearchQuery, SimilarityMetric
from database.schemas import ChatDocumentCreate, ProcessingStatus


@pytest_asyncio.fixture
async def db_session():
    """Create test database session"""
    db_manager = DatabaseManager()
    async with db_manager.get_async_session() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create test user"""
    user = ChatUser(
        anp_seq=12345,
        name="Test User",
        email="test@example.com",
        test_completed_at=datetime.utcnow()
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
def sample_embedding():
    """Create sample 768-dimensional embedding vector"""
    return [0.1] * 768


def create_sample_document_data(user_id):
    """Create sample document data"""
    return ChatDocumentCreate(
        user_id=user_id,
        doc_type=DocumentType.PERSONALITY_PROFILE,
        content={
            "primary_tendency": {
                "name": "창의형",
                "code": "tnd12000",
                "explanation": "새로운 아이디어를 창출하고 혁신적인 해결책을 제시합니다.",
                "rank": 1,
                "percentage_in_total": 15.2,
                "score": 85
            },
            "secondary_tendency": {
                "name": "분석형", 
                "code": "tnd21000",
                "explanation": "논리적 사고를 통해 문제를 체계적으로 분석합니다.",
                "rank": 2,
                "percentage_in_total": 12.8,
                "score": 78
            },
            "top_tendencies": [
                {"rank": 1, "name": "창의형", "score": 85},
                {"rank": 2, "name": "분석형", "score": 78},
                {"rank": 3, "name": "탐구형", "score": 72}
            ],
            "bottom_tendencies": [
                {"rank": 23, "name": "안정형", "score": 32},
                {"rank": 24, "name": "보수형", "score": 28},
                {"rank": 25, "name": "수동형", "score": 25}
            ],
            "overall_summary": "창의적이고 분석적인 성향을 가진 사용자입니다."
        },
        summary_text="사용자는 창의형과 분석형 성향이 강하며, 새로운 아이디어 창출과 논리적 분석에 뛰어납니다.",
        metadata={"test": True}
    )


class TestDocumentRepository:
    """Test cases for DocumentRepository"""
    
    @pytest.mark.asyncio
    async def test_create_document(self, db_session, test_user, sample_embedding):
        """Test document creation"""
        repo = await get_document_repository(db_session)
        sample_document_data = create_sample_document_data(test_user.user_id)
        
        document = await repo.create_document(sample_document_data, sample_embedding)
        
        assert document.doc_id is not None
        assert document.user_id == test_user.user_id
        assert document.doc_type == DocumentType.PERSONALITY_PROFILE
        assert document.content == sample_document_data.content
        assert document.summary_text == sample_document_data.summary_text
        assert len(document.embedding_vector) == 768
        assert document.doc_metadata == {"test": True}
    
    @pytest.mark.asyncio
    async def test_get_document_by_id(self, db_session, test_user, sample_embedding):
        """Test document retrieval by ID"""
        repo = await get_document_repository(db_session)
        sample_document_data = create_sample_document_data(test_user.user_id)
        
        # Create document
        created_doc = await repo.create_document(sample_document_data, sample_embedding)
        await db_session.commit()
        
        # Retrieve document
        retrieved_doc = await repo.get_document_by_id(created_doc.doc_id)
        
        assert retrieved_doc is not None
        assert retrieved_doc.doc_id == created_doc.doc_id
        assert retrieved_doc.user_id == test_user.user_id
        assert retrieved_doc.doc_type == DocumentType.PERSONALITY_PROFILE
    
    @pytest.mark.asyncio
    async def test_get_documents_by_user(self, db_session, test_user, sample_embedding):
        """Test retrieving documents by user"""
        repo = await get_document_repository(db_session)
        
        # Create multiple documents
        doc_data_1 = ChatDocumentCreate(
            user_id=test_user.user_id,
            doc_type=DocumentType.PERSONALITY_PROFILE,
            content={"test": "data1"},
            summary_text="Test document 1 for personality profile analysis"
        )
        
        doc_data_2 = ChatDocumentCreate(
            user_id=test_user.user_id,
            doc_type=DocumentType.THINKING_SKILLS,
            content={"cognitive_abilities": [{"skill": "test"} for _ in range(8)]},
            summary_text="Test document 2 for thinking skills analysis"
        )
        
        await repo.create_document(doc_data_1, sample_embedding)
        await repo.create_document(doc_data_2, sample_embedding)
        await db_session.commit()
        
        # Retrieve all documents
        all_docs = await repo.get_documents_by_user(test_user.user_id)
        assert len(all_docs) == 2
        
        # Retrieve filtered documents
        personality_docs = await repo.get_documents_by_user(
            test_user.user_id, 
            doc_type=DocumentType.PERSONALITY_PROFILE
        )
        assert len(personality_docs) == 1
        assert personality_docs[0].doc_type == DocumentType.PERSONALITY_PROFILE
    
    async def test_update_document(self, db_session, test_user, sample_document_data, sample_embedding):
        """Test document update with versioning"""
        repo = await get_document_repository(db_session)
        
        # Create document
        document = await repo.create_document(sample_document_data, sample_embedding)
        await db_session.commit()
        
        # Update document
        new_content = {"updated": "content"}
        new_summary = "Updated summary text for testing purposes"
        
        updated_doc = await repo.update_document(
            document.doc_id,
            content=new_content,
            summary_text=new_summary
        )
        
        assert updated_doc is not None
        assert updated_doc.content == new_content
        assert updated_doc.summary_text == new_summary
        assert "previous_version" in updated_doc.doc_metadata
        assert "version_count" in updated_doc.doc_metadata
        assert updated_doc.doc_metadata["version_count"] == 1
    
    async def test_delete_document(self, db_session, test_user, sample_document_data, sample_embedding):
        """Test document deletion"""
        repo = await get_document_repository(db_session)
        
        # Create document
        document = await repo.create_document(sample_document_data, sample_embedding)
        await db_session.commit()
        
        # Delete document
        deleted = await repo.delete_document(document.doc_id)
        assert deleted is True
        
        # Verify deletion
        retrieved_doc = await repo.get_document_by_id(document.doc_id)
        assert retrieved_doc is None
    
    async def test_batch_create_documents(self, db_session, test_user, sample_embedding):
        """Test batch document creation"""
        repo = await get_document_repository(db_session)
        
        # Prepare batch data
        batch_data = []
        for i in range(3):
            doc_data = ChatDocumentCreate(
                user_id=test_user.user_id,
                doc_type=DocumentType.PERSONALITY_PROFILE,
                content={"batch_test": f"document_{i}"},
                summary_text=f"Batch test document {i} for testing batch creation functionality"
            )
            batch_data.append((doc_data, sample_embedding))
        
        # Batch create
        result = await repo.batch_create_documents(batch_data)
        
        assert result.status == ProcessingStatus.COMPLETED
        assert result.documents_created == 3
        assert result.documents_failed == 0
        assert len(result.error_messages) == 0
        
        # Verify documents were created
        docs = await repo.get_documents_by_user(test_user.user_id)
        assert len(docs) == 3
    
    async def test_document_count_and_types(self, db_session, test_user, sample_embedding):
        """Test document counting and type listing"""
        repo = await get_document_repository(db_session)
        
        # Create documents of different types
        doc_types = [DocumentType.PERSONALITY_PROFILE, DocumentType.THINKING_SKILLS, DocumentType.CAREER_RECOMMENDATIONS]
        
        for doc_type in doc_types:
            doc_data = ChatDocumentCreate(
                user_id=test_user.user_id,
                doc_type=doc_type,
                content={"type": doc_type},
                summary_text=f"Test document for {doc_type} analysis and validation"
            )
            await repo.create_document(doc_data, sample_embedding)
        
        await db_session.commit()
        
        # Test count
        count = await repo.get_document_count_by_user(test_user.user_id)
        assert count == 3
        
        # Test types
        types = await repo.get_document_types_by_user(test_user.user_id)
        assert len(types) == 3
        assert set(types) == set(doc_types)
        
        # Test existence check
        exists = await repo.check_document_exists(test_user.user_id, DocumentType.PERSONALITY_PROFILE)
        assert exists is True
        
        not_exists = await repo.check_document_exists(test_user.user_id, DocumentType.LEARNING_STYLE)
        assert not_exists is False


class TestVectorSearchService:
    """Test cases for VectorSearchService"""
    
    async def test_similarity_search(self, db_session, test_user, sample_embedding):
        """Test basic similarity search"""
        # Create test documents
        repo = await get_document_repository(db_session)
        search_service = VectorSearchService(db_session)
        
        # Create documents with different embeddings
        embeddings = [
            [0.1] * 768,  # Similar to query
            [0.9] * 768,  # Different from query
            [0.2] * 768   # Somewhat similar to query
        ]
        
        for i, embedding in enumerate(embeddings):
            doc_data = ChatDocumentCreate(
                user_id=test_user.user_id,
                doc_type=DocumentType.PERSONALITY_PROFILE,
                content={"test": f"document_{i}"},
                summary_text=f"Test document {i} for similarity search testing and validation"
            )
            await repo.create_document(doc_data, embedding)
        
        await db_session.commit()
        
        # Perform search
        query = SearchQuery(
            user_id=test_user.user_id,
            query_vector=[0.15] * 768,  # Close to first document
            limit=3,
            similarity_threshold=0.5
        )
        
        results = await search_service.similarity_search(query)
        
        assert len(results) > 0
        assert all(r.similarity_score >= 0.5 for r in results)
        assert results[0].similarity_score >= results[-1].similarity_score  # Sorted by similarity
    
    async def test_search_by_document_type(self, db_session, test_user, sample_embedding):
        """Test search filtered by document type"""
        repo = await get_document_repository(db_session)
        search_service = VectorSearchService(db_session)
        
        # Create documents of different types
        doc_types = [DocumentType.PERSONALITY_PROFILE, DocumentType.THINKING_SKILLS]
        
        for doc_type in doc_types:
            doc_data = ChatDocumentCreate(
                user_id=test_user.user_id,
                doc_type=doc_type,
                content={"type": doc_type},
                summary_text=f"Test document for {doc_type} type filtering and search"
            )
            await repo.create_document(doc_data, sample_embedding)
        
        await db_session.commit()
        
        # Search for specific type
        results = await search_service.search_by_document_type(
            test_user.user_id,
            sample_embedding,
            DocumentType.PERSONALITY_PROFILE
        )
        
        assert len(results) == 1
        assert results[0].document.doc_type == DocumentType.PERSONALITY_PROFILE
    
    async def test_multi_type_search(self, db_session, test_user, sample_embedding):
        """Test search across multiple document types"""
        repo = await get_document_repository(db_session)
        search_service = VectorSearchService(db_session)
        
        # Create documents of different types
        doc_types = [DocumentType.PERSONALITY_PROFILE, DocumentType.THINKING_SKILLS, DocumentType.CAREER_RECOMMENDATIONS]
        
        for doc_type in doc_types:
            for i in range(2):  # 2 documents per type
                doc_data = ChatDocumentCreate(
                    user_id=test_user.user_id,
                    doc_type=doc_type,
                    content={"type": doc_type, "index": i},
                    summary_text=f"Test document {i} for {doc_type} multi-type search testing"
                )
                await repo.create_document(doc_data, sample_embedding)
        
        await db_session.commit()
        
        # Multi-type search
        results = await search_service.multi_type_search(
            test_user.user_id,
            sample_embedding,
            doc_types,
            limit_per_type=1
        )
        
        assert len(results) == 3
        for doc_type in doc_types:
            assert doc_type in results
            assert len(results[doc_type]) == 1
    
    async def test_get_similar_documents(self, db_session, test_user, sample_embedding):
        """Test finding similar documents"""
        repo = await get_document_repository(db_session)
        search_service = VectorSearchService(db_session)
        
        # Create source document
        source_doc_data = ChatDocumentCreate(
            user_id=test_user.user_id,
            doc_type=DocumentType.PERSONALITY_PROFILE,
            content={"source": True},
            summary_text="Source document for similarity testing and validation"
        )
        source_doc = await repo.create_document(source_doc_data, sample_embedding)
        
        # Create similar documents
        for i in range(3):
            similar_embedding = [0.1 + (i * 0.01)] * 768  # Slightly different
            doc_data = ChatDocumentCreate(
                user_id=test_user.user_id,
                doc_type=DocumentType.THINKING_SKILLS,
                content={"similar": i},
                summary_text=f"Similar document {i} for testing document similarity search"
            )
            await repo.create_document(doc_data, similar_embedding)
        
        await db_session.commit()
        
        # Find similar documents
        results = await search_service.get_similar_documents(source_doc.doc_id, limit=3)
        
        assert len(results) <= 3
        for result in results:
            assert result.document.doc_id != source_doc.doc_id
            assert result.similarity_score > 0.5
    
    async def test_search_performance_metrics(self, db_session, test_user, sample_embedding):
        """Test search performance monitoring"""
        repo = await get_document_repository(db_session)
        search_service = VectorSearchService(db_session)
        
        # Create test document
        doc_data = ChatDocumentCreate(
            user_id=test_user.user_id,
            doc_type=DocumentType.PERSONALITY_PROFILE,
            content={"performance": "test"},
            summary_text="Performance test document for monitoring search metrics"
        )
        await repo.create_document(doc_data, sample_embedding)
        await db_session.commit()
        
        # Perform search to generate metrics
        query = SearchQuery(
            user_id=test_user.user_id,
            query_vector=sample_embedding,
            limit=5
        )
        await search_service.similarity_search(query)
        
        # Check metrics
        metrics = await search_service.get_search_performance_metrics(user_id=test_user.user_id)
        
        assert len(metrics) == 1
        assert metrics[0].user_id == test_user.user_id
        assert metrics[0].query_time_ms > 0
        assert metrics[0].results_returned >= 0
    
    async def test_optimize_search_performance(self, db_session, test_user, sample_embedding):
        """Test search performance optimization analysis"""
        search_service = VectorSearchService(db_session)
        
        # Generate some performance data
        search_service._performance_metrics = [
            search_service.SearchPerformanceMetrics(
                query_time_ms=100.0,
                total_documents_searched=10,
                results_returned=5,
                similarity_threshold=0.7,
                search_timestamp=datetime.utcnow(),
                user_id=test_user.user_id
            )
        ]
        
        # Get optimization recommendations
        analysis = await search_service.optimize_search_performance()
        
        assert "performance_summary" in analysis
        assert "recommendations" in analysis
        assert "analysis_timestamp" in analysis
        assert analysis["performance_summary"]["average_query_time_ms"] == 100.0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])