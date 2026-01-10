# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Full-stack Claude AI chat interface with sandbox code execution. Frontend (React/TypeScript/Vite) on port 3000, Backend (FastAPI/Python) on port 8080, PostgreSQL 13, Redis 7.

## Commands

### Frontend (from `/frontend`)

```bash
npm run dev           # Dev server on :3000
npm run build         # Production build
npm run lint          # ESLint
npm run lint:fix      # ESLint autofix
npm run format        # Prettier format
npm run typecheck     # TypeScript check
```

### Backend (from `/backend`)

```bash
# Development
uvicorn app.main:app --reload

# Linting & Formatting
ruff check .          # Lint
ruff format .         # Format
mypy app/             # Type check

# Database
python migrate.py                              # Run migrations
alembic revision --autogenerate -m "message"   # Create migration

# Testing (requires Docker)
docker compose -f docker-compose.test.yml run --rm backend-test pytest
docker compose -f docker-compose.test.yml run --rm backend-test pytest tests/path/test_file.py::test_name  # Single test
```

### Docker Compose

```bash
docker compose up -d              # Start all services
docker compose down               # Stop all services
docker compose logs -f backend    # View logs
```

## Architecture

### Backend (`/backend/app`)

- **Entry:** `main.py` - FastAPI app factory with `create_application()`
- **API Layer:** `api/endpoints/` - Route handlers (chat, auth, sandbox, websocket, agents, skills, commands)
- **Service Layer:** `services/` - Business logic (`ChatService`, `ClaudeAgentService`, `SandboxService`, `PermissionManager`)
- **Models:** `models/db_models/` - SQLAlchemy ORM, `models/schemas/` - Pydantic schemas
- **Background Tasks:** `tasks/` - Celery tasks for async chat processing and scheduling
- **Dependencies:** `core/deps.py` - FastAPI dependency injection for sessions, auth, services

### Frontend (`/frontend/src`)

- **Entry:** `main.tsx` → `App.tsx` with React Router
- **Pages:** `pages/` - Route containers (ChatPage, SettingsPage, etc.)
- **Components:** `components/` - Feature folders (chat/, editor/, settings/, ui/)
- **State:** `store/` - Zustand stores (authStore, chatStore, streamStore, modelStore, permissionStore)
- **API:** `services/` - API client functions, `hooks/queries/` - React Query hooks
- **Custom Hooks:** `hooks/` - 30+ hooks for chat streaming, file handling, message actions

### Key Patterns

- Backend uses async SQLAlchemy with separate session factories for API (`SessionLocal`) and Celery (`CelerySessionLocal`)
- Real-time chat via SSE streaming with Redis pub/sub for cross-worker communication
- Docker containers provide isolated sandbox environments for code execution
- Frontend uses Zustand for client state, React Query for server state
- All API responses use Pydantic schemas for validation

### Frontend Type Placement

- **Shared types** (used across multiple files) → `types/*.types.ts` with barrel export via `types/index.ts`
- **Local types** (used only in one file) → define in that file, do not export
- Hook option/result interfaces (`UseXxxOptions`, `UseXxxResult`) → local to the hook file
- Component prop interfaces → local to the component file
- Service request/response types used only by that service → local to the service file

### Database

Models in `/backend/app/models/db_models/`: User, Chat, Message, MessageAttachment, AIModel, UserSettings, RefreshToken, ScheduledTask

Migrations in `/backend/migrations/` managed by Alembic.

## Environment

Key env vars in `.env`: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `ANTHROPIC_API_KEY`, `ENVIRONMENT` (development/production)
