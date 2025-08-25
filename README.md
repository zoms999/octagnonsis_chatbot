# Octag AI 적성 분석 챗봇

## 1. 프로젝트 개요

Octag AI 챗봇은 사용자의 적성을 분석하고 관련 정보를 제공하는 지능형 대화형 AI 플랫폼입니다. Python(FastAPI) 기반의 강력한 백엔드 시스템과 Next.js 기반의 반응형 웹 프론트엔드로 구성되어 있습니다.

본 시스템은 마이크로서비스 지향 아키텍처를 채택하여, 인증, 채팅, ETL, RAG, 모니터링 등 각 기능이 독립적으로 개발 및 배포될 수 있도록 설계되었습니다. 데이터의 정확성, 보안, 안정적인 모니터링이 중요한 엔터프라이즈 환경에 최적화되어 있으며, 강력한 ETL 파이프라인과 RAG(Retrieval-Augmented Generation) 기반의 질의응답 시스템을 통해 높은 수준의 데이터 처리 능력과 지능적인 대화 능력을 제공합니다.

## 2. 시스템 아키텍처

본 프로젝트는 기능적으로 분리된 백엔드와 프론트엔드 아키텍처를 따릅니다.

- **Backend**: 데이터 처리, AI 모델 서빙, 비즈니스 로직, API 제공 등 핵심 기능을 담당합니다.
- **Frontend**: 사용자 인터페이스, 사용자 경험, 백엔드와의 통신을 담당합니다.

## 3. Backend (Octag AI 챗봇 시스템)

### 3.1. 주요 기능

- 🔐 **사용자 인증 (User Authentication)**: JWT (JSON Web Token) 기반의 안전한 사용자 인증 시스템을 제공하며, 토큰 발급, 재발급, 검증을 통해 인가된 사용자만 서비스에 접근할 수 있도록 제어합니다.
- 💬 **실시간 채팅 (Real-time Chat)**: WebSocket을 활용하여 사용자와 서버 간의 실시간 양방향 통신을 지원하여 원활한 대화 경험을 제공합니다.
- ⚙️ **ETL 파이프라인 (ETL Pipeline)**: 다양한 소스로부터 데이터를 추출(Extract), 변환(Transform), 적재(Load)하는 강력한 ETL 파이프라인을 갖추고 있습니다. 데이터 정제, 형식 변환, 벡터 임베딩 등 복잡한 데이터 처리 작업을 자동화하고 관리하며, 작업 상태 모니터링 및 오류 대응 기능을 포함합니다.
- 🧠 **RAG (Retrieval-Augmented Generation) 기반 질의응답**: RAG 기술을 도입하여, 방대한 데이터베이스에서 사용자의 질문과 관련된 정보를 신속하게 검색하고, 이를 바탕으로 정확하고 문맥에 맞는 답변을 생성합니다. 벡터 검색(Vector Search)을 통해 의미적으로 유사한 문서를 효율적으로 찾아내어 답변의 질을 높입니다.
- 🔧 **관리자 및 사용자 설정 (Admin & User Preferences)**: 관리자가 시스템의 주요 설정을 변경하고 모니터링할 수 있는 관리자 기능을 제공하며, 사용자별 맞춤 설정을 저장하고 관리하여 개인화된 챗봇 경험을 제공합니다.
- 📈 **모니터링 및 알림 (Monitoring & Alerting)**: 시스템의 주요 지표(Metric)를 실시간으로 수집하고 모니터링하며, 이상 발생 시 관리자에게 알림을 보내 신속한 대응을 가능하게 합니다.

### 3.2. 기술 스택

- **Language**: Python
- **Framework**: FastAPI (예상)
- **Database**: PostgreSQL (예상, Vector DB 기능 포함)
- **Real-time**: WebSockets
- **Authentication**: JWT

### 3.3. API 엔드포인트

- **Auth Endpoints**: `/api/auth/...` (로그인, 회원가입, 토큰 재발급 등)
- **Chat Endpoints**: `/api/chat/...` (채팅 메시지 전송 및 내역 관리)
- **ETL Endpoints**: `/api/etl/...` (ETL 작업 실행 및 상태 확인)
- **Admin/Preference Endpoints**: `/api/admin/...`, `/api/preferences/...` (관리자 기능 및 사용자 설정)
- **Monitoring Endpoints**: `/api/monitoring/...` (시스템 모니터링 데이터 조회)

### 3.4. 설치 및 실행

*참고: 아래의 실행 방법은 프로젝트 구조를 바탕으로 추론한 것이며, 실제 환경에 따라 일부 명령어는 수정이 필요할 수 있습니다.*

```bash
# 1. 가상 환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\activate  # Windows

# 2. 의존성 설치
pip install -r requirements.txt
pip install -r etl_requirements.txt

# 3. 데이터베이스 마이그레이션
python run_migration.py

# 4. 백엔드 서버 실행 (FastAPI 애플리케이션으로 가정)
uvicorn main:app --reload
```

## 4. Frontend (웹 애플리케이션)

### 4.1. 주요 기능

- 🔐 **사용자 인증**: 개인/조직 로그인 지원
- 💬 **실시간 채팅**: WebSocket 기반 AI 채팅
- 📊 **ETL 모니터링**: 데이터 처리 상태 실시간 추적
- 📝 **대화 기록**: 이전 대화 내용 조회
- 👤 **프로필 관리**: 사용자 정보 및 문서 관리
- 📱 **반응형 디자인**: 모바일/태블릿/데스크톱 지원
- 🧪 **테스트 및 디버깅**: `test-login.html`을 통한 간단한 로그인 테스트 및 다양한 테스트 유틸리티를 포함합니다.

### 4.2. 기술 스택

- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: React Query + React Context
- **Real-time**: WebSocket + Server-Sent Events

### 4.3. 설치 및 실행

```bash
# 1. front 디렉터리로 이동
cd front

# 2. 의존성 설치
npm install

# 3. 환경 변수 설정
cp .env.example .env.local

# 4. 개발 서버 실행
npm run dev
```

이제 브라우저에서 `http://localhost:3000` 으로 접속하여 애플리케이션을 확인할 수 있습니다.

## 5. 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다.
