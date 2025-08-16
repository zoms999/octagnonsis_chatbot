"""
인증 시스템 테스트 스크립트
NextJS 백엔드에서 Python FastAPI로 포팅된 로그인 기능 테스트
"""

import asyncio
import httpx
import json
from typing import Dict, Any

# API 기본 URL
BASE_URL = "http://localhost:8000"

class AuthTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.token = None
        
    async def test_personal_login(self, username: str, password: str) -> Dict[str, Any]:
        """개인 사용자 로그인 테스트"""
        print(f"\n=== 개인 사용자 로그인 테스트 ===")
        print(f"Username: {username}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/auth/login",
                json={
                    "username": username,
                    "password": password,
                    "loginType": "personal"
                }
            )
            
            result = response.json()
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if result.get("success") and result.get("token"):
                self.token = result["token"]
                print(f"✅ 로그인 성공! 토큰 저장됨")
            else:
                print(f"❌ 로그인 실패")
                
            return result
    
    async def test_organization_login(self, username: str, password: str, session_code: str) -> Dict[str, Any]:
        """기관 사용자 로그인 테스트"""
        print(f"\n=== 기관 사용자 로그인 테스트 ===")
        print(f"Username: {username}")
        print(f"Session Code: {session_code}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/auth/login",
                json={
                    "username": username,
                    "password": password,
                    "loginType": "organization",
                    "sessionCode": session_code
                }
            )
            
            result = response.json()
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if result.get("success") and result.get("token"):
                self.token = result["token"]
                print(f"✅ 기관 로그인 성공! 토큰 저장됨")
            else:
                print(f"❌ 기관 로그인 실패")
                
            return result
    
    async def test_token_verification(self) -> Dict[str, Any]:
        """토큰 검증 테스트"""
        print(f"\n=== 토큰 검증 테스트 ===")
        
        if not self.token:
            print("❌ 토큰이 없습니다. 먼저 로그인하세요.")
            return {"error": "No token"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/auth/verify-token",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            result = response.json()
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if response.status_code == 200:
                print(f"✅ 토큰 검증 성공!")
            else:
                print(f"❌ 토큰 검증 실패")
                
            return result
    
    async def test_current_user_info(self) -> Dict[str, Any]:
        """현재 사용자 정보 조회 테스트"""
        print(f"\n=== 현재 사용자 정보 조회 테스트 ===")
        
        if not self.token:
            print("❌ 토큰이 없습니다. 먼저 로그인하세요.")
            return {"error": "No token"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/auth/me",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            result = response.json()
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if response.status_code == 200:
                print(f"✅ 사용자 정보 조회 성공!")
            else:
                print(f"❌ 사용자 정보 조회 실패")
                
            return result
    
    async def test_protected_chat_endpoint(self, user_id: str, question: str) -> Dict[str, Any]:
        """보호된 채팅 엔드포인트 테스트"""
        print(f"\n=== 보호된 채팅 엔드포인트 테스트 ===")
        print(f"User ID: {user_id}")
        print(f"Question: {question}")
        
        if not self.token:
            print("❌ 토큰이 없습니다. 먼저 로그인하세요.")
            return {"error": "No token"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat/question",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "user_id": user_id,
                    "question": question
                }
            )
            
            result = response.json()
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if response.status_code == 200:
                print(f"✅ 채팅 요청 성공!")
            else:
                print(f"❌ 채팅 요청 실패")
                
            return result
    
    async def test_unauthorized_access(self) -> Dict[str, Any]:
        """인증 없이 보호된 엔드포인트 접근 테스트"""
        print(f"\n=== 인증 없이 보호된 엔드포인트 접근 테스트 ===")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/auth/me")
            
            result = response.json()
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if response.status_code == 401:
                print(f"✅ 예상대로 401 Unauthorized 응답!")
            else:
                print(f"❌ 예상과 다른 응답")
                
            return result
    
    async def test_health_check(self) -> Dict[str, Any]:
        """인증 서비스 상태 확인"""
        print(f"\n=== 인증 서비스 상태 확인 ===")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/auth/health")
            
            result = response.json()
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if response.status_code == 200:
                print(f"✅ 인증 서비스 정상!")
            else:
                print(f"❌ 인증 서비스 문제 있음")
                
            return result

async def main():
    """메인 테스트 함수"""
    print("🚀 인증 시스템 테스트 시작")
    
    tester = AuthTester()
    
    # 1. 서비스 상태 확인
    await tester.test_health_check()
    
    # 2. 인증 없이 보호된 엔드포인트 접근 시도
    await tester.test_unauthorized_access()
    
    # 3. 개인 사용자 로그인 테스트 (실제 데이터베이스에 있는 계정으로 테스트)
    print("\n" + "="*50)
    print("실제 데이터베이스 계정으로 테스트하려면 아래 값들을 수정하세요:")
    print("개인 사용자 계정 정보를 입력하세요.")
    
    # 테스트용 계정 정보 (실제 데이터베이스에 맞게 수정 필요)
    personal_username = input("개인 사용자 ID를 입력하세요 (또는 Enter로 건너뛰기): ").strip()
    
    if personal_username:
        personal_password = input("비밀번호를 입력하세요: ").strip()
        
        if personal_password:
            login_result = await tester.test_personal_login(personal_username, personal_password)
            
            if login_result.get("success"):
                # 4. 토큰 검증
                await tester.test_token_verification()
                
                # 5. 현재 사용자 정보 조회
                user_info = await tester.test_current_user_info()
                
                # 6. 보호된 채팅 엔드포인트 테스트
                if user_info.get("user_id"):
                    await tester.test_protected_chat_endpoint(
                        user_info["user_id"], 
                        "안녕하세요, 제 성격 유형에 대해 알려주세요."
                    )
    
    # 7. 기관 로그인 테스트
    print("\n" + "="*50)
    print("기관 로그인 테스트")
    org_username = input("기관 사용자 ID를 입력하세요 (또는 Enter로 건너뛰기): ").strip()
    
    if org_username:
        org_password = input("비밀번호를 입력하세요: ").strip()
        session_code = input("세션코드를 입력하세요: ").strip()
        
        if org_password and session_code:
            await tester.test_organization_login(org_username, org_password, session_code)
    
    print("\n🎉 인증 시스템 테스트 완료!")
    print("\n📝 테스트 결과 요약:")
    print("- 인증 없이 보호된 엔드포인트 접근: 401 응답 확인")
    print("- 로그인 성공 시: JWT 토큰 발급 확인")
    print("- 토큰으로 보호된 엔드포인트 접근: 인증된 사용자만 접근 가능")
    print("- 사용자 정보 조회: 토큰에서 사용자 정보 추출")

if __name__ == "__main__":
    asyncio.run(main())