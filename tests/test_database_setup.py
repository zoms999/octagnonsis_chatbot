"""
Tests for database setup and core infrastructure
Verifies database connection, schema creation, and basic operations
"""

import pytest
import asyncio
import uuid
from datetime import datetime
from sqlalchemy import text
from database import (
    db_manager, 
    ChatUser, 
    ChatDocument, 
    DocumentType,
    get_async_session
)

class TestDatabaseSetup:
    """Test database setup and basic functionality"""
    
    @pytest.mark.asyncio
    async def test_database_connection(self):
        """Test that database connection works"""
        connected = await db_manager.test_connection()
        assert connected, "Database connection should be successful"
    
    @pytest.mark.asyncio
    async def test_pgvector_extension(self):
        """Test that pgvector extension is installed"""
        has_pgvector = await db_manager.check_pgvector_extension()
        assert has_pgvector, "pgvector extension should be installed"
    
    @pytest.mark.asyncio
    async def test_required_tables_exist(self):
        """Test that all required tables exist"""
        required_tables = [
            'chat_users',
            'chat_documents', 
            'chat_jobs',
            'chat_majors',
            'chat_conversations'
        ]
        
        async with db_manager.get_async_session() as session:
            for table in required_tables:
                result = await session.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    )
                """))
                
                exists = result.scalar()
                assert exists, f"Table '{table}' should exist"
    
    @pytest.mark.asyncio
    async def test_vector_indexes_exist(self):
        """Test that vector indexes are created"""
        expected_indexes = [
            'idx_chat_documents_embedding',
            'idx_chat_jobs_embedding',
            'idx_chat_majors_embedding'
        ]
        
        async with db_manager.get_async_session() as session:
            for index in expected_indexes:
                result = await session.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM pg_indexes 
                        WHERE indexname = '{index}'
                    )
                """))
                
                exists = result.scalar()
                assert exists, f"Vector index '{index}' should exist"
    
    @pytest.mark.asyncio
    async def test_create_user(self):
        """Test creating a user record"""
        async with db_manager.get_async_session() as session:
            # Create test user
            test_user = ChatUser(
                anp_seq=12345,
                name="Test User",
                email="test@example.com",
                test_completed_at=datetime.now()
            )
            
            session.add(test_user)
            await session.commit()
            
            # Verify user was created
            result = await session.execute(
                text("SELECT name FROM chat_users WHERE anp_seq = :anp_seq"),
                {"anp_seq": 12345}
            )
            
            user_name = result.scalar()
            assert user_name == "Test User"
            
            # Cleanup
            await session.execute(
                text("DELETE FROM chat_users WHERE anp_seq = :anp_seq"),
                {"anp_seq": 12345}
            )
            await session.commit()
    
    @pytest.mark.asyncio
    async def test_create_document_with_vector(self):
        """Test creating a document with vector embedding"""
        async with db_manager.get_async_session() as session:
            # Create test user first
            test_user = ChatUser(
                anp_seq=12346,
                name="Test User 2",
                test_completed_at=datetime.now()
            )
            session.add(test_user)
            await session.flush()  # Get user_id
            
            # Create test document with vector
            test_vector = [0.1] * 768  # 768-dimensional vector
            
            test_doc = ChatDocument(
                user_id=test_user.user_id,
                doc_type=DocumentType.PERSONALITY_PROFILE,
                content={"test": "data"},
                summary_text="Test document summary",
                embedding_vector=test_vector,
                doc_metadata={"source": "test"}
            )
            
            session.add(test_doc)
            await session.commit()
            
            # Verify document was created
            result = await session.execute(
                text("SELECT doc_type FROM chat_documents WHERE user_id = :user_id"),
                {"user_id": test_user.user_id}
            )
            
            doc_type = result.scalar()
            assert doc_type == DocumentType.PERSONALITY_PROFILE
            
            # Test vector similarity search
            result = await session.execute(text("""
                SELECT doc_id, embedding_vector <-> :query_vector as distance
                FROM chat_documents 
                WHERE user_id = :user_id
                ORDER BY embedding_vector <-> :query_vector
                LIMIT 1
            """), {
                "query_vector": test_vector,
                "user_id": test_user.user_id
            })
            
            row = result.fetchone()
            assert row is not None
            assert row.distance < 0.1  # Should be very similar
            
            # Cleanup
            await session.execute(
                text("DELETE FROM chat_users WHERE anp_seq = :anp_seq"),
                {"anp_seq": 12346}
            )
            await session.commit()
    
    @pytest.mark.asyncio
    async def test_document_type_validation(self):
        """Test document type validation"""
        valid_types = DocumentType.all_types()
        assert len(valid_types) == 6
        assert DocumentType.PERSONALITY_PROFILE in valid_types
        assert DocumentType.is_valid(DocumentType.THINKING_SKILLS)
        assert not DocumentType.is_valid("INVALID_TYPE")