#!/usr/bin/env python3
"""
챗봇 시스템 종합 진단 스크립트
"""

import asyncio
import sys
import requests
import json
from datetime import datetime
sys.path.append('.')

from database.connection import db_manager
from sqlalchemy import select, func
from database.models import ChatUser, ChatDocument
from etl.vector_embedder import VectorEmbedder
from database.vector_search import VectorSearchService, SearchQuery
from uuid import UUID

async def diagnose_system():
    print("=== 챗봇 시스템 종합 진단 ===")
    print(f"진단 시작 시간: {datetime.now()}")
    
    # 1. 데이터베이스 연결 테스트
    print("\n1. 데이터베이스 연결 테스트")
    try:
        async with db_manager.get_async_session() as db:
            await db.execute(select(1))
            print("✓ 데이터베이스 연결 성공")
            
            # 사용자 및 문서 통계
            user_count = await db.execute(select(func.count(ChatUser.user_id)))
            doc_count = await db.execute(select(func.count(ChatDocument.doc_id)))
            print(f"✓ 총 사용자 수: {user_count.scalar()}")
            print(f"✓ 총 문서 수: {doc_count.scalar()}")
            
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        return
    
    # 2. 벡터 임베더 테스트
    print("\n2. 벡터 임베더 테스트")
    try:
        embedder = VectorEmbedder.instance()
        test_text = "내성향알려줘"
        embedding = await embedder.generate_embedding(test_text)
        print(f"✓ 임베딩 생성 성공: {len(embedding.embedding)}차원")
    except Exception as e:
        print(f"❌ 벡터 임베더 실패: {e}")
        return
    
    # 3. 특정 사용자 데이터 확인
    print("\n3. 특정 사용자 데이터 확인")
    test_user_id = "5294802c-2219-4651-a4a5-a9a5dae7546f"
    try:
        async with db_manager.get_async_session() as db:
            # 사용자 존재 확인
            user_result = await db.execute(
                select(ChatUser).where(ChatUser.user_id == UUID(test_user_id))
            )
            user = user_result.scalar_one_or_none()
            
            if user:
                print(f"✓ 사용자 발견: {user.name} (anp_seq: {user.anp_seq})")
                
                # 사용자 문서 확인
                doc_result = await db.execute(
                    select(ChatDocument.doc_type, func.count(ChatDocument.doc_id))
                    .where(ChatDocument.user_id == user.user_id)
                    .group_by(ChatDocument.doc_type)
                )
                docs = doc_result.all()
                
                if docs:
                    print("✓ 사용자 문서:")
                    for doc_type, count in docs:
                        print(f"  - {doc_type}: {count}개")
                else:
                    print("❌ 사용자 문서 없음")
            else:
                print(f"❌ 사용자 {test_user_id} 찾을 수 없음")
                
    except Exception as e:
        print(f"❌ 사용자 데이터 확인 실패: {e}")
    
    # 4. 벡터 검색 테스트
    print("\n4. 벡터 검색 테스트")
    try:
        async with db_manager.get_async_session() as db:
            vector_search = VectorSearchService(db)
            search_query = SearchQuery(
                user_id=UUID(test_user_id),
                query_vector=embedding.embedding,
                limit=5,
                similarity_threshold=0.3
            )
            
            results = await vector_search.similarity_search(search_query)
            print(f"✓ 벡터 검색 성공: {len(results)}개 결과")
            
            for i, result in enumerate(results[:3]):
                print(f"  결과 {i+1}: {result.document.doc_type} (유사도: {result.similarity_score:.3f})")
                
    except Exception as e:
        print(f"❌ 벡터 검색 실패: {e}")
    
    # 5. HTTP API 테스트
    print("\n5. HTTP API 테스트")
    try:
        url = "http://127.0.0.1:8000/api/chat/health"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            health_data = response.json()
            print(f"✓ API 서버 상태: {health_data['status']}")
            
            # 실제 질문 API 테스트
            question_url = "http://127.0.0.1:8000/api/chat/question"
            headers = {
                "accept": "application/json",
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNTI5NDgwMmMtMjIxOS00NjUxLWE0YTUtYTlhNWRhZTc1NDZmIiwidXNlcl90eXBlIjoicGVyc29uYWwiLCJhY19pZCI6InRlc3Q5OTkiLCJleHAiOjE3NTUyNTA2MzIsImlhdCI6MTc1NTE2NDIzMn0.PXZoN6oiJx8mXTT9UoDTfzXh5XDcY7tmJYIiA-Hb16A",
                "Content-Type": "application/json"
            }
            
            data = {
                "user_id": test_user_id,
                "question": "내성향알려줘",
                "conversation_id": "test"
            }
            
            api_response = requests.post(question_url, headers=headers, json=data, timeout=30)
            
            if api_response.status_code == 200:
                result = api_response.json()
                print(f"✓ 질문 API 성공")
                print(f"  응답 길이: {len(result['response'])}자")
                print(f"  검색된 문서: {len(result['retrieved_documents'])}개")
                print(f"  신뢰도: {result['confidence_score']}")
                
                # 응답 내용 분석
                if "검사 결과를 찾을 수 없" in result['response']:
                    print("❌ 경고: '검사 결과를 찾을 수 없다' 메시지 발견")
                else:
                    print("✓ 정상적인 응답 생성됨")
            else:
                print(f"❌ 질문 API 실패: {api_response.status_code} - {api_response.text}")
        else:
            print(f"❌ API 서버 연결 실패: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ API 서버에 연결할 수 없음 (서버가 실행 중인지 확인)")
    except Exception as e:
        print(f"❌ HTTP API 테스트 실패: {e}")
    
    print(f"\n진단 완료 시간: {datetime.now()}")
    print("=== 진단 완료 ===")

if __name__ == "__main__":
    asyncio.run(diagnose_system())