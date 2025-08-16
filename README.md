# Aptitude Chatbot RAG 시스템

이 문서는 정적인 적성 검사 보고서를 RAG(Retrieval-Augmented Generation) 기술을 활용하여 동적이고 상호작용적인 대화형 AI 시스템으로 전환하는 Aptitude Chatbot RAG 시스템에 대한 상세한 설명을 제공합니다.

## 프로젝트 개요

Aptitude Chatbot RAG 시스템은 사용자의 적성 검사 결과를 분석하여 개인의 성격 유형, 사고 능력, 그리고 직업 추천에 대한 자연어 대화를 가능하게 하는 지능형 대화형 AI 시스템입니다. 이 시스템은 원시 테스트 데이터를 벡터 검색에 최적화된 의미론적 문서로 변환하고, 이를 통해 사용자가 자신의 프로필에 대해 깊이 있고 상호작용적인 대화를 나눌 수 있도록 지원합니다.

## 주요 기능 및 특징

*   **개인화된 대화 경험**: 사용자의 적성 검사 결과를 기반으로 맞춤형 대화를 제공하여, 자신의 강점과 약점을 더 잘 이해하고 미래 계획을 세울 수 있도록 돕습니다.
*   **정확하고 신뢰할 수 있는 정보**: RAG 기술을 통해 관련성 높은 문서를 검색하고 이를 기반으로 응답을 생성하여, 정확하고 신뢰할 수 있는 정보를 제공합니다.
*   **확장 가능한 아키텍처**: 모듈화된 구성 요소를 통해 시스템의 유연성과 확장성을 보장하며, 향후 기능 추가 및 성능 개선이 용이합니다.
*   **보안 및 사용자 관리**: JWT 기반 인증 시스템을 통해 개인 및 조직 사용자의 데이터를 안전하게 보호하고 관리합니다.

## 시스템 아키텍처

Aptitude Chatbot RAG 시스템은 다음과 같은 핵심 구성 요소로 이루어져 있습니다.

*   **인증 시스템 (Authentication System)**: JWT(JSON Web Token) 기반의 인증 시스템으로, 개인 사용자 및 조직 사용자를 모두 지원합니다. 사용자 로그인, 토큰 발급 및 검증, 사용자 정보 관리 등의 기능을 담당합니다.
*   **ETL 파이프라인 (ETL Pipeline)**: 원시 적성 검사 데이터를 추출(Extract), 변환(Transform), 적재(Load)하여 벡터 검색에 최적화된 의미론적 문서로 만듭니다. 이 과정에서 데이터는 정규화되고 임베딩을 위한 형태로 가공됩니다.
*   **벡터 데이터베이스 (Vector Database)**: PostgreSQL과 `pgvector` 확장을 사용하여 벡터 임베딩을 저장하고 관리합니다. 이를 통해 고차원 벡터 공간에서 효율적인 유사성 검색을 수행할 수 있습니다.
*   **RAG 엔진 (RAG Engine)**: Google Gemini 모델을 활용하여 문서 임베딩을 생성하고, 검색된 문서를 기반으로 사용자 질문에 대한 응답을 생성합니다. 이는 검색(Retrieval)과 생성(Generation)을 결합하여 답변의 정확성과 유창성을 높입니다.
*   **API 레이어 (API Layer)**: FastAPI 프레임워크를 사용하여 RESTful API 엔드포인트와 WebSocket 지원을 제공합니다. 프론트엔드 애플리케이션 및 다른 서비스와의 통신을 담당합니다.

## 데이터베이스 설정

### 전제 조건

1.  PostgreSQL 14+ 및 `pgvector` 확장
2.  Python 3.9+
3.  `requirements.txt`에 명시된 Python 패키지

### 설치 방법

1.  **의존성 설치**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **환경 설정**:
    ```bash
    cp .env.example .env
    # .env 파일을 열어 데이터베이스 자격 증명을 설정합니다.
    ```

3.  **데이터베이스 설정**:
    ```bash
    python scripts/setup_database.py
    ```

### 수동 데이터베이스 설정 (선택 사항)

