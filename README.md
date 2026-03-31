# Full Stack Auth App

This workspace is organized into two app folders only:

- `backend` for the FastAPI API and PostgreSQL-backed auth
- `frontend` for the React TypeScript client with React Compiler enabled

## Tech Stack

### Frontend

- React 19
- TypeScript 5
- Vite 6
- React Compiler via `babel-plugin-react-compiler`
- CSS for styling

### Backend

- Python 3.11
- FastAPI
- SQLAlchemy 2
- SQLite for local development
- PostgreSQL as an optional database target
- Psycopg 3 for PostgreSQL connectivity
- Pydantic Settings
- JWT auth with `python-jose`
- Password hashing with `passlib` using `pbkdf2_sha256`

### Database

- Local SQLite database by default
- Optional local PostgreSQL database
- `users` table with UUID primary key, unique email, hashed password, and created timestamp

## Backend

The backend provides:

- `POST /api/auth/signup`
- `POST /api/auth/signin`
- `GET /api/auth/me`
- `GET /api/health`
- `GET /api/agents/mine`
- `POST /api/agents/execute`
- `WS /api/voice/pipeline/ws?token=<jwt>`

Create `backend/.env` from `backend/.env.example`, keep the default SQLite `DATABASE_URL` for local development, and run:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The app will create `backend/local.db` automatically.

The local backend now includes a digital twin data model for users, agent identities, persisted conversations, learning patterns, and action execution records.

The voice pipeline uses Amazon Transcribe through the FastAPI backend. The browser streams microphone audio over the authenticated websocket, then the frontend forwards the final transcript into the existing digital-twin execution route.

PostgreSQL remains optional. The table definition is included in `backend/sql/schema.sql`.

Example local Postgres setup:

```sql
CREATE DATABASE fullstack_auth;
```

## Frontend

The frontend is a Vite React TypeScript app configured with React Compiler through the Vite React plugin.

Run:

```powershell
Set-Location frontend
npm install
npm run dev
```

The frontend expects the backend at `http://127.0.0.1:8000/api` by default. Override with `VITE_API_BASE_URL` if needed.

The main UI is now a voice-command workspace with:

- auth and primary-agent state
- live microphone controls
- transcript streaming view
- typed-command fallback
- structured response and event-log panels