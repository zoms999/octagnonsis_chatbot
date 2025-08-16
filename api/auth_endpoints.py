"""
FastAPI Authentication Endpoints
로그인 기능을 위한 API endpoints - NextJS 백엔드 로직을 Python으로 포팅
"""

import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from passlib.context import CryptContext
import jwt

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, environment variables should be set externally
    pass

from database.connection import get_async_session

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# JWT 설정
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Password context for verification
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

import re
from typing import Optional

TOKEN_REGEX = re.compile(r'^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$')

# Security scheme with soft error handling
security = HTTPBearer(auto_error=False)

# Pydantic models
class LoginRequest(BaseModel):
    """로그인 요청 모델"""
    username: str = Field(..., description="사용자 ID")
    password: str = Field(..., description="비밀번호")
    loginType: str = Field(..., description="로그인 타입: personal, organization")
    sessionCode: Optional[str] = Field(None, description="기관 로그인용 세션코드")

class PersonalUserInfo(BaseModel):
    """개인 사용자 정보"""
    id: str
    name: str
    type: str = "personal"
    sex: str
    isPaid: bool
    productType: str
    isExpired: bool
    state: str
    ac_id: str

class OrganizationAdminInfo(BaseModel):
    """기관 관리자 정보"""
    id: str
    name: str
    type: str = "organization_admin"
    sessionCode: str
    ac_id: str
    ins_seq: int

class OrganizationMemberInfo(BaseModel):
    """기관 소속 사용자 정보"""
    id: str
    name: str
    type: str = "organization_member"
    sessionCode: str
    ac_id: str

class AuthTokens(BaseModel):
    """인증 토큰 모델"""
    access: str
    refresh: str

class LoginResponse(BaseModel):
    """로그인 응답 모델"""
    success: bool
    message: str
    user: Optional[Union[PersonalUserInfo, OrganizationAdminInfo, OrganizationMemberInfo]] = None
    tokens: Optional[AuthTokens] = None
    expires_at: Optional[str] = None

class TokenPayload(BaseModel):
    """JWT 토큰 페이로드"""
    user_id: str
    user_type: str
    ac_id: str
    exp: int
    iat: int

# 유틸리티 함수들
def create_access_token(user_data: Dict[str, Any]) -> str:
    """JWT 액세스 토큰 생성"""
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "user_id": user_data["id"],
        "user_type": user_data["type"],
        "ac_id": user_data["ac_id"],
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """JWT 토큰 검증: (payload, error_message) 반환"""
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat"]},
            leeway=60
        )
        if payload.get("type") == "refresh":
            return None, "Authorization 헤더에는 access 토큰만 사용할 수 있습니다."
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, "토큰이 만료되었습니다."
    except jwt.InvalidSignatureError:
        return None, "토큰 서명이 유효하지 않습니다."
    except jwt.DecodeError:
        return None, "토큰을 해석할 수 없습니다."
    except Exception:
        return None, "유효하지 않은 토큰입니다."

async def log_login_attempt(db: AsyncSession, ac_gid: str, success: bool = True):
    """로그인 시도 로그 기록"""
    try:
        user_agent_json = json.dumps({"source": "Python API Login"})
        
        if success:
            await db.execute(
                text("""
                    INSERT INTO mwd_log_login_account (login_date, user_agent, ac_gid) 
                    VALUES (now(), CAST(:user_agent AS json), CAST(:ac_gid AS uuid))
                """),
                {"user_agent": user_agent_json, "ac_gid": ac_gid}
            )
        
        await db.commit()
        logger.info(f"로그인 로그 기록 완료: {ac_gid}")
        
    except Exception as e:
        logger.error(f"로그인 로그 기록 실패: {e}")
        # 로그 기록 실패는 로그인 진행에 영향 없음

