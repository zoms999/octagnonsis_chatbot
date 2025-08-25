#!/usr/bin/env python3
"""
Test script to identify the specific error in the chat endpoint
"""

import asyncio
import logging
import sys
import traceback
from uuid import UUID

# Setup logging to see detailed errors
logging.basicConfig(level=logging.DEBUG)

async def test_chat_components():
    """Test each component of the chat pipeline to identify the issue"""
    
    print("Testing chat endpoint components...")
    
    try:
        # Test 1: Database connection
        print("\n1. Testing database connection...")
        from database.connection import db_manager
        async with db_manager.get_async_session() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        # Test 2: Import RAG components
        print("\n2. Testing RAG component imports...")
        from rag.question_processor import QuestionProcessor
        from rag.context_builder import ContextBuilder
        from rag.response_generator import ResponseGenerator
        from etl.vector_embedder import VectorEmbedder
        from database.vector_search import VectorSearchService
        print("✓ RAG component imports successful")
    except Exception as e:
        print(f"✗ RAG component import failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        # Test 3: Initialize components
        print("\n3. Testing component initialization...")
        
        # Initialize vector embedder
        vector_embedder = VectorEmbedder.instance()
        print("✓ VectorEmbedder initialized")
        
        # Initialize question processor
        question_processor = QuestionProcessor(vector_embedder)
        print("✓ QuestionProcessor initialized")
        
        # Test database session for other components
        async with db_manager.get_async_session() as session:
            # Initialize vector search service
            vector_search_service = VectorSearchService(session)
            print("✓ VectorSearchService initialized")
            
            # Initialize context builder
            context_builder = ContextBuilder(vector_search_service)
            print("✓ ContextBuilder initialized")
        
        # Initialize response generator
        response_generator = ResponseGenerator()
        print("✓ ResponseGenerator initialized")
        
    except Exception as e:
        print(f"✗ Component initialization failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        # Test 4: Process a simple question
        print("\n4. Testing question processing...")
        processed_question = await question_processor.process_question(
            "적성검사기반", 
            "5294802c-2219-4651-a4a5-a9a5dae7546f"
        )
        print(f"✓ Question processed: category={processed_question.category.value}")
        
    except Exception as e:
        print(f"✗ Question processing failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        # Test 5: Check if user exists
        print("\n5. Testing user lookup...")
        async with db_manager.get_async_session() as session:
            from database.models import ChatUser
            from sqlalchemy import select
            
            user_uuid = UUID("5294802c-2219-4651-a4a5-a9a5dae7546f")
            result = await session.execute(select(ChatUser).where(ChatUser.user_id == user_uuid))
            user = result.scalar_one_or_none()
            
            if user:
                print(f"✓ User found: {user.name}")
            else:
                print("✗ User not found in database")
                return False
                
    except Exception as e:
        print(f"✗ User lookup failed: {e}")
        traceback.print_exc()
        return False
    
    print("\n✓ All components tested successfully!")
    return True

if __name__ == "__main__":
    asyncio.run(test_chat_components())