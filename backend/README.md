# PromptDNA — Backend

FastAPI + Python. Layered API (router → schema → service → repository →
SQLAlchemy → PostgreSQL) with JWT authentication (Phase 3), plus the Phase 1
data layer (models, Alembic migration, seed script).

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
(copy `../.env.example`). Two settings are needed to run the API:

```
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME   # Phase 1 schema
JWT_SECRET_KEY=<strong random value>                               # REQUIRED — no fallback
# optional: JWT_ALGORITHM=HS256, ACCESS_TOKEN_EXPIRE_MINUTES=30, CORS_ORIGINS=...
```

The API **refuses to start** if `JWT_SECRET_KEY` is unset.

## Run the API

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- `GET /`            → service metadata
- `GET /health`      → liveness (no DB) · `GET /health/db` → readiness (`SELECT 1`)
- `GET /docs`        → OpenAPI UI (has an **Authorize** button)
- `POST /api/v1/auth/register` · `POST /api/v1/auth/login` · `GET /api/v1/auth/me`
- `POST/GET /api/v1/prompts` · `GET|PATCH /api/v1/prompts/{id}`
- `GET|POST /api/v1/prompts/{id}/versions` · `GET /api/v1/prompts/{id}/versions/{vid}`
- all `/prompts*` routes require `Authorization: Bearer <token>`

Full reference: `../docs/api.md`. Ownership comes from the authenticated user
(the Phase 2 `X-Dev-User-ID` header was removed in Phase 3). Prompt text lives
in **versions**; existing versions are immutable — editing content means
`POST …/versions` (owner only).

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

A test `JWT_SECRET_KEY` is set automatically by `tests/conftest.py`.

- `tests/test_health.py` — runs anywhere, no database.
- `tests/test_database.py`, `test_seed.py`, `test_zz_migration.py`,
  `test_api_prompts.py`, `test_auth.py`, `test_authz.py` — require a **real
  PostgreSQL** throwaway database. Point them at one with:

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
│   ├── main.py                FastAPI app: lifespan (JWT-secret check), CORS, handlers, routers
│   ├── core/
│   │   ├── config.py          pydantic-settings (+ CORS, DB pool, JWT settings)
│   │   └── security.py        Argon2 hash/verify + JWT create/decode
│   ├── api/
│   │   ├── router.py          aggregates /api/v1 (auth + prompts)
│   │   ├── deps.py            get_current_user (Bearer JWT -> User); CurrentUser
│   │   ├── errors.py          AppError types (+ 401/403) + exception handlers
│   │   └── routes/
│   │       ├── health.py      GET /health, GET /health/db
│   │       ├── auth.py        POST /auth/register, POST /auth/login, GET /auth/me
│   │       └── prompts.py     POST/GET /api/v1/prompts, /{id}, /{id}/versions
│   ├── schemas/
│   │   ├── auth.py            RegisterRequest / UserRead / TokenResponse
│   │   └── prompt.py          PromptCreate / PromptRead / *ListResponse / VersionRead
│   ├── services/
│   │   ├── auth.py            register + login (authentication)
│   │   └── prompt.py          create/append/patch transactions + authorization (visibility, owner-only, lineage)
│   ├── repositories/
│   │   ├── user.py            get_by_id / get_by_email / add_user
│   │   └── prompt.py          prompt/version access; visibility predicate; get_max_version_number; get_version_by_id; update_prompt
│   └── db/
│       ├── base.py            DeclarativeBase + constraint naming convention
│       ├── models.py          the 9 Phase 1 tables (schema only — UNCHANGED)
│       ├── session.py         lazy engine + get_db dependency + build_engine
│       └── seed.py            deterministic, idempotent dev seed data
├── alembic/
│   ├── env.py                 target_metadata = models; URL from settings/-x
│   └── versions/0001_initial_schema.py    (UNCHANGED — no Phase 2/3 migration)
├── alembic.ini
├── tests/
│   ├── conftest.py            PostgreSQL fixtures + API client + auth helpers (savepoint-isolated)
│   ├── test_health.py         no DB
│   ├── test_database.py       Phase 1: 15 mandated schema checks + extras
│   ├── test_seed.py           Phase 1
│   ├── test_zz_migration.py   Phase 1: downgrade base → upgrade head round-trip
│   ├── test_api_prompts.py    prompt list/get/validation + PATCH metadata (bearer-authed)
│   ├── test_auth.py           Phase 3: authentication (13 cases + hash check)
│   ├── test_authz.py          Phase 3: authorization + security attack scenario
│   ├── test_versions.py       Phase 4A: version append / numbering / immutability / retrieval / 409
│   └── test_lineage.py        Phase 4A: parent_prompt_id fork rules
├── requirements.txt / requirements-dev.txt
└── pyproject.toml             pytest config
```

See `../docs/api.md`, `../docs/database-design.md`, and `../docs/decisions.md`.
