# APTIT 프로젝트 디자인 시스템 및 폰트 가이드

## 1. 디자인 컨셉
- **프로젝트명**: APTIT (적성검사 플랫폼)
- **기술 스택**: Next.js 15, TypeScript, Tailwind CSS, Prisma
- **디자인 컨셉**: 모던 글래스모피즘 + 그라데이션 기반의 신뢰감 있는 검사 플랫폼

---

## 2. 폰트 시스템 (Font System)

### 2.1. 기본 폰트 정책
- **주요 폰트**: **나눔스퀘어 네오 (NanumSquareNeo)**
- **대체 폰트 스택**: `'NanumSquareNeo', 'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', sans-serif`
- **폰트 파일 위치**: `app/fonts/NanumSquareNeo-*.woff2`

### 2.2. 폰트 가중치 (Font Weight)
- **제목 (h1-h3)**: `font-bold` (700) 또는 `font-semibold` (600)
- **본문**: `font-normal` (400)
- **버튼/강조**: `font-medium` (500) 또는 `font-semibold` (600)

### 2.3. 폰트 크기 (Font Size)
- **h1**: `text-3xl` / **h2**: `text-2xl` / **h3**: `text-xl`
- **본문**: `text-base` (15px) / **작은 텍스트**: `text-sm` (13.125px)

---

## 3. 디자인 토큰 (Design Tokens)

### 3.1. 색상 팔레트
- **Primary Colors (검사 단계별 브랜딩)**
  - `--color-primary-blue: #3B82F6;` (성향 진단)
  - `--color-primary-indigo: #6366F1;` (사고력 진단)
  - `--color-primary-purple: #8B5CF6;` (선호도 진단)
  - `--color-primary-teal: #14B8A6;` (종합검사)
- **Secondary & Neutral Colors**: (생략... 기존 내용과 동일)
- **Background Gradients**:
  - `--bg-gradient-primary: linear-gradient(135deg, #EBF8FF 0%, #E0E7FF 50%, #F3E8FF 100%);`
  - `--bg-gradient-card: rgba(255, 255, 255, 0.9);`

### 3.2. 스페이싱 (8px Grid System)
- `--spacing-4: 1rem;` (16px) / `--spacing-6: 1.5rem;` (24px) / `--spacing-8: 2rem;` (32px)

---

## 4. 컴포넌트 디자인 시스템

### 4.1. 카드 컴포넌트 (Glassmorphism Card)
- **기본 클래스**: `glass-card`
- **스타일**: `bg-white/90 backdrop-blur-md rounded-3xl shadow-2xl border border-white/30`
- **인터랙션**: `hover:shadow-3xl transition-all duration-300`

### 4.2. 버튼 시스템
- **기본 클래스**: `btn`
- **Primary**: `btn--primary`, `bg-gradient-to-r from-blue-500 to-indigo-600 text-white`
- **Secondary**: `btn--secondary`, `bg-white/80 border border-gray-200/50`
- **Sizes**: `btn--size-sm`, `btn--size-md`, `btn--size-lg`

### 4.3. 검사 문항 컴포넌트
- **성향 진단 (6점 척도)**: 번호 박스는 그라데이션, 선택지는 그리드 레이아웃.
- **사고력 진단 (객관식)**: 질문과 이미지를 포함한 카드, 선택지는 세로 목록.
- **선호도 진단 (이미지 기반)**: 큰 이미지 뷰어와 하단 선택지 그리드.

---

## 5. 레이아웃 및 기타
- **기본 레이아웃**: `min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50`
- **다크 모드**: `@media (prefers-color-scheme: dark)` 또는 `.dark` 클래스 기반 스타일 적용. `glass-card`는 `bg-gray-900/90 border-gray-700/30`으로 변경.
- **애니메이션**: `fade-in-up`, `hover-lift` 등 미세한 전환 효과 사용.
- **접근성**: 모든 인터랙티브 요소에 `aria-*` 속성 및 `focus-visible` 스타일 적용.