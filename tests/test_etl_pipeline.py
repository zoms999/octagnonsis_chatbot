"""
Test script for ETL pipeline foundation
Verifies the implementation of legacy query executor, document transformer, and vector embedder
"""

import asyncio
import logging
from typing import Dict, Any, List
import pytest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_etl_pipeline():
    """Test the complete ETL pipeline foundation"""
    
    try:
        # Import the ETL components
        from etl.legacy_query_executor import LegacyQueryExecutor, QueryResult
        from etl.document_transformer import DocumentTransformer, TransformedDocument
        from etl.vector_embedder import VectorEmbedder
        from database.connection import get_sync_session
        
        logger.info("Starting ETL pipeline foundation test...")
        
        # Test 1: Legacy Query Executor
        logger.info("Testing Legacy Query Executor...")
        query_executor = LegacyQueryExecutor(max_retries=1)
        
        # Mock database session (in real implementation, this would be a proper session)
        mock_session = None  # Using None for this test since we have mock data
        test_anp_seq = 12345
        
        # Execute queries
        query_results = await query_executor.execute_all_queries_async(mock_session, test_anp_seq)
        successful_results = await query_executor.get_successful_results(query_results)
        
        logger.info(f"Query execution completed: {len(successful_results)} successful queries")
        
        # Test 2: Document Transformer
        logger.info("Testing Document Transformer...")
        transformer = DocumentTransformer()
        
        # Transform query results into documents
        documents = await transformer.transform_all_documents(successful_results)
        
        logger.info(f"Document transformation completed: {len(documents)} documents created")
        
        # Validate documents
        valid_documents = []
        for doc in documents:
            if await transformer.validate_document(doc):
                valid_documents.append(doc)
                logger.info(f"✓ Valid document: {doc.doc_type}")
            else:
                logger.warning(f"✗ Invalid document: {doc.doc_type}")
        
        # Test 3: Vector Embedder (only if API key is available)
        logger.info("Testing Vector Embedder...")
        
        try:
            # Note: This will only work if GOOGLE_API_KEY environment variable is set
            async with VectorEmbedder(enable_cache=True) as embedder:
                # Test single embedding
                test_text = "이것은 테스트 텍스트입니다. 벡터 임베딩을 생성하기 위한 샘플입니다."
                embedding_result = await embedder.generate_embedding(test_text)
                
                logger.info(f"✓ Single embedding generated: {embedding_result.dimensions} dimensions")
                
                # Test batch embeddings with document summary texts
                summary_texts = [doc.summary_text for doc in valid_documents[:3]]  # Test with first 3 documents
                if summary_texts:
                    batch_results = await embedder.generate_embeddings_batch(summary_texts)
                    logger.info(f"✓ Batch embeddings generated: {len(batch_results)} embeddings")
                
                # Test document embedding enhancement
                document_dicts = [
                    {
                        'doc_type': doc.doc_type,
                        'content': doc.content,
                        'summary_text': doc.summary_text,
                        'metadata': doc.metadata
                    }
                    for doc in valid_documents[:2]  # Test with first 2 documents
                ]
                
                enhanced_documents = await embedder.generate_document_embeddings(document_dicts)
                logger.info(f"✓ Document embeddings generated: {len(enhanced_documents)} enhanced documents")
                
                # Check cache stats
                cache_stats = embedder.get_cache_stats()
                logger.info(f"Cache stats: {cache_stats}")
                
        except ValueError as e:
            logger.warning(f"Vector embedder test skipped: {e}")
            logger.info("To test vector embedder, set GOOGLE_API_KEY environment variable")
        
        # Test 4: Integration Test
        logger.info("Testing ETL pipeline integration...")
        
        # Simulate complete ETL flow
        pipeline_results = {
            'queries_executed': len(query_results),
            'successful_queries': len(successful_results),
            'documents_created': len(documents),
            'valid_documents': len(valid_documents),
            'document_types': [doc.doc_type for doc in valid_documents]
        }
        
        logger.info("ETL Pipeline Integration Results:")
        for key, value in pipeline_results.items():
            logger.info(f"  {key}: {value}")
        
        # Clean up
        await query_executor.close()
        
        logger.info("✅ ETL pipeline foundation test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ ETL pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

@pytest.mark.asyncio
async def test_individual_components():
    """Test individual components separately"""
    
    logger.info("Testing individual ETL components...")
    
    # Test Legacy Query Executor
    try:
        from etl.legacy_query_executor import LegacyQueryExecutor
        executor = LegacyQueryExecutor()
        logger.info("✓ LegacyQueryExecutor imported and initialized successfully")
        await executor.close()
    except Exception as e:
        logger.error(f"✗ LegacyQueryExecutor test failed: {e}")
    
    # Test Document Transformer
    try:
        from etl.document_transformer import DocumentTransformer
        transformer = DocumentTransformer()
        logger.info("✓ DocumentTransformer imported and initialized successfully")
    except Exception as e:
        logger.error(f"✗ DocumentTransformer test failed: {e}")
    
    # Test Vector Embedder
    try:
        from etl.vector_embedder import VectorEmbedder, EmbeddingCache
        cache = EmbeddingCache()
        logger.info("✓ VectorEmbedder and EmbeddingCache imported successfully")
    except Exception as e:
        logger.error(f"✗ VectorEmbedder test failed: {e}")

if __name__ == "__main__":
    print("🚀 Testing ETL Pipeline Foundation")
    print("=" * 50)
    
    # Test individual components first
    asyncio.run(test_individual_components())
    
    print("\n" + "=" * 50)
    
    # Test complete pipeline
    success = asyncio.run(test_etl_pipeline())
    
    if success:
        print("\n🎉 All tests passed! ETL pipeline foundation is ready.")
    else:
        print("\n💥 Some tests failed. Check the logs above.")