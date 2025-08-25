#!/usr/bin/env python3
"""
API 엔드포인트 디버깅 테스트
"""

import asyncio
import sys
sys.path.append('.')

from database.connection import db_manager
from api.chat_endpoints import ask_question, ChatQuestionRequest, get_rag_components
from api.auth_endpoints import get_current_user
from uuid import UUID

async def test_api_endpoint():
    user_id = "5294802c-2219-4651-a4a5-a9a5dae7546f"
    question = "내성향알려줘"
    
    print(f'API 엔드포인트 테스트: 사용자 {user_id}의 질문 "{question}"')
    
    try:
        # 1. 요청 객체 생성
        request = ChatQuestionRequest(
            user_id=user_id,
            question=question,
            conversation_id="string"
        )
        print('✓ 요청 객체 생성 완료')
        
        # 2. 현재 사용자 모킹 (인증 우회)
        current_user = {"user_id": user_id}
        print('✓ 사용자 인증 모킹 완료')
        
        # 3. RAG 컴포넌트 초기화
        rag_components = await get_rag_components()
        print('✓ RAG 컴포넌트 초기화 완료')
        
        # 4. API 엔드포인트 직접 호출
        response = await ask_question(request, current_user, rag_components)
        print('✓ API 호출 완료')
        
        print(f'응답 내용: {response.response[:200]}...')
        print(f'검색된 문서 수: {len(response.retrieved_documents)}')
        print(f'신뢰도: {response.confidence_score}')
        
        # 검색된 문서 상세 정보
        for i, doc in enumerate(response.retrieved_documents):
            print(f'  문서 {i+1}: {doc["doc_type"]} (유사도: {doc["similarity_score"]:.3f})')
        
    except Exception as e:
        print(f'❌ 에러 발생: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api_endpoint())