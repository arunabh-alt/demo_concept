# Backend

## Purpose

This backend is a FastAPI API for local authentication.

Implemented features:

- health check endpoint
- signup endpoint
- signin endpoint
- current-user endpoint with JWT auth
- SQLAlchemy-backed user persistence with SQLite for local development
- optional PostgreSQL support through `DATABASE_URL`
- user-owned digital twin agent profiles
- deterministic direct-mode and orchestrator-mode execution pipeline
- conversation, memory, and action execution persistence
- simplified schema with only users, agents, conversations, memory, and action storage
- authenticated websocket voice pipeline for Amazon Transcribe streaming

## Tech Stack

- Python 3.11
- FastAPI
- SQLAlchemy 2
- SQLite for local development
- PostgreSQL for optional production-like local setup
- Psycopg 3 for PostgreSQL connections
- Pydantic Settings
- `python-jose` for JWT creation and validation
- `passlib` with `pbkdf2_sha256` for password hashing

## API Endpoints

- `GET /api/health`
- `POST /api/auth/signup`
- `POST /api/auth/signin`
- `GET /api/auth/me`
- `GET /api/agents/mine`
- `POST /api/agents/execute`
- `WS /api/voice/pipeline/ws?token=<jwt>`

## Agentic Architecture

The backend now models the digital twin pipeline described in the architecture:

- `User` owns one or more `AgentProfile` records
- each request carries `message`, `agent_id`, and `user_id`
- the API builds a prompt-like context string
- the execution service selects `direct` or `orchestrator` mode
- the response is stored in a `Conversation` and `ConversationMessage` history
- the `LearningEngine` writes reusable `MemoryPattern` records
- financial actions are written to `ActionExecution`

Core tables:

- `users`
- `agent_profiles`
- `conversations`
- `conversation_messages`
- `memory_patterns`
- `action_executions`

Detailed schema document:

- `DATABASE_SCHEMA.md`

Local demo behavior:

- signup creates a primary digital twin agent
- requests like `Transfer 500 Pounds to Alice` execute through direct mode and are recorded as structured action executions
- transfer details are stored in `action_executions.response_payload`

## Environment

Create `backend/.env` based on `backend/.env.example`.

Required settings:

- `APP_NAME`
- `APP_ENV`
- `API_PREFIX`
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `JWT_EXPIRE_MINUTES`
- `BACKEND_CORS_ORIGINS`
- `AWS_REGION`
- `AWS_TRANSCRIBE_LANGUAGE_CODE`
- `AWS_TRANSCRIBE_MEDIA_ENCODING`
- `AWS_TRANSCRIBE_SAMPLE_RATE_HZ`

Example `DATABASE_URL`:

```text
sqlite:///./local.db
```

Optional PostgreSQL example:

```text
postgresql+psycopg://postgres:your_password@localhost:5432/fullstack_auth
```

Example AWS voice configuration:

```text
AWS_REGION=us-east-1
AWS_TRANSCRIBE_LANGUAGE_CODE=en-US
AWS_TRANSCRIBE_MEDIA_ENCODING=pcm
AWS_TRANSCRIBE_SAMPLE_RATE_HZ=16000
```

## Database

Default local database:

- SQLite file at `backend/local.db`

No separate database server is required for local development. The file is created automatically on startup.

Optional PostgreSQL database:

```sql
CREATE DATABASE fullstack_auth;
```

Schema file:

- `sql/schema.sql` for PostgreSQL

The app also creates tables on startup through SQLAlchemy metadata.

## Install

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Default local server:

- `http://127.0.0.1:8000`
- root path redirects to `/docs`

## Voice Pipeline

The voice path is split into two stages:

- browser microphone audio streams to `WS /api/voice/pipeline/ws?token=<jwt>`
- the frontend submits the final transcript to `POST /api/agents/execute`

Websocket control flow:

- connect with a valid JWT in the query string
- send `{"type":"start","sample_rate":16000,"language_code":"en-US"}`
- stream PCM16 mono audio bytes
- send `{"type":"stop"}`
- receive `transcript` events and a final `transcript_complete`

## Validation

Quick import check:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -c "from app.main import app; print(app.title)"
```