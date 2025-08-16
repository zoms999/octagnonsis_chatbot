# Design Document

## Overview

적성검사 기반 지능형 챗봇의 Next.js 프론트엔드는 사용자가 적성검사 결과에 대해 AI와 대화하고 테스트 결과를 관리할 수 있는 현대적인 웹 애플리케이션입니다. 백엔드 Python FastAPI와 연동하여 인증, 실시간 채팅, ETL 처리 상태 모니터링 기능을 제공합니다.

## Architecture

### 기술 스택
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS + shadcn/ui
- **State Management**: Zustand
- **Authentication**: JWT (Access/Refresh tokens)
- **Real-time Communication**: Server-Sent Events (SSE) + Fetch API
- **Code Quality**: ESLint + Prettier

### 폴더 구조
```
src/
├── app/                    # Next.js App Router
│   ├── (auth)/            # 인증 관련 페이지
│   │   └── login/
│   ├── (dashboard)/       # 메인 대시보드
│   │   ├── chat/
│   │   └── tests/
│   ├── api/               # API 라우트 핸들러
│   ├── globals.css
│   └── layout.tsx
├── components/            # 재사용 가능한 컴포넌트
│   ├── ui/               # shadcn/ui 컴포넌트
│   ├── auth/             # 인증 관련 컴포넌트
│   ├── chat/             # 채팅 관련 컴포넌트
│   ├── tests/            # 테스트 관련 컴포넌트
│   └── common/           # 공통 컴포넌트
├── lib/                  # 유틸리티 및 설정
│   ├── api/              # API 클라이언트
│   ├── auth/             # 인증 로직
│   ├── stores/           # Zustand 스토어
│   └── utils/            # 유틸리티 함수
├── types/                # TypeScript 타입 정의
└── hooks/                # 커스텀 React 훅
```

## Components and Interfaces

### 1. 인증 시스템

#### AuthStore (Zustand)
```typescript
interface AuthState {
  user: User | null;
  tokens: {
    access: string | null;
    refresh: string | null;
  };
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
  checkAuth: () => Promise<void>;
}
```

#### LoginForm Component
- 개인/기관 로그인 타입 선택
- 폼 검증 및 에러 처리
- 로딩 상태 관리

### 2. 채팅 시스템

#### ChatStore (Zustand)
```typescript
interface ChatState {
  conversations: Conversation[];
  currentConversation: string | null;
  isStreaming: boolean;
  sendMessage: (message: string) => Promise<void>;
  loadHistory: () => Promise<void>;
  clearConversation: () => void;
}
```

#### ChatInterface Component
- 메시지 입력 및 전송
- 스트리밍 응답 처리
- 대화 히스토리 표시
- 타이핑 인디케이터

#### MessageBubble Component
- 사용자/AI 메시지 구분
- 마크다운 렌더링
- 복사 기능

### 3. 테스트 결과 시스템

#### TestStore (Zustand)
```typescript
interface TestState {
  tests: TestResult[];
  currentTest: TestResult | null;
  processingJobs: ProcessingJob[];
  loadTests: () => Promise<void>;
  reprocessTest: (testId: string) => Promise<void>;
  monitorJob: (jobId: string) => void;
}
```

#### TestResultsList Component
- 테스트 목록 표시
- 상태별 필터링
- 재처리 기능

#### TestProgressMonitor Component
- 실시간 진행률 표시 (SSE)
- 에러 상태 처리
- 취소/재시도 기능

### 4. 공통 컴포넌트

#### Layout Components
- AppLayout: 전체 레이아웃
- Navigation: 탭 네비게이션
- Header: 사용자 정보 및 로그아웃

#### UI Components (shadcn/ui 기반)
- Button, Input, Card, Dialog
- Toast 알림 시스템
- Loading Spinner
- Error Boundary

## Data Models

### User Types
```typescript
interface PersonalUser {
  id: string;
  name: string;
  type: 'personal';
  sex: string;
  isPaid: boolean;
  productType: string;
  isExpired: boolean;
  state: string;
  ac_id: string;
}

interface OrganizationUser {
  id: string;
  name: string;
  type: 'organization_admin' | 'organization_member';
  sessionCode: string;
  ac_id: string;
  ins_seq?: number;
}
```