수동으로 데이터베이스를 설정하려면 다음 단계를 따르세요.

1.  **데이터베이스 생성**:
    ```sql
    CREATE DATABASE aptitude_chatbot;
    ```

2.  **pgvector 확장 활성화**:
    ```sql
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    ```

3.  **마이그레이션 실행**:
    ```bash
    python database/migration_manager.py migrate
    ```

## 데이터베이스 스키마

### 핵심 테이블

*   **chat_users**: 사용자 관리 및 테스트 완료 추적
*   **chat_documents**: 벡터 임베딩을 포함한 의미론적 문서
*   **chat_jobs**: 직업 정보 및 경력 매칭 벡터
*   **chat_majors**: 학과 데이터 및 유사성 벡터
*   **chat_conversations**: 채팅 기록 및 컨텍스트 추적

### 벡터 검색

시스템은 효율적인 유사성 검색을 위해 HNSW 인덱스와 함께 `pgvector`를 사용합니다.

*   768차원 벡터 (Google Gemini 임베딩 크기)
*   문서 매칭을 위한 코사인 유사도
*   서브-초 검색 성능에 최적화

## 테스트

데이터베이스 설정 테스트를 실행합니다.

```bash
pytest tests/test_database_setup.py -v
```

## 마이그레이션 관리

마이그레이션 상태 확인:
```bash
python database/migration_manager.py status
```

대기 중인 마이그레이션 실행:
```bash
python database/migration_manager.py migrate
```

마이그레이션 롤백:
```bash
python database/migration_manager.py rollback 001
```

## 환경 변수

| 변수 | 설명 | 기본값 |
|----------|-------------|---------|
| DB_HOST | 데이터베이스 호스트 | localhost |
| DB_PORT | 데이터베이스 포트 | 5432 |
| DB_NAME | 데이터베이스 이름 | aptitude_chatbot |
| DB_USER | 데이터베이스 사용자 | postgres |
| DB_PASSWORD | 데이터베이스 비밀번호 | (필수) |
| DB_POOL_SIZE | 연결 풀 크기 | 10 |
| DB_ECHO | SQL 로깅 활성화 | false |
| JWT_SECRET_KEY | JWT 서명 비밀 키 | (필수) |
| JWT_ALGORITHM | JWT 알고리즘 | HS256 |
| JWT_EXPIRATION_HOURS | 토큰 만료 시간 (시간) | 24 |
| ADMIN_TOKEN | 관리자 접근 토큰 | (선택 사항) |
| AUTH_DISABLED | 인증 비활성화 | false |

## API 사용법

### 인증

시스템은 두 가지 유형의 로그인을 지원합니다.

#### 1. 개인 사용자 로그인
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password",
    "loginType": "personal"
  }'
```

#### 2. 조직 사용자 로그인
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password",
    "loginType": "organization",
    "sessionCode": "your_session_code"
  }'
```

#### 3. JWT 토큰 사용
성공적인 로그인 후, 다음 요청에서 JWT 토큰을 사용합니다.

```bash
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 채팅 API

#### 질문하기
```bash
curl -X POST "http://localhost:8000/api/chat/question" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your_user_id",
    "question": "제 성격 유형에 대해 알려주세요"
  }'
```

#### 대화 기록 가져오기
```bash
curl -X GET "http://localhost:8000/api/chat/history/your_user_id" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 인증 테스트

인증 테스트 스크립트를 실행합니다.

```bash
python test_auth_system.py
```

이 스크립트는 다음 테스트를 안내합니다.
*   개인 및 조직 로그인
*   토큰 검증
*   보호된 엔드포인트 접근
*   사용자 정보 검색

## 다음 단계

데이터베이스 설정을 완료한 후, 다음 단계를 진행할 수 있습니다.

1.  **Task 2**: 핵심 데이터 모델 및 유효성 검사 구현
2.  **Task 3**: ETL 파이프라인 기반 구축
3.  **Task 4**: 문서 저장 및 검색 시스템 구현

전체 구현 계획은 `.kiro/specs/aptitude-chatbot-rag-system/tasks.md`에서 확인할 수 있습니다.
