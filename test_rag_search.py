#!/usr/bin/env python3
"""
Test RAG search with hypothetical questions
"""

import asyncio
import sys
import requests
import json
sys.path.append('.')

async def test_rag_search():
    """RAG 검색 성능을 테스트합니다."""
    
    user_id = "9b08ed21-fddf-4998-a1f4-29bccda89a54"
    
    # JWT 토큰 생성 (테스트용)
    import jwt
    from datetime import datetime, timedelta
    
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, 'your-secret-key', algorithm='HS256')
    
    # API 요청
    url = "http://localhost:8000/api/chat"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    data = {
        "message": "내성향알려줘",
        "conversation_id": "test-conv-hypothetical"
    }
    
    print(f"RAG 검색 테스트:")
    print(f"  사용자 질문: {data['message']}")
    print(f"  User ID: {user_id}")
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ API 응답 성공!")
            print(f"  응답 길이: {len(result.get('response', ''))} 문자")
            
            # 검색된 문서 확인
            retrieved_docs = result.get('retrieved_documents', [])
            print(f"  검색된 문서 수: {len(retrieved_docs)}")
            
            if retrieved_docs:
                print(f"  검색된 문서 타입들:")
                for doc in retrieved_docs:
                    print(f"    - {doc.get('doc_type', 'unknown')}: {doc.get('summary_text', '')[:50]}...")
                print(f"✅ RAG 검색 성공! 관련 문서를 찾았습니다.")
            else:
                print(f"❌ RAG 검색 실패: 관련 문서를 찾지 못했습니다.")
                
            # 응답 내용 일부 출력
            response_text = result.get('response', '')
            if response_text:
                print(f"\n📝 챗봇 응답 (처음 200자):")
                print(f"  {response_text[:200]}...")
        else:
            print(f"❌ API 요청 실패: {response.status_code}")
            print(f"  에러: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 네트워크 에러: {e}")
    except Exception as e:
        print(f"❌ 예상치 못한 에러: {e}")

if __name__ == "__main__":
    asyncio.run(test_rag_search())