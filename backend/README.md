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

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- `GET /`       → service metadata
- `GET /health` → liveness check
- `GET /docs`   → OpenAPI UI

The API does **not** touch the database yet (Phase 1 is schema only).

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
- `tests/test_database.py`, `test_seed.py`, `test_zz_migration.py` — require a
  **real PostgreSQL** throwaway database. Point them at one with:

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
│   ├── main.py                FastAPI app + root route
│   ├── core/config.py         pydantic-settings configuration
│   ├── api/routes/health.py
│   └── db/
│       ├── base.py            DeclarativeBase + constraint naming convention
│       ├── models.py          the 9 Phase 1 tables (schema only)
│       ├── session.py         engine / session factory helpers
│       └── seed.py            deterministic, idempotent dev seed data
├── alembic/
│   ├── env.py                 target_metadata = models; URL from settings/-x
│   └── versions/0001_initial_schema.py
├── alembic.ini
├── tests/
│   ├── conftest.py            PostgreSQL fixtures (skip-with-reason if absent)
│   ├── test_health.py
│   ├── test_database.py       15 mandated schema checks + extras
│   ├── test_seed.py
│   └── test_zz_migration.py   downgrade base → upgrade head round-trip
├── requirements.txt / requirements-dev.txt
└── pyproject.toml             pytest config
```

See `../docs/database-design.md` and `../docs/decisions.md`.
