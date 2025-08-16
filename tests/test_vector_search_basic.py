"""
Basic tests for vector search functionality
"""

import asyncio
import random
from datetime import datetime
from uuid import uuid4

from database.connection import DatabaseManager
from database.models import ChatUser, ChatDocument, DocumentType
from database.repositories import DocumentRepository
from database.vector_search import VectorSearchService, SearchQuery, SimilarityMetric
from database.schemas import ChatDocumentCreate


async def test_basic_vector_search():
    """Test basic vector search operations"""
    print("Testing basic vector search operations...")
    
    db_manager = DatabaseManager()
    
    try:
        async with db_manager.get_async_session() as session:
            # Create test user
            test_user = ChatUser(
                anp_seq=random.randint(100000, 999999),
                name="Vector Test User",
                email="vector@example.com",
                test_completed_at=datetime.utcnow()
            )
            session.add(test_user)
            await session.flush()
            print(f"Created test user: {test_user.user_id}")
            
            # Create repository and search service
            repo = DocumentRepository(session)
            search_service = VectorSearchService(session)
            
            # Create test documents with different embeddings
            embeddings = [
                [0.1] * 768,  # Similar to query
                [0.9] * 768,  # Different from query
                [0.2] * 768   # Somewhat similar to query
            ]
            
            created_docs = []
            for i, embedding in enumerate(embeddings):
                doc_data = ChatDocumentCreate(
                    user_id=test_user.user_id,
                    doc_type=DocumentType.PERSONALITY_PROFILE,
                    content={
                        "primary_tendency": {
                            "name": f"성향{i+1}",
                            "code": f"tnd{i+1}000",
                            "explanation": f"테스트 성향 {i+1}입니다.",
                            "rank": i+1,
                            "percentage_in_total": 15.0 - i,
                            "score": 85 - i*5
                        },
                        "secondary_tendency": {
                            "name": f"부성향{i+1}",
                            "code": f"tnd{i+1}100",
                            "explanation": f"테스트 부성향 {i+1}입니다.",
                            "rank": i+2,
                            "percentage_in_total": 12.0 - i,
                            "score": 75 - i*5
                        },
                        "top_tendencies": [
                            {"rank": 1, "name": f"성향{i+1}", "score": 85 - i*5}
                        ],
                        "overall_summary": f"테스트 문서 {i+1}의 성향 분석입니다."
                    },
                    summary_text=f"테스트 문서 {i+1}의 성향 분석 요약입니다. 벡터 검색 테스트용 문서입니다.",
                    metadata={"test_doc": i+1}
                )
                
                doc = await repo.create_document(doc_data, embedding)
                created_docs.append(doc)
                print(f"Created test document {i+1}: {doc.doc_id}")
            
            await session.commit()
            
            # Test basic similarity search
            query_vector = [0.15] * 768  # Close to first document
            search_query = SearchQuery(
                user_id=test_user.user_id,
                query_vector=query_vector,
                limit=3,
                similarity_threshold=0.5
            )
            
            results = await search_service.similarity_search(search_query)
            
            assert len(results) > 0, "Should return search results"
            assert all(r.similarity_score >= 0.5 for r in results), "All results should meet threshold"
            assert results[0].similarity_score >= results[-1].similarity_score, "Results should be sorted by similarity"
            print(f"Basic similarity search: Found {len(results)} results")
            
            # Test search by document type
            type_results = await search_service.search_by_document_type(
                test_user.user_id,
                query_vector,
                DocumentType.PERSONALITY_PROFILE
            )
            
            assert len(type_results) > 0, "Should find documents of specified type"
            assert all(r.document.doc_type == DocumentType.PERSONALITY_PROFILE for r in type_results), "All results should be of correct type"
            print(f"Search by document type: Found {len(type_results)} results")
            
            # Test similar documents search
            source_doc = created_docs[0]
            similar_results = await search_service.get_similar_documents(source_doc.doc_id, limit=2)
            
            assert all(r.document.doc_id != source_doc.doc_id for r in similar_results), "Should not include source document"
            print(f"Similar documents search: Found {len(similar_results)} results")
            
            # Test performance metrics
            metrics = await search_service.get_search_performance_metrics(user_id=test_user.user_id)
            assert len(metrics) > 0, "Should have performance metrics"
            print(f"Performance metrics: {len(metrics)} recorded searches")
            
            print("✅ All vector search tests passed!")
            
    except Exception as e:
        print(f"❌ Vector search test failed: {e}")
        raise
    finally:
        await db_manager.close()