### Chat Types
```typescript
interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: string;
  isStreaming?: boolean;
}

interface Conversation {
  id: string;
  messages: Message[];
  createdAt: string;
  updatedAt: string;
}

interface ChatResponse {
  conversation_id: string;
  response: string;
  retrieved_documents: DocumentReference[];
  confidence_score: number;
  processing_time: number;
}
```

### Test Types
```typescript
interface TestResult {
  id: string;
  userId: string;
  anpSeq: number;
  status: 'completed' | 'processing' | 'failed';
  completedAt: string;
  documents: TestDocument[];
}

interface TestDocument {
  id: string;
  type: DocumentType;
  summary: string;
  contentPreview: Record<string, any>;
  createdAt: string;
}

interface ProcessingJob {
  jobId: string;
  status: JobStatus;
  progress: number;
  currentStep: string;
  estimatedCompletion: string;
  errorMessage?: string;
}
```

## Error Handling

### Error Types
```typescript
interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
}

interface NetworkError extends Error {
  isNetworkError: true;
  retryable: boolean;
}

interface AuthError extends Error {
  isAuthError: true;
  requiresLogin: boolean;
}
```

### Error Handling Strategy
1. **API 에러**: 상태 코드별 처리 및 사용자 친화적 메시지
2. **네트워크 에러**: 재시도 로직 및 오프라인 상태 표시
3. **인증 에러**: 자동 토큰 갱신 및 로그인 리다이렉트
4. **스트리밍 에러**: 연결 재시도 및 부분 응답 복구

### Error Boundary
- 컴포넌트 레벨 에러 캐치
- 에러 리포팅
- 폴백 UI 제공

## Testing Strategy

### Unit Testing
- 컴포넌트 렌더링 테스트
- 스토어 로직 테스트
- 유틸리티 함수 테스트
- API 클라이언트 테스트

### Integration Testing
- 인증 플로우 테스트
- 채팅 기능 테스트
- 테스트 결과 조회 테스트

### E2E Testing
- 로그인부터 채팅까지 전체 플로우
- 다양한 사용자 시나리오
- 에러 상황 처리

## Security Considerations

### Token Management
- 액세스 토큰: 메모리 저장 (XSS 방지)
- 리프레시 토큰: HttpOnly 쿠키 (CSRF 방지)
- 자동 토큰 갱신 로직

### API Security
- CORS 설정
- Rate limiting 처리
- 입력 검증 및 sanitization

### Environment Variables
```typescript
// 런타임 환경변수 (public)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

// 서버사이드 환경변수 (private)
JWT_SECRET_KEY=your-secret-key
ADMIN_TOKEN=admin-token
```

## Performance Optimizations

### Code Splitting
- 페이지별 코드 분할
- 컴포넌트 lazy loading
- 동적 import 활용

### Caching Strategy
- API 응답 캐싱 (React Query 또는 SWR)
- 이미지 최적화
- 정적 자산 캐싱

### Bundle Optimization
- Tree shaking
- 불필요한 의존성 제거
- 번들 크기 모니터링

## Accessibility Features

### ARIA Support
- 적절한 ARIA 라벨
- 키보드 네비게이션
- 스크린 리더 지원

### Visual Accessibility
- 색상 대비 준수
- 폰트 크기 조절 가능
- 다크/라이트 테마 지원

### Interaction Accessibility
- 포커스 관리
- 키보드 단축키
- 에러 메시지 접근성

## Responsive Design

### Breakpoints
- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

### Layout Adaptations
- 모바일: 단일 컬럼, 풀스크린 채팅
- 태블릿: 사이드바 축소, 터치 최적화
- 데스크톱: 멀티 컬럼, 키보드 최적화

## Real-time Features

### Server-Sent Events (SSE)
- 채팅 응답 스트리밍
- ETL 진행률 업데이트
- 실시간 알림

### Connection Management
- 자동 재연결 로직
- 연결 상태 표시
- 오프라인 모드 지원

## Monitoring and Analytics

### Error Tracking
- 클라이언트 에러 로깅
- 성능 메트릭 수집
- 사용자 행동 분석

### Performance Monitoring
- 페이지 로드 시간
- API 응답 시간
- 번들 크기 추적