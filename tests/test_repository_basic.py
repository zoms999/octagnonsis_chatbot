"""
Basic tests for document repository functionality
"""

import asyncio
from datetime import datetime
from uuid import uuid4

from database.connection import DatabaseManager
from database.models import ChatUser, ChatDocument, DocumentType
from database.repositories import DocumentRepository
from database.schemas import ChatDocumentCreate


async def test_basic_repository_operations():
    """Test basic repository operations"""
    print("Testing basic repository operations...")
    
    # Create database manager
    db_manager = DatabaseManager()
    
    try:
        # Test connection
        connection_ok = await db_manager.test_connection()
        print(f"Database connection: {'OK' if connection_ok else 'FAILED'}")
        
        if not connection_ok:
            print("Skipping tests due to database connection failure")
            return
        
        async with db_manager.get_async_session() as session:
            # Create test user
            test_user = ChatUser(
                anp_seq=99999,
                name="Test User",
                email="test@example.com",
                test_completed_at=datetime.utcnow()
            )
            session.add(test_user)
            await session.flush()
            print(f"Created test user: {test_user.user_id}")
            
            # Create repository
            repo = DocumentRepository(session)
            
            # Test document creation
            sample_embedding = [0.1] * 768
            doc_data = ChatDocumentCreate(
                user_id=test_user.user_id,
                doc_type=DocumentType.PERSONALITY_PROFILE,
                content={
                    "primary_tendency": {
                        "name": "창의형",
                        "code": "tnd12000",
                        "explanation": "새로운 아이디어를 창출합니다.",
                        "rank": 1,
                        "percentage_in_total": 15.2,
                        "score": 85
                    },
                    "secondary_tendency": {
                        "name": "분석형",
                        "code": "tnd21000",
                        "explanation": "논리적 사고를 통해 문제를 분석합니다.",
                        "rank": 2,
                        "percentage_in_total": 12.8,
                        "score": 78
                    },
                    "top_tendencies": [
                        {"rank": 1, "name": "창의형", "score": 85},
                        {"rank": 2, "name": "분석형", "score": 78},
                        {"rank": 3, "name": "탐구형", "score": 72}
                    ],
                    "overall_summary": "창의적이고 분석적인 성향을 가진 사용자입니다."
                },
                summary_text="사용자는 창의형 성향이 강하며, 새로운 아이디어 창출에 뛰어납니다.",
                metadata={"test": True}
            )
            
            # Create document
            document = await repo.create_document(doc_data, sample_embedding)
            print(f"Created document: {document.doc_id}")
            
            # Test document retrieval
            retrieved_doc = await repo.get_document_by_id(document.doc_id)
            assert retrieved_doc is not None
            assert retrieved_doc.doc_id == document.doc_id
            print("Document retrieval: OK")
            
            # Test documents by user
            user_docs = await repo.get_documents_by_user(test_user.user_id)
            assert len(user_docs) == 1
            assert user_docs[0].doc_id == document.doc_id
            print("Documents by user: OK")
            
            # Test document count
            count = await repo.get_document_count_by_user(test_user.user_id)
            assert count == 1
            print("Document count: OK")
            
            # Test document types
            types = await repo.get_document_types_by_user(test_user.user_id)
            assert DocumentType.PERSONALITY_PROFILE in types
            print("Document types: OK")
            
            # Test document existence check
            exists = await repo.check_document_exists(test_user.user_id, DocumentType.PERSONALITY_PROFILE)
            assert exists is True
            print("Document existence check: OK")
            
            # Test document update
            updated_doc = await repo.update_document(
                document.doc_id,
                content={"updated": "content"},
                summary_text="Updated summary text for testing purposes"
            )
            assert updated_doc is not None
            assert updated_doc.content == {"updated": "content"}
            assert "version_count" in updated_doc.doc_metadata
            print("Document update: OK")
            
            # Test document deletion
            deleted = await repo.delete_document(document.doc_id)
            assert deleted is True
            
            # Verify deletion
            deleted_doc = await repo.get_document_by_id(document.doc_id)
            assert deleted_doc is None
            print("Document deletion: OK")
            
            await session.commit()
            print("All repository tests passed!")
            
    except Exception as e:
        print(f"Test failed with error: {e}")
        raise
    finally:
        await db_manager.close()


async def test_batch_operations():
    """Test batch document operations"""
    print("\nTesting batch operations...")
    
    db_manager = DatabaseManager()
    
    try:
        async with db_manager.get_async_session() as session:
            # Create test user
            test_user = ChatUser(
                anp_seq=99998,
                name="Batch Test User",
                email="batch@example.com",
                test_completed_at=datetime.utcnow()
            )
            session.add(test_user)
            await session.flush()
            
            # Create repository
            repo = DocumentRepository(session)
            
            # Prepare batch data
            batch_data = []
            sample_embedding = [0.2] * 768
            
            for i in range(3):
                doc_data = ChatDocumentCreate(
                    user_id=test_user.user_id,
                    doc_type=DocumentType.PERSONALITY_PROFILE,
                    content={"batch_test": f"document_{i}"},
                    summary_text=f"Batch test document {i} for testing batch creation functionality"
                )
                batch_data.append((doc_data, sample_embedding))
            
            # Test batch creation
            result = await repo.batch_create_documents(batch_data)
            
            assert result.documents_created == 3
            assert result.documents_failed == 0
            print(f"Batch creation: {result.documents_created} documents created")
            
            # Verify documents were created
            docs = await repo.get_documents_by_user(test_user.user_id)
            assert len(docs) == 3
            print("Batch creation verification: OK")
            
            await session.commit()
            print("Batch operations test passed!")
            
    except Exception as e:
        print(f"Batch test failed with error: {e}")
        raise
    finally:
        await db_manager.close()


async def main():
    """Run all tests"""
    print("Starting repository tests...\n")
    
    try:
        await test_basic_repository_operations()
        await test_batch_operations()
        print("\n✅ All tests passed successfully!")
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)