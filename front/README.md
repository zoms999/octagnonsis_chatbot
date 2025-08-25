# AI 적성 분석 챗봇 Frontend

Next.js 기반의 AI 적성 분석 챗봇 웹 애플리케이션입니다.

## 기술 스택

- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: React Query + React Context
- **Real-time**: WebSocket + Server-Sent Events

## 시작하기

### 필수 요구사항

- Node.js 18.0.0 이상
- npm 또는 yarn

### 설치

1. 의존성 설치:
```bash
npm install
```

2. 환경 변수 설정:
```bash
cp .env.example .env.local
```

3. 개발 서버 실행:
```bash
npm run dev
```

4. 브라우저에서 [http://localhost:3000](http://localhost:3000) 접속

## 프로젝트 구조

```
src/
├── app/                    # Next.js App Router 페이지
│   ├── (auth)/            # 인증 관련 페이지
│   ├── (protected)/       # 보호된 페이지
│   ├── layout.tsx         # 루트 레이아웃
│   └── globals.css        # 글로벌 스타일
├── components/            # 재사용 가능한 컴포넌트
│   ├── ui/               # 기본 UI 컴포넌트
│   ├── auth/             # 인증 컴포넌트
│   ├── chat/             # 채팅 관련 컴포넌트
│   ├── etl/              # ETL 모니터링 컴포넌트
│   └── layout/           # 레이아웃 컴포넌트
├── lib/                  # 유틸리티 및 설정
├── hooks/                # 커스텀 React 훅
└── providers/            # Context 프로바이더
```

## 주요 기능

- 🔐 **사용자 인증**: 개인/조직 로그인 지원
- 💬 **실시간 채팅**: WebSocket 기반 AI 채팅
- 📊 **ETL 모니터링**: 데이터 처리 상태 실시간 추적
- 📝 **대화 기록**: 이전 대화 내용 조회
- 👤 **프로필 관리**: 사용자 정보 및 문서 관리
- 📱 **반응형 디자인**: 모바일/태블릿/데스크톱 지원

## 개발 스크립트

```bash
# 개발 서버 실행
npm run dev

# 프로덕션 빌드
npm run build

# 프로덕션 서버 실행
npm run start

# 린팅
npm run lint

# 타입 체크
npm run type-check
```

## 환경 변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `NEXT_PUBLIC_API_BASE` | API 서버 URL | `http://localhost:8000` |
| `NEXT_PUBLIC_WS_BASE` | WebSocket 서버 URL | `ws://localhost:8000` |
| `NEXT_PUBLIC_ADMIN_TOKEN` | 관리자 토큰 (선택사항) | - |

## 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다.