#!/usr/bin/env python3
"""
RAG 검색 디버깅 테스트
"""

import asyncio
import sys
sys.path.append('.')

from database.connection import db_manager
from database.vector_search import VectorSearchService, SearchQuery
from etl.vector_embedder import VectorEmbedder
from rag.question_processor import QuestionProcessor
from rag.context_builder import ContextBuilder
from rag.response_generator import ResponseGenerator
from uuid import UUID

async def test_rag_search():
    user_id = "5294802c-2219-4651-a4a5-a9a5dae7546f"
    question = "내성향알려줘"
    
    print(f'사용자 {user_id}의 질문 "{question}"에 대한 RAG 검색 테스트:')
    
    try:
        async with db_manager.get_async_session() as db:
            # 1. 벡터 임베더 초기화
            vector_embedder = VectorEmbedder.instance()
            print('✓ 벡터 임베더 초기화 완료')
            
            # 2. 질문 임베딩
            question_embedding = await vector_embedder.generate_embedding(question)
            print(f'✓ 질문 임베딩 완료: {len(question_embedding.embedding)}차원')
            
            # 3. 벡터 검색 서비스 초기화
            vector_search = VectorSearchService(db)
            print('✓ 벡터 검색 서비스 초기화 완료')
            
            # 4. 검색 쿼리 생성
            search_query = SearchQuery(
                user_id=UUID(user_id),
                query_vector=question_embedding.embedding,
                limit=5,
                similarity_threshold=0.3  # 낮은 임계값으로 테스트
            )
            
            # 5. 벡터 검색 실행
            search_results = await vector_search.similarity_search(search_query)
            print(f'✓ 벡터 검색 완료: {len(search_results)}개 결과')
            
            for i, result in enumerate(search_results):
                print(f'  결과 {i+1}: {result.document.doc_type} (유사도: {result.similarity_score:.3f})')
                print(f'    요약: {result.document.summary_text[:100]}...')
            
            # 6. 질문 프로세서 테스트
            question_processor = QuestionProcessor(vector_embedder)
            processed_question = await question_processor.process_question(question, user_id)
            print(f'✓ 질문 처리 완료: 카테고리={processed_question.category}, 의도={processed_question.intent}')
            
            # 7. 컨텍스트 빌더 테스트
            context_builder = ContextBuilder(vector_search)
            context = await context_builder.build_context(processed_question, user_id)
            print(f'✓ 컨텍스트 구성 완료: {len(context.retrieved_documents)}개 문서')
            
            # 8. 응답 생성 테스트
            response_generator = ResponseGenerator()
            response = await response_generator.generate_response(context, user_id)
            print(f'✓ 응답 생성 완료: 신뢰도={response.confidence_score:.3f}')
            print(f'응답 내용: {response.content[:200]}...')
            
    except Exception as e:
        print(f'❌ 에러 발생: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_rag_search())