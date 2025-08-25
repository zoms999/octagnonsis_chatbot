#!/usr/bin/env python3
"""
Test Improved ETL Process
Test the ETL process with the applied fixes
"""

import asyncio
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

async def test_etl_with_monitoring():
    """Test ETL process with connection monitoring"""
    
    print("=== Testing Improved ETL Process ===")
    
    # Start connection monitoring
    from etl.connection_monitor import connection_monitor
    await connection_monitor.start_monitoring()
    
    try:
        # Test query execution
        print("\n1. Testing Query Execution...")
        await connection_monitor.check_connections("before_queries")
        
        from etl.simple_query_executor import SimpleQueryExecutor
        executor = SimpleQueryExecutor()
        
        results = executor.execute_core_queries(18240)
        
        await connection_monitor.check_connections("after_queries")
        
        # Clean up executor
        if hasattr(executor, 'cleanup'):
            if asyncio.iscoroutinefunction(executor.cleanup):
                await executor.cleanup()
            else:
                executor.cleanup()
        
        await connection_monitor.check_connections("after_cleanup")
        
        # Test document transformation
        print("\n2. Testing Document Transformation...")
        
        # Convert results to expected format
        formatted_results = {}
        for query_name, result in results.items():
            if result.success and result.data:
                formatted_results[query_name] = result.data
            else:
                formatted_results[query_name] = []
        
        # Test enhanced document transformer
        from etl.enhanced_document_transformer import enhanced_transformer
        documents = await enhanced_transformer.transform_all_documents(formatted_results)
        
        await connection_monitor.check_connections("after_transformation")
        
        print(f"✓ Created {len(documents)} documents")
        
        # Show document distribution
        doc_types = {}
        for doc in documents:
            doc_types[doc.doc_type] = doc_types.get(doc.doc_type, 0) + 1
        
        print("Document distribution:")
        for doc_type, count in doc_types.items():
            print(f"  {doc_type}: {count}")
        
        # Test document content
        print("\n3. Testing Document Content...")
        for i, doc in enumerate(documents[:3]):  # Show first 3 documents
            print(f"Document {i+1}: {doc.doc_type}")
            print(f"  Summary: {doc.summary_text[:100]}...")
            print(f"  Questions: {len(doc.metadata.get('hypothetical_questions', []))}")
        
        return True
        
    except Exception as e:
        logger.error(f"ETL test failed: {e}")
        print(f"✗ ETL test failed: {e}")
        return False
        
    finally:
        await connection_monitor.end_monitoring()

async def test_connection_leak_prevention():
    """Test that connection leaks are prevented"""
    
    print("\n=== Testing Connection Leak Prevention ===")
    
    from etl.connection_monitor import connection_monitor
    await connection_monitor.start_monitoring()
    
    try:
        # Run multiple query executions to test for leaks
        for i in range(3):
            print(f"Iteration {i+1}...")
            
            from etl.simple_query_executor import SimpleQueryExecutor
            executor = SimpleQueryExecutor()
            
            results = executor.execute_core_queries(18240)
            
            # Clean up
            if hasattr(executor, 'cleanup'):
                if asyncio.iscoroutinefunction(executor.cleanup):
                    await executor.cleanup()
                else:
                    executor.cleanup()
            
            await connection_monitor.check_connections(f"iteration_{i+1}")
        
        print("✓ Multiple iterations completed without connection leaks")
        return True
        
    except Exception as e:
        print(f"✗ Connection leak test failed: {e}")
        return False
        
    finally:
        await connection_monitor.end_monitoring()

async def simulate_full_etl():
    """Simulate a full ETL process"""
    
    print("\n=== Simulating Full ETL Process ===")
    
    from etl.connection_monitor import connection_monitor
    await connection_monitor.start_monitoring()
    
    try:
        # Stage 1: Query Execution
        print("Stage 1: Query Execution")
        await connection_monitor.check_connections("stage_1_start")
        
        from etl.simple_query_executor import SimpleQueryExecutor
        executor = SimpleQueryExecutor()
        query_results = executor.execute_core_queries(18240)
        
        # Convert to expected format
        formatted_results = {}
        for query_name, result in query_results.items():
            if result.success and result.data:
                formatted_results[query_name] = result.data
            else:
                formatted_results[query_name] = []
        
        executor.cleanup()
        await connection_monitor.check_connections("stage_1_end")
        
        # Stage 2: Document Transformation
        print("Stage 2: Document Transformation")
        await connection_monitor.check_connections("stage_2_start")
        
        from etl.enhanced_document_transformer import enhanced_transformer
        documents = await enhanced_transformer.transform_all_documents(formatted_results)
        
        await connection_monitor.check_connections("stage_2_end")
        
        # Stage 3: Mock Embedding Generation
        print("Stage 3: Mock Embedding Generation")
        await connection_monitor.check_connections("stage_3_start")
        
        # Simulate embedding generation
        for doc in documents:
            doc.embedding_vector = [0.1] * 384  # Mock embedding
        
        await connection_monitor.check_connections("stage_3_end")
        
        # Stage 4: Mock Document Storage
        print("Stage 4: Mock Document Storage")
        await connection_monitor.check_connections("stage_4_start")
        
        # Simulate document storage (without actually storing)
        print(f"Would store {len(documents)} documents")
        
        await connection_monitor.check_connections("stage_4_end")
        
        print("✓ Full ETL simulation completed successfully")
        
        # Summary
        print(f"\nETL Summary:")
        print(f"- Queries executed: {len(query_results)}")
        print(f"- Documents created: {len(documents)}")
        print(f"- Document types: {len(set(doc.doc_type for doc in documents))}")
        
        return True
        
    except Exception as e:
        print(f"✗ Full ETL simulation failed: {e}")
        return False
        
    finally:
        await connection_monitor.end_monitoring()

async def main():
    """Run all tests"""
    
    print("Testing Improved ETL Process")
    print("=" * 50)
    
    tests = [
        ("ETL with Monitoring", test_etl_with_monitoring),
        ("Connection Leak Prevention", test_connection_leak_prevention),
        ("Full ETL Simulation", simulate_full_etl)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} failed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! ETL improvements are working correctly.")
    else:
        print("⚠️  Some tests failed. Review the output above for details.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())