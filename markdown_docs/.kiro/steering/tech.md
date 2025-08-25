# Technology Stack

## Backend (Python)

- **Framework**: FastAPI with async/await patterns
- **Database**: PostgreSQL with pgvector extension for vector storage
- **ORM**: SQLAlchemy 2.0+ with async support
- **Authentication**: JWT tokens with PyJWT and passlib[bcrypt]
- **AI/ML**: Google Gemini API for text generation
- **Vector Search**: pgvector for semantic search capabilities
- **Background Jobs**: Asyncio-based task processing (no external queue)
- **Logging**: structlog for structured logging
- **Testing**: pytest with pytest-asyncio

## Frontend (TypeScript/React)

- **Framework**: Next.js 14+ with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS with custom components
- **State Management**: React Query (@tanstack/react-query) + React Context
- **Real-time**: WebSocket connections + Server-Sent Events
- **Testing**: Vitest with @testing-library/react
- **Forms**: Custom form handling with validation

## Development Commands

### Backend
```bash
# Start development server
python main.py

# Run database migrations
python run_migration.py

# Run tests
pytest

# Check ETL status
python monitor_etl.py
```

### Frontend
```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Run tests
npm run test

# Type checking
npm run type-check

# Linting
npm run lint
```

## Environment Setup

- Backend requires `.env` file with database credentials and API keys
- Frontend requires `.env.local` with API endpoints
- PostgreSQL with pgvector extension must be installed
- Node.js 18.0.0+ required for frontend development