# 인증 의존성
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """현재 사용자 정보 가져오기"""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Authorization 헤더가 누락되었거나 형식이 잘못되었습니다. 예) Bearer <access_token>'
        )
    raw = (credentials.credentials or "").strip()
    if not TOKEN_REGEX.match(raw):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='잘못된 토큰 형식입니다. Authorization에는 access 토큰만 넣으세요. 예) Bearer <access_token>'
        )
    payload, err = verify_token(raw)
    if err is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=err
        )
    return payload

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="사용자 로그인",
    description="개인 사용자 또는 기관 사용자 로그인 처리"
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_async_session)
) -> LoginResponse:
    """
    사용자 로그인 처리
    
    NextJS 백엔드의 authorize 함수를 Python으로 포팅한 버전
    개인 사용자와 기관 사용자(관리자/소속원) 로그인을 모두 지원
    """
    logger.info(f"로그인 시도 시작: username={request.username}, loginType={request.loginType}")
    
    try:
        # 1. 개인 사용자 로그인
        if request.loginType == "personal":
            logger.info(f"개인 사용자 로그인 시도: {request.username}")
            
            try:
                # 계정 정보 조회
                account_result = await db.execute(
                    text("""
                        SELECT pe.pe_seq, pe.pe_name, ac.ac_gid, ac.ac_use, ac.ac_id
                        FROM mwd_person pe
                        JOIN mwd_account ac ON ac.pe_seq = pe.pe_seq 
                        WHERE ac.ac_id = lower(:username) 
                        AND ac.ac_pw = CRYPT(:password, ac.ac_pw)
                    """),
                    {"username": request.username, "password": request.password}
                )
            except Exception as db_error:
                logger.error(f"데이터베이스 쿼리 오류: {db_error}")
                return LoginResponse(
                    success=False,
                    message="데이터베이스 연결 오류가 발생했습니다."
                )
            
            account_row = account_result.fetchone()
            
            if not account_row or account_row.ac_use != 'Y':
                logger.info("로그인 실패: 계정 정보 없음 또는 비활성화된 계정")
                return LoginResponse(
                    success=False,
                    message="아이디 또는 비밀번호가 올바르지 않습니다."
                )
            
            pe_seq, pe_name, ac_gid, ac_use, ac_id = account_row
            
            # 기관 관리자 계정인지 확인 (pe_seq = -1인 경우)
            if pe_seq == -1:
                logger.info(f"기관 관리자 계정이 일반 로그인 시도함: {ac_id}")
                return LoginResponse(
                    success=False,
                    message="기관 관리자 계정은 기관 로그인을 사용해주세요."
                )
            
            # 기관 소속 사용자인지 확인
            institute_check = await db.execute(
                text("""
                    SELECT COUNT(*) as count
                    FROM mwd_institute_member im
                    WHERE im.pe_seq = :pe_seq
                """),
                {"pe_seq": pe_seq}
            )
            
            institute_count = institute_check.fetchone().count
            
            if institute_count > 0:
                logger.info(f"기관 소속 사용자가 일반 로그인 시도함: {ac_id}")
                return LoginResponse(
                    success=False,
                    message="기관 소속 사용자는 기관 로그인을 사용해주세요."
                )
            
            # 로그인 로그 기록
            await log_login_attempt(db, str(ac_gid), True)
            
            # 결제 상태 확인
            payment_result = await db.execute(
                text("""
                    SELECT cr_pay, pd_kind, expire, state FROM (
                        SELECT ac.ac_gid, row_number() OVER (ORDER BY cr.cr_seq DESC) rnum,
                               COALESCE(cr.cr_pay, 'N') cr_pay, 
                               COALESCE(cr.pd_kind, '') pd_kind,
                               CASE WHEN ac.ac_expire_date >= now() THEN 'Y' ELSE 'N' END expire,
                               COALESCE(ap.anp_done, 'R') state
                        FROM mwd_person pe, mwd_account ac
                        LEFT OUTER JOIN mwd_choice_result cr ON cr.ac_gid = ac.ac_gid
                        LEFT OUTER JOIN mwd_answer_progress ap ON ap.cr_seq = cr.cr_seq
                        WHERE ac.ac_gid = CAST(:ac_gid AS uuid)
                        AND pe.pe_seq = ac.pe_seq AND ac.ac_use = 'Y'
                    ) t WHERE rnum = 1
                """),
                {"ac_gid": str(ac_gid)}
            )
            
            payment_row = payment_result.fetchone()
            
            # 성별 정보 조회
            gender_result = await db.execute(
                text("""
                    SELECT pe.pe_sex 
                    FROM mwd_account ac, mwd_person pe 
                    WHERE ac.ac_gid = CAST(:ac_gid AS uuid)
                    AND pe.pe_seq = ac.pe_seq
                """),
                {"ac_gid": str(ac_gid)}
            )
            
            gender_row = gender_result.fetchone()
            
            # 사용자 정보 구성
            user_info = PersonalUserInfo(
                id=str(ac_gid),
                name=pe_name,
                sex=gender_row.pe_sex if gender_row else "",
                isPaid=payment_row.cr_pay == 'Y' if payment_row else False,
                productType=payment_row.pd_kind if payment_row else "",
                isExpired=payment_row.expire == 'N' if payment_row else True,
                state=payment_row.state if payment_row else "R",
                ac_id=ac_id
            )
            
            # JWT 토큰 생성
            access_token = create_access_token(user_info.dict())
            expires_at = (datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)).isoformat()
            
            # 토큰 객체 생성 (refresh token은 현재 access token과 동일하게 설정)
            tokens = AuthTokens(access=access_token, refresh=access_token)
            
            logger.info(f"개인 로그인 성공: {user_info.id}")
            
            return LoginResponse(
                success=True,
                message="로그인 성공",
                user=user_info,
                tokens=tokens,
                expires_at=expires_at
            )
        
        # 2. 기관 로그인 (관리자 또는 소속 사용자)
        elif request.loginType == "organization":
            logger.info(f"기관 로그인 시도: username={request.username}")
            
            if not request.sessionCode:
                return LoginResponse(
                    success=False,
                    message="세션코드가 필요합니다."
                )
            
            # 회차코드 유효성 검사
            turn_result = await db.execute(
                text("""
                    SELECT tur.ins_seq, tur.tur_seq
                    FROM mwd_institute_turn tur
                    WHERE tur.tur_code = :session_code AND tur.tur_use = 'Y'
                """),
                {"session_code": request.sessionCode}
            )
            
            turn_row = turn_result.fetchone()
            
            if not turn_row:
                logger.info("세션코드 검증 실패: 유효하지 않은 코드")
                return LoginResponse(
                    success=False,
                    message="유효하지 않은 세션코드입니다."
                )
            
            ins_seq, tur_seq = turn_row
            
            # 기관 관리자로 로그인 시도 (1순위)
            admin_result = await db.execute(
                text("""
                    SELECT i.ins_seq, i.ins_manager1_name, ac.ac_gid, ac.ac_use, ac.ac_id
                    FROM mwd_institute i
                    JOIN mwd_account ac ON ac.ins_seq = i.ins_seq
                    WHERE ac.pe_seq = -1
                    AND ac.ins_seq = :ins_seq
                    AND ac.ac_id = lower(:username)
                    AND ac.ac_pw = CRYPT(:password, ac.ac_pw)
                """),
                {"ins_seq": ins_seq, "username": request.username, "password": request.password}
            )
            
            admin_row = admin_result.fetchone()
            
            if admin_row and admin_row.ac_use == 'Y':
                admin_info = OrganizationAdminInfo(
                    id=str(admin_row.ac_gid),
                    name=admin_row.ins_manager1_name,
                    sessionCode=request.sessionCode,
                    ac_id=admin_row.ac_id,
                    ins_seq=admin_row.ins_seq
                )
                
                # JWT 토큰 생성
                access_token = create_access_token(admin_info.dict())
                expires_at = (datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)).isoformat()
                
                # 토큰 객체 생성
                tokens = AuthTokens(access=access_token, refresh=access_token)
                
                logger.info(f"기관 관리자 로그인 성공: {admin_info.id}")
                
                return LoginResponse(
                    success=True,
                    message="기관 관리자 로그인 성공",
                    user=admin_info,
                    tokens=tokens,
                    expires_at=expires_at
                )
            
            # 기관 소속 개인 사용자로 로그인 시도 (2순위)
            member_result = await db.execute(
                text("""
                    SELECT pe.pe_seq, pe.pe_name, ac.ac_gid, ac.ac_use, ac.ac_id
                    FROM mwd_person pe
                    JOIN mwd_account ac ON ac.pe_seq = pe.pe_seq
                    JOIN mwd_institute_member im ON im.pe_seq = pe.pe_seq
                    WHERE ac.ac_id = lower(:username)
                    AND ac.ac_pw = CRYPT(:password, ac.ac_pw)
                    AND im.ins_seq = :ins_seq
                    AND im.tur_seq = :tur_seq
                """),
                {
                    "username": request.username, 
                    "password": request.password,
                    "ins_seq": ins_seq,
                    "tur_seq": tur_seq
                }
            )
            
            member_row = member_result.fetchone()
            
            if member_row and member_row.ac_use == 'Y':
                # 로그인 로그 기록
                await log_login_attempt(db, str(member_row.ac_gid), True)
                
                member_info = OrganizationMemberInfo(
                    id=str(member_row.ac_gid),
                    name=member_row.pe_name,
                    sessionCode=request.sessionCode,
                    ac_id=member_row.ac_id
                )
                
                # JWT 토큰 생성
                access_token = create_access_token(member_info.dict())
                expires_at = (datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)).isoformat()
                
                # 토큰 객체 생성
                tokens = AuthTokens(access=access_token, refresh=access_token)
                
                logger.info(f"기관 소속 사용자 로그인 성공: {member_info.id}")
                
                return LoginResponse(
                    success=True,
                    message="기관 소속 사용자 로그인 성공",
                    user=member_info,
                    tokens=tokens,
                    expires_at=expires_at
                )
            
            logger.info("기관 로그인 실패: 일치하는 계정 정보 없음")
            return LoginResponse(
                success=False,
                message="아이디, 비밀번호 또는 세션코드가 올바르지 않습니다."
            )
        
        else:
            logger.info(f"로그인 실패: 지원하지 않는 로그인 타입: {request.loginType}")
            return LoginResponse(
                success=False,
                message="지원하지 않는 로그인 타입입니다."
            )
    
    except Exception as e:
        logger.error(f"로그인 처리 중 오류: {e}", exc_info=True)
        return LoginResponse(
            success=False,
            message=f"로그인 처리 중 오류가 발생했습니다: {str(e)}"
        )

