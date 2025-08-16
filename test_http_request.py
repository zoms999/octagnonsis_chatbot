#!/usr/bin/env python3
"""
실제 HTTP 요청 테스트
"""

import requests
import json

def test_http_request():
    url = "http://127.0.0.1:8000/api/chat/question"
    
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNTI5NDgwMmMtMjIxOS00NjUxLWE0YTUtYTlhNWRhZTc1NDZmIiwidXNlcl90eXBlIjoicGVyc29uYWwiLCJhY19pZCI6InRlc3Q5OTkiLCJleHAiOjE3NTUyNTA2MzIsImlhdCI6MTc1NTE2NDIzMn0.PXZoN6oiJx8mXTT9UoDTfzXh5XDcY7tmJYIiA-Hb16A",
        "Content-Type": "application/json"
    }
    
    data = {
        "user_id": "5294802c-2219-4651-a4a5-a9a5dae7546f",
        "question": "내성향알려줘",
        "conversation_id": "string"
    }
    
    try:
        print("HTTP 요청 전송 중...")
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        print(f"응답 상태 코드: {response.status_code}")
        print(f"응답 헤더: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"응답 내용: {result['response'][:200]}...")
            print(f"검색된 문서 수: {len(result['retrieved_documents'])}")
            print(f"신뢰도: {result['confidence_score']}")
        else:
            print(f"에러 응답: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
    except requests.exceptions.Timeout:
        print("❌ 요청 시간 초과")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    test_http_request()