async def test_multi_type_search():
    """Test multi-type search functionality"""
    print("\nTesting multi-type search...")
    
    db_manager = DatabaseManager()
    
    try:
        async with db_manager.get_async_session() as session:
            # Create test user
            test_user = ChatUser(
                anp_seq=random.randint(100000, 999999),
                name="Multi Type Test User",
                email="multitype@example.com",
                test_completed_at=datetime.utcnow()
            )
            session.add(test_user)
            await session.flush()
            
            # Create repository and search service
            repo = DocumentRepository(session)
            search_service = VectorSearchService(session)
            
            # Create documents of different types
            doc_types = [DocumentType.PERSONALITY_PROFILE, DocumentType.THINKING_SKILLS, DocumentType.CAREER_RECOMMENDATIONS]
            sample_embedding = [0.3] * 768
            
            for doc_type in doc_types:
                if doc_type == DocumentType.PERSONALITY_PROFILE:
                    content = {
                        "primary_tendency": {"name": "테스트", "code": "test", "explanation": "테스트", "rank": 1, "percentage_in_total": 15.0, "score": 85},
                        "secondary_tendency": {"name": "테스트2", "code": "test2", "explanation": "테스트2", "rank": 2, "percentage_in_total": 12.0, "score": 75},
                        "top_tendencies": [{"rank": 1, "name": "테스트", "score": 85}],
                        "overall_summary": "테스트 성향 분석"
                    }
                elif doc_type == DocumentType.THINKING_SKILLS:
                    content = {
                        "cognitive_abilities": [{"skill": f"능력{i}", "score": 80-i} for i in range(8)],
                        "analysis_summary": "테스트 사고 능력 분석"
                    }
                else:  # CAREER_RECOMMENDATIONS
                    content = {
                        "top_recommendations": [
                            {"job_name": f"직업{i}", "match_percentage": 90-i*5, "reasoning": f"추천 이유 {i}"} 
                            for i in range(5)
                        ],
                        "recommendations_summary": "테스트 직업 추천"
                    }
                
                doc_data = ChatDocumentCreate(
                    user_id=test_user.user_id,
                    doc_type=doc_type,
                    content=content,
                    summary_text=f"테스트 {doc_type} 문서입니다. 멀티 타입 검색 테스트용입니다.",
                    metadata={"doc_type": doc_type}
                )
                
                await repo.create_document(doc_data, sample_embedding)
                print(f"Created {doc_type} document")
            
            await session.commit()
            
            # Test multi-type search
            results = await search_service.multi_type_search(
                test_user.user_id,
                sample_embedding,
                doc_types,
                limit_per_type=1
            )
            
            assert len(results) == 3, "Should return results for all document types"
            for doc_type in doc_types:
                assert doc_type in results, f"Should have results for {doc_type}"
                assert len(results[doc_type]) <= 1, "Should respect limit per type"
            
            print(f"Multi-type search: Found results for {len(results)} document types")
            print("✅ Multi-type search test passed!")
            
    except Exception as e:
        print(f"❌ Multi-type search test failed: {e}")
        raise
    finally:
        await db_manager.close()


async def test_hybrid_search():
    """Test hybrid search functionality"""
    print("\nTesting hybrid search...")
    
    db_manager = DatabaseManager()
    
    try:
        async with db_manager.get_async_session() as session:
            # Create test user
            test_user = ChatUser(
                anp_seq=random.randint(100000, 999999),
                name="Hybrid Test User",
                email="hybrid@example.com",
                test_completed_at=datetime.utcnow()
            )
            session.add(test_user)
            await session.flush()
            
            # Create repository and search service
            repo = DocumentRepository(session)
            search_service = VectorSearchService(session)
            
            # Create test document
            doc_data = ChatDocumentCreate(
                user_id=test_user.user_id,
                doc_type=DocumentType.PERSONALITY_PROFILE,
                content={
                    "primary_tendency": {"name": "창의형", "code": "creative", "explanation": "창의적 성향", "rank": 1, "percentage_in_total": 15.0, "score": 85},
                    "secondary_tendency": {"name": "분석형", "code": "analytical", "explanation": "분석적 성향", "rank": 2, "percentage_in_total": 12.0, "score": 75},
                    "top_tendencies": [{"rank": 1, "name": "창의형", "score": 85}],
                    "overall_summary": "창의적이고 분석적인 성향"
                },
                summary_text="사용자는 창의적이고 분석적인 성향을 가지고 있습니다. 혁신적인 아이디어를 제시하며 논리적 사고가 뛰어납니다.",
                metadata={"hybrid_test": True}
            )
            
            sample_embedding = [0.4] * 768
            await repo.create_document(doc_data, sample_embedding)
            await session.commit()
            
            # Test hybrid search with text query
            results = await search_service.hybrid_search(
                test_user.user_id,
                sample_embedding,
                text_query="창의적 분석적",
                limit=5
            )
            
            assert len(results) > 0, "Should return hybrid search results"
            for result in results:
                assert 'text_query' in result.search_metadata, "Should have text query in metadata"
                assert 'search_type' in result.search_metadata, "Should have search type"
            
            print(f"Hybrid search: Found {len(results)} results with hybrid scoring")
            print("✅ Hybrid search test passed!")
            
    except Exception as e:
        print(f"❌ Hybrid search test failed: {e}")
        raise
    finally:
        await db_manager.close()


async def main():
    """Run all vector search tests"""
    print("Starting vector search tests...\n")
    
    try:
        await test_basic_vector_search()
        await test_multi_type_search()
        await test_hybrid_search()
        print("\n✅ All vector search tests passed successfully!")
        return True
    except Exception as e:
        print(f"\n❌ Vector search tests failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)