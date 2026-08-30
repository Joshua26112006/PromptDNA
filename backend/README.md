# PromptDNA — Backend

FastAPI + Python. Phase 0: application shell, configuration, and a `/health`
endpoint. No authentication, no CRUD, no business logic.

## Requirements

- Python 3.11+ (developed on 3.13)

## Setup (Windows / PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

macOS / Linux:

```bash
cd backend
python -m venv .venv
./.venv/bin/pip install -r requirements-dev.txt
```

Configuration is read from environment variables and an optional repo-root
`.env` (copy `../.env.example`). Nothing is required to start in Phase 0.

## Run

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- `GET /`        → service metadata
- `GET /health`  → liveness check (`{"status":"ok", "message":"PromptDNA backend is running", ...}`)
- `GET /docs`    → OpenAPI UI

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Layout

```
backend/
├── app/
│   ├── main.py            FastAPI app + root route
│   ├── core/config.py     pydantic-settings configuration
│   └── api/routes/health.py
├── alembic/               migration environment (NO migrations yet)
├── alembic.ini            sqlalchemy.url intentionally blank (filled from settings)
├── tests/test_health.py
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml         pytest config
```

## Migrations

Alembic is wired to the app's `DATABASE_URL` setting but has **no models and no
revisions** in Phase 0. See `../docs/database-design.md`.
