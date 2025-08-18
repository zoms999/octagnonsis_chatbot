# Project Structure

## Root Directory Layout

```
├── api/                    # FastAPI route handlers
├── database/              # Database models, repositories, and connections
├── etl/                   # ETL pipeline components
├── rag/                   # RAG system components
├── monitoring/            # System monitoring and metrics
├── tests/                 # Backend test suite
├── front/                 # Next.js frontend application
├── logs/                  # Application logs
└── .kiro/                 # Kiro IDE configuration
```

## Backend Architecture

### API Layer (`api/`)
- `auth_endpoints.py` - Authentication and user management
- `chat_endpoints.py` - Chat interactions and WebSocket handlers
- `etl_endpoints.py` - ETL job management and monitoring
- `user_endpoints.py` - User profile and document management

### Database Layer (`database/`)
- `models.py` - SQLAlchemy ORM models
- `repositories.py` - Data access layer with business logic
- `connection.py` - Database connection and session management
- `schemas.py` - Pydantic schemas for validation
- `vector_search.py` - Vector similarity search functionality
- `cache.py` - Database-level caching mechanisms

### ETL Pipeline (`etl/`)
- `etl_orchestrator.py` - Main ETL workflow coordination
- `document_transformer.py` - Document processing and chunking
- `vector_embedder.py` - Text embedding generation
- `legacy_query_executor.py` - Legacy system data extraction
- `error_handling.py` - ETL error classification and recovery

### RAG System (`rag/`)
- `question_processor.py` - User question analysis and processing
- `context_builder.py` - Relevant context retrieval and assembly
- `response_generator.py` - AI response generation with context

## Frontend Architecture (`front/src/`)

### App Router Structure (`app/`)
```
├── (auth)/                # Authentication pages (login, register)
├── (protected)/           # Protected pages requiring authentication
│   ├── chat/             # Main chat interface
│   ├── history/          # Conversation history
│   ├── profile/          # User profile management
│   ├── documents/        # Document management
│   └── etl/              # ETL monitoring dashboard
├── layout.tsx            # Root layout with providers
└── globals.css           # Global styles
```

### Component Organization (`components/`)
```
├── ui/                   # Reusable UI primitives (Button, Input, Modal)
├── auth/                 # Authentication components
├── chat/                 # Chat interface components
├── layout/               # Layout and navigation components
└── history/              # Conversation history components
```

### Utilities and Hooks (`lib/`, `hooks/`)
- `lib/api.ts` - API client with error handling
- `lib/auth.ts` - Authentication utilities and token management
- `lib/websocket.ts` - WebSocket connection management
- `hooks/websocket-hooks.ts` - WebSocket React hooks
- `hooks/api-hooks.ts` - React Query API hooks

## Key Patterns

### Backend Patterns
- **Repository Pattern**: Data access abstracted through repository classes
- **Async/Await**: All database and external API calls use async patterns
- **Dependency Injection**: FastAPI dependency system for database sessions
- **Error Classification**: Structured error handling with retry logic
- **Job Tracking**: Database-based background job status tracking

### Frontend Patterns
- **Route Groups**: Next.js route groups for auth and protected pages
- **Custom Hooks**: Reusable hooks for WebSocket, API calls, and UI state
- **Provider Pattern**: React Context for global state (auth, theme)
- **Component Composition**: Small, focused components with clear interfaces
- **Type Safety**: Full TypeScript coverage with strict type checking

### File Naming Conventions
- Backend: `snake_case.py`
- Frontend: `kebab-case.tsx` for components, `camelCase.ts` for utilities
- Tests: `test_*.py` (backend), `*.test.tsx` (frontend)
- Types: Shared in `types.ts` files with clear interfaces