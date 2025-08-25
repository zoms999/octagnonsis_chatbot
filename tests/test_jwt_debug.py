#!/usr/bin/env python3
"""
JWT 토큰 디버깅
"""

import jwt
import json

# 실제 요청에서 사용된 JWT 토큰
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNTI5NDgwMmMtMjIxOS00NjUxLWE0YTUtYTlhNWRhZTc1NDZmIiwidXNlcl90eXBlIjoicGVyc29uYWwiLCJhY19pZCI6InRlc3Q5OTkiLCJleHAiOjE3NTUyNTA2MzIsImlhdCI6MTc1NTE2NDIzMn0.PXZoN6oiJx8mXTT9UoDTfzXh5XDcY7tmJYIiA-Hb16A"

try:
    # JWT 토큰 디코딩 (서명 검증 없이)
    decoded = jwt.decode(token, options={"verify_signature": False})
    print("JWT 토큰 내용:")
    print(json.dumps(decoded, indent=2, ensure_ascii=False))
    
    # 만료 시간 확인
    import datetime
    exp_timestamp = decoded.get('exp')
    if exp_timestamp:
        exp_date = datetime.datetime.fromtimestamp(exp_timestamp)
        now = datetime.datetime.now()
        print(f"\n토큰 만료 시간: {exp_date}")
        print(f"현재 시간: {now}")
        print(f"토큰 유효성: {'유효' if exp_date > now else '만료됨'}")
    
except Exception as e:
    print(f"JWT 디코딩 에러: {e}")