@router.post(
    "/verify-token",
    summary="토큰 검증",
    description="JWT 토큰의 유효성을 검증합니다"
)
async def verify_user_token(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """JWT 토큰 검증 및 사용자 정보 반환"""
    return {
        "valid": True,
        "user": current_user,
        "message": "토큰이 유효합니다"
    }

class TokenBody(BaseModel):
    token: str = Field(..., description="검증할 access 토큰")

@router.post("/verify-token-body", summary="바디로 토큰 검증(디버깅용)")
async def verify_user_token_body(payload: TokenBody) -> Dict[str, Any]:
    token = payload.token.strip()
    if not TOKEN_REGEX.match(token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="JWT 형식이 아닙니다."
        )
    data, err = verify_token(token)
    if err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=err)
    return {"valid": True, "user": data, "message": "토큰이 유효합니다"}

@router.post(
    "/logout",
    summary="로그아웃",
    description="사용자 로그아웃 처리"
)
async def logout(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    로그아웃 처리
    
    현재는 클라이언트 측에서 토큰을 삭제하도록 안내
    향후 토큰 블랙리스트 기능 추가 가능
    """
    logger.info(f"사용자 로그아웃: {current_user.get('user_id')}")
    
    return {
        "success": True,
        "message": "로그아웃되었습니다. 클라이언트에서 토큰을 삭제해주세요."
    }

@router.get(
    "/me",
    summary="현재 사용자 정보",
    description="현재 로그인한 사용자의 정보를 반환합니다"
)
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """현재 로그인한 사용자의 상세 정보 반환"""
    try:
        user_id = current_user["user_id"]
        user_type = current_user["user_type"]
        
        if user_type == "personal":
            # 개인 사용자 정보 조회
            result = await db.execute(
                text("""
                    SELECT pe.pe_name, ac.ac_id, pe.pe_sex
                    FROM mwd_account ac
                    JOIN mwd_person pe ON pe.pe_seq = ac.pe_seq
                    WHERE ac.ac_gid = CAST(:user_id AS uuid)
                """),
                {"user_id": user_id}
            )
            
            row = result.fetchone()
            if row:
                return {
                    "user_id": user_id,
                    "name": row.pe_name,
                    "ac_id": row.ac_id,
                    "type": user_type,
                    "sex": row.pe_sex
                }
        
        elif user_type in ["organization_admin", "organization_member"]:
            # 기관 사용자 정보 조회
            if user_type == "organization_admin":
                result = await db.execute(
                    text("""
                        SELECT i.ins_manager1_name as name, ac.ac_id
                        FROM mwd_account ac
                        JOIN mwd_institute i ON i.ins_seq = ac.ins_seq
                        WHERE ac.ac_gid = CAST(:user_id AS uuid) AND ac.pe_seq = -1
                    """),
                    {"user_id": user_id}
                )
            else:
                result = await db.execute(
                    text("""
                        SELECT pe.pe_name as name, ac.ac_id
                        FROM mwd_account ac
                        JOIN mwd_person pe ON pe.pe_seq = ac.pe_seq
                        WHERE ac.ac_gid = CAST(:user_id AS uuid)
                    """),
                    {"user_id": user_id}
                )
            
            row = result.fetchone()
            if row:
                return {
                    "user_id": user_id,
                    "name": row.name,
                    "ac_id": row.ac_id,
                    "type": user_type
                }
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자 정보를 찾을 수 없습니다"
        )
        
    except Exception as e:
        logger.error(f"사용자 정보 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 정보 조회 중 오류가 발생했습니다"
        )

@router.get(
    "/health",
    summary="인증 서비스 상태 확인",
    description="인증 서비스의 상태를 확인합니다"
)
async def auth_health_check(
    db: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """인증 서비스 상태 확인"""
    try:
        # 데이터베이스 연결 확인
        result = await db.execute(text("SELECT 1 as test"))
        test_value = result.scalar()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "database": "healthy" if test_value == 1 else "unhealthy",
                "jwt": "healthy"
            }
        }
    except Exception as e:
        logger.error(f"인증 서비스 상태 확인 실패: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@router.post(
    "/test-login",
    summary="테스트 로그인 (데이터베이스 없이)",
    description="데이터베이스 연결 없이 로그인 로직을 테스트합니다"
)
async def test_login(request: LoginRequest) -> LoginResponse:
    """데이터베이스 연결 없이 로그인 테스트"""
    logger.info(f"테스트 로그인 시도: username={request.username}, loginType={request.loginType}")
    
    # 하드코딩된 테스트 사용자
    if request.username == "test999" and request.password == "111111" and request.loginType == "personal":
        user_info = PersonalUserInfo(
            id="test-user-id",
            name="테스트 사용자",
            sex="M",
            isPaid=True,
            productType="premium",
            isExpired=False,
            state="C",
            ac_id="test999"
        )
        
        access_token = create_access_token(user_info.dict())
        expires_at = (datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)).isoformat()
        
        # 토큰 객체 생성
        tokens = AuthTokens(access=access_token, refresh=access_token)
        
        return LoginResponse(
            success=True,
            message="테스트 로그인 성공",
            user=user_info,
            tokens=tokens,
            expires_at=expires_at
        )
    
    return LoginResponse(
        success=False,
        message="테스트 로그인 실패: test999/111111을 사용하세요"
    )