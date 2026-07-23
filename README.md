# Abhinav Group — AI Gmail Intelligence & Legal Assistant

> **Enterprise AI-powered Corporate Memory System** for Abhinav Group

---

## Overview

The Abhinav Group AI Intelligence Assistant transforms labeled Gmail emails into a searchable, AI-powered knowledge base. Directors can ask questions in natural language and receive evidence-backed answers drawn exclusively from approved emails and attachments.

**Core Technology**: Retrieval-Augmented Generation (RAG) — the AI never fabricates answers. Every response is traceable to a real email.

---

## Architecture

```
Frontend (React + TypeScript + Tailwind)
    ↓ HTTPS + JWT
Backend (FastAPI + Python)
    ↓
PostgreSQL + pgvector  |  Redis  |  Celery Workers
    ↓
Gmail API  |  Groq AI  |  PaddleOCR
```

---

## Prerequisites

Before starting, ensure you have installed:

| Software | Version | Download |
|----------|---------|---------|
| Docker Desktop | Latest | https://www.docker.com/products/docker-desktop |
| Git | 2.40+ | https://git-scm.com |
| Node.js (for local dev) | 20+ | https://nodejs.org |
| Python (for local dev) | 3.11+ | https://python.org |

---

## Quick Start (Docker)

### Step 1: Copy environment file
```bash
cp .env.example .env
```

### Step 2: Edit `.env` with your values
At minimum, set:
- `SECRET_KEY` — generate with `python -c "import secrets; print(secrets.token_hex(64))"`
- `POSTGRES_PASSWORD` — strong password
- `REDIS_PASSWORD` — strong password
- `FIRST_DIRECTOR_EMAIL` — your email (bootstraps first account)
- `FIRST_DIRECTOR_NAME` — your name
- `FIRST_DIRECTOR_PASSWORD` — secure password

### Step 3: Start all services
```bash
docker-compose up -d
```

### Step 4: Run database migrations
```bash
docker-compose exec backend alembic upgrade head
```

### Step 5: Access the application
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Celery Monitor**: http://localhost:5555

---

## Local Development (Without Docker)

### Backend
```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# or: source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Copy and configure env
cp .env.example .env
# Edit .env with your values

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

---

## External Services Setup

### Google Cloud Project (Gmail API)
> **⚠️ Required for Gmail sync — do this after initial setup is verified**

1. Go to https://console.cloud.google.com
2. Create a new project named "Abhinav AI Assistant"
3. Enable Gmail API: APIs & Services → Enable APIs → search "Gmail API"
4. Create OAuth credentials: APIs & Services → Credentials → Create OAuth 2.0 Client ID
   - Application type: Web application
   - Authorized redirect URIs: `http://localhost:8000/api/v1/oauth/callback`
5. Copy Client ID and Client Secret to `.env`

### Groq API (AI Engine)
> **⚠️ Required for AI chat — do this after Gmail sync is working**

1. Go to https://console.groq.com
2. Sign up for a free account
3. Create an API key
4. Copy to `.env` as `GROQ_API_KEY`

---

## Project Structure

```
Gmail Assistant/
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── api/v1/            # API endpoints
│   │   ├── core/              # Config, security, database
│   │   ├── models/            # SQLAlchemy database models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── services/          # Business logic
│   │   ├── middleware/        # Audit logging, rate limiting
│   │   └── workers/           # Celery background tasks
│   ├── tests/                 # Pytest test suite
│   ├── alembic/               # Database migrations
│   └── requirements.txt
├── frontend/                  # React TypeScript frontend
│   └── src/
│       ├── pages/             # Page components
│       ├── components/        # Reusable UI components
│       ├── store/             # Zustand state management
│       └── api/               # API client functions
├── docker/
│   └── postgres/init.sql      # Database initialization
├── docker-compose.yml         # Development environment
├── .env.example               # Environment variables template
└── README.md
```

---

## Development Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | 🔄 In Progress | Foundation, Authentication, Project Scaffold |
| 2 | ⬜ Pending | Gmail Sync Engine |
| 3 | ⬜ Pending | OCR + Document Processing |
| 4 | ⬜ Pending | Entity Extraction |
| 5 | ⬜ Pending | Embeddings + Vector Search |
| 6 | ⬜ Pending | AI Chat + RAG Engine |
| 7 | ⬜ Pending | Automatic Reports |
| 8 | ⬜ Pending | Full Dashboard |
| 9 | ⬜ Pending | Security Hardening |
| 10 | ⬜ Pending | Testing + Production Deployment |

---

## Security

- JWT authentication (15-minute access tokens, 7-day refresh tokens)
- Google OAuth with minimal scope (Gmail read-only, label-filtered)
- Role-based access control
- Rate limiting on all endpoints
- Complete audit trail (every action logged)
- Encryption at rest and in transit
- Files stored outside web root with signed temporary URLs

---

## API Documentation

When the backend is running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Testing

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

---

## License

Proprietary — Abhinav Group. All rights reserved.
