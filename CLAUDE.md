# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Romanian Freight Forwarder Automation System

This is an AI-powered logistics automation platform designed for Romanian freight forwarders. The system provides end-to-end automation from email order intake to payment reconciliation, with intelligent document processing using GPT-4 Vision and Claude 3.5 Sonnet.

## Development Commands

### Quick Start
```bash
make setup     # Initial project setup (creates .env, installs deps, starts Docker services)
make dev       # Start all development servers
make stop      # Stop all services
```

### Testing
```bash
make test           # Run all tests (backend + frontend)
make test-backend   # Backend tests only (pytest with coverage)
make test-frontend  # Frontend tests only (vitest)
make test-e2e       # End-to-end tests (Playwright)
```

### Code Quality
```bash
make lint     # Run linting (black, isort, flake8, mypy for backend; eslint for frontend)
make format   # Format code (black/isort for backend; prettier for frontend)
```

### Frontend Development
```bash
cd frontend
npm run dev         # Development server
npm run build       # Production build
npm run type-check  # TypeScript type checking
npm run test        # Run tests
npm run test:ui     # Test UI
```

### Backend Development
```bash
cd backend
# Activate virtual environment first: . venv/bin/activate
uvicorn app.main:app --reload  # Development server
pytest tests/ -v --cov=app     # Run tests
black app/ && isort app/       # Format code
mypy app/                      # Type checking
```

### Database Operations
```bash
make migration  # Create new Alembic migration
make migrate    # Run database migrations
make shell-db   # Open PostgreSQL shell
make backup-db  # Backup database
```

## Architecture Overview

### Full-Stack Structure
- **Backend**: FastAPI with Python 3.11+, PostgreSQL with PostGIS, Redis, Celery
- **Frontend**: React 18 with TypeScript, Vite, TanStack Query, Zustand
- **AI Integration**: OpenAI GPT-4 Vision + Anthropic Claude 3.5 Sonnet
- **Storage**: MinIO (S3-compatible) for file storage
- **Background Tasks**: Celery with Redis broker

### Key Backend Components

#### Core Architecture
- `app/main.py` - FastAPI application with lifespan management, middleware setup
- `app/core/` - Configuration, database, security, dependencies
- `app/api/v1/` - API routes organized by domain (orders, auth, monitoring)
- `app/services/` - Business logic layer with AI integration
- `app/models/` - SQLAlchemy ORM models with PostGIS support
- `app/schemas/` - Pydantic models for request/response validation
- `app/tasks/` - Celery background tasks for email processing and AI operations

#### AI Integration Pattern
The system uses a dual-AI approach:
- **Document Processing**: GPT-4 Vision extracts data from transport documents
- **Business Logic**: Claude 3.5 Sonnet handles Romanian business rules and EFACTURA compliance
- **Services**: `ai_service.py`, `ai_provider_manager.py`, `confidence_scorer.py`

#### Order Processing Flow
1. Email monitoring via `email_service.py` and `email_tasks.py`
2. Document parsing using `pdf_processor.py` + AI services
3. Order creation through `order_service_enhanced.py` with Romanian business logic
4. Real-time updates via WebSocket (`websocket_manager.py`)

### Key Frontend Components

#### Architecture Pattern
- **Feature-based organization**: `/features/auth`, `/features/orders`, `/features/subcontractors`
- **Shared components**: `/shared/components`, `/shared/services`, `/shared/hooks`
- **State management**: Zustand stores in `/shared/stores`
- **Real-time**: WebSocket integration for live updates

#### Core Features
- **Orders Management**: Complete order lifecycle with workflow progress tracking
- **Real-time Updates**: WebSocket connections for live order status updates
- **Document Processing**: Upload and AI-powered document parsing
- **Romanian Localization**: Business-specific Romanian freight forwarding terms

#### UI Framework
- **Component Library**: Radix UI primitives with custom styling
- **Styling**: Tailwind CSS with custom design system
- **Forms**: React Hook Form with Zod validation
- **Data Fetching**: TanStack Query for server state management

## Development Environment

### Docker Services
- **Backend**: FastAPI app on port 8000
- **Frontend**: React dev server on port 3000  
- **PostgreSQL**: Database with PostGIS extension on port 5432
- **Redis**: Cache and Celery broker on port 6379
- **MinIO**: S3-compatible storage on ports 9000/9001
- **Celery Worker**: Background task processing
- **Celery Beat**: Scheduled task management

### Service URLs (Development)
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- MinIO Console: http://localhost:9001 (minioadmin/minioadmin123)

### Environment Configuration
Requires `.env` file with:
- `OPENAI_API_KEY` - GPT-4 Vision access
- `ANTHROPIC_API_KEY` - Claude 3.5 Sonnet access
- `SECRET_KEY` - JWT signing key
- `VITE_MAPBOX_TOKEN` - Frontend mapping features

## Romanian Business Context

This system implements specific Romanian freight forwarding business logic:
- **EFACTURA compliance** for electronic invoicing
- **RON currency handling** and profit margin calculations
- **Romanian transport document formats** (CMR, freight bills)
- **Local subcontractor management** patterns
- **Romanian VAT and tax calculations**

The AI services are specifically trained to understand Romanian transport documents and business practices.

## Code Patterns and Conventions

### Backend Patterns
- **Async/await**: All database and external API calls use async patterns
- **Dependency injection**: FastAPI dependency system for database sessions, auth
- **Error handling**: Custom exception hierarchy with proper HTTP status codes
- **Logging**: Loguru for structured logging with rotation
- **Type safety**: Full mypy type checking enabled

### Frontend Patterns  
- **Component composition**: Radix UI primitives with custom wrappers
- **Custom hooks**: Feature-specific hooks for business logic
- **Error boundaries**: Proper error handling for AI processing failures
- **TypeScript strict mode**: Full type safety with strict configuration
- **Real-time patterns**: WebSocket hooks for live data updates

### AI Integration Best Practices
- **Confidence scoring**: All AI responses include confidence metrics
- **Fallback handling**: Graceful degradation when AI services are unavailable
- **Cost optimization**: Smart caching and request batching
- **Romanian context**: AI prompts include Romanian business context and terminology

## Testing Strategy

### Backend Testing
- **Unit tests**: pytest with SQLAlchemy test fixtures
- **Integration tests**: FastAPI TestClient for API endpoints
- **AI service mocking**: Mock AI responses for consistent testing
- **Database tests**: Isolated test database with cleanup

### Frontend Testing
- **Component tests**: React Testing Library + Vitest
- **Hook tests**: Custom hook testing patterns
- **E2E tests**: Playwright for full user workflows
- **Visual regression**: Screenshot testing for UI consistency

### AI Testing Approach
- **Mock AI responses** during development and testing
- **Confidence threshold testing** for document processing accuracy
- **Romanian document samples** for validation testing