# PromptDNA — Backend

FastAPI + Python. Also home to the **Phase 1 PostgreSQL data layer**: SQLAlchemy
models, the Alembic migration, and the seed script. No authentication, no CRUD,
no business logic.

## Requirements

- Python 3.11+ (developed on 3.13)
- PostgreSQL 13+ for anything database-related (13+ ships `gen_random_uuid()`).

## Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt   # Windows
# ./.venv/bin/pip install -r requirements-dev.txt                   # macOS/Linux
```

Configuration comes from environment variables / a repo-root `.env`
(copy `../.env.example`). `DATABASE_URL` is the only one the data layer needs:

```
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME
```

## Run the API

`DATABASE_URL` must point at a database holding the Phase 1 schema.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- `GET /`            → service metadata
- `GET /health`      → liveness (no DB)
- `GET /health/db`   → readiness (`SELECT 1`; 503 if PostgreSQL unreachable)
- `GET /docs`        → OpenAPI UI
- `POST /api/v1/prompts` · `GET /api/v1/prompts` · `GET /api/v1/prompts/{id}` ·
  `GET /api/v1/prompts/{id}/versions`

Full reference: `../docs/api.md`. Creating a prompt needs a development-only
header `X-Dev-User-ID: <existing users.user_id>` (not authentication).

## Database: migrate + seed

```powershell
# 1. create the schema from empty (reproducible via Alembic)
.\.venv\Scripts\alembic.exe upgrade head

# 2. load deterministic dev data (safe to rerun)
.\.venv\Scripts\python.exe -m app.db.seed

# other useful commands
.\.venv\Scripts\alembic.exe downgrade base     # drop the schema
.\.venv\Scripts\alembic.exe check              # models vs. migration drift check
```

Alembic resolves the URL from `-x db_url=...`, then `alembic.ini`
(`sqlalchemy.url`, blank by default), then `DATABASE_URL`.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest
```

- `tests/test_health.py` — runs anywhere, no database.
- `tests/test_database.py`, `test_seed.py`, `test_zz_migration.py`,
  `test_api_prompts.py` — require a **real PostgreSQL** throwaway database.
  Point them at one with:

  ```
  PROMPTDNA_TEST_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/promptdna_test
  ```

  The suite `DROP SCHEMA public CASCADE`s and re-runs the migration, so the URL
  must name a disposable database (the fixture refuses names without "test"
  unless `PROMPTDNA_TEST_ALLOW_ANY_DB=1`). With no such URL these tests **skip
  with a message** — they never silently fall back to SQLite.

## Layout

```
backend/
├── app/
│   ├── main.py                FastAPI app: CORS, exception handlers, routers
│   ├── core/config.py         pydantic-settings configuration (+ CORS, pool)
│   ├── api/
│   │   ├── router.py          aggregates the versioned API under /api/v1
│   │   ├── deps.py            get_dev_user_id  (X-Dev-User-ID, dev-only)
│   │   ├── errors.py          AppError types + exception handlers
│   │   └── routes/
│   │       ├── health.py      GET /health, GET /health/db
│   │       └── prompts.py     POST/GET /api/v1/prompts, /{id}, /{id}/versions
│   ├── schemas/prompt.py      PromptCreate / PromptRead / *ListResponse / VersionRead
│   ├── services/prompt.py     business rules + the create transaction
│   ├── repositories/prompt.py all SQLAlchemy access (never commits)
│   └── db/
│       ├── base.py            DeclarativeBase + constraint naming convention
│       ├── models.py          the 9 Phase 1 tables (schema only)
│       ├── session.py         lazy engine + get_db dependency + build_engine
│       └── seed.py            deterministic, idempotent dev seed data
├── alembic/
│   ├── env.py                 target_metadata = models; URL from settings/-x
│   └── versions/0001_initial_schema.py    (unchanged in Phase 2)
├── alembic.ini
├── tests/
│   ├── conftest.py            PostgreSQL fixtures + API test client (savepoint-isolated)
│   ├── test_health.py         no DB
│   ├── test_database.py       Phase 1: 15 mandated schema checks + extras
│   ├── test_seed.py           Phase 1
│   ├── test_zz_migration.py   Phase 1: downgrade base → upgrade head round-trip
│   └── test_api_prompts.py    Phase 2: API integration tests (real PostgreSQL)
├── requirements.txt / requirements-dev.txt
└── pyproject.toml             pytest config
```

See `../docs/api.md`, `../docs/database-design.md`, and `../docs/decisions.md`.
