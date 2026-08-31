# PromptDNA — Backend

FastAPI + Python. Layered API (router → schema → service → repository →
SQLAlchemy → PostgreSQL) with JWT authentication (Phase 3), plus the Phase 1
data layer (models, Alembic migration, seed script). Phase 7 adds a **derived,
read-only Neo4j projection** of prompt-to-prompt relationships — PostgreSQL
stays the system of record; the graph is rebuildable and never authoritative.

## Requirements

- Python 3.11+ (developed on 3.13)
- PostgreSQL 13+ for anything database-related (13+ ships `gen_random_uuid()`).
- Optional: pgvector (Phase 6 semantic search) and Neo4j 5.x Community (Phase 7
  graph projection) — both are feature-gated and off by default. See
  `../database/docker-compose.yml` for local containers.

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

Phase 7 graph projection is opt-in and off by default:

```
NEO4J_ENABLED=false                       # true to enable the /api/v1/graph/* endpoints + post-commit projection
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j                       # NEO4J_USER is also accepted
NEO4J_PASSWORD=<password>                  # database/docker-compose.yml uses neo4j / promptdna_dev
NEO4J_DATABASE=neo4j
```

With `NEO4J_ENABLED=false` the graph endpoints return `503` and prompt writes
are unaffected. A Neo4j outage never rolls back a PostgreSQL write.

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
- `GET /api/v1/graph/prompts/{id}/{ancestors|descendants|dependencies|related}` (Phase 7 — needs `NEO4J_ENABLED=true`, else `503`)
- all `/prompts*` and `/graph*` routes require `Authorization: Bearer <token>`

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

**Phase 7 adds no migration** — `alembic check` still reports no drift. The
Neo4j graph is populated separately (and idempotently) from PostgreSQL:

```powershell
.\.venv\Scripts\python.exe -m scripts.sync_neo4j            # MERGE a node per prompt + DERIVED_FROM edges
.\.venv\Scripts\python.exe -m scripts.sync_neo4j --prune    # also delete nodes whose prompt is gone from PostgreSQL
.\.venv\Scripts\python.exe -m scripts.sync_neo4j --dry-run  # report counts, write nothing
```

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
│   │       ├── prompts.py     POST/GET /api/v1/prompts, /{id}, /{id}/versions
│   │       └── graph.py       GET /api/v1/graph/prompts/{id}/{ancestors|descendants|dependencies|related} (Phase 7 — no Cypher here)
│   ├── graph/                Phase 7 — Neo4j projection (all Cypher lives here)
│   │   ├── client.py          lazy Bolt driver singleton; GraphUnavailable; verify_connectivity; config from env
│   │   └── service.py         MERGE node/relationship upserts + depth-bounded traversal (DERIVED_FROM/FORKED_FROM/DEPENDS_ON only)
│   ├── schemas/
│   │   ├── auth.py            RegisterRequest / UserRead / TokenResponse
│   │   ├── prompt.py          PromptCreate / PromptRead / *ListResponse / VersionRead
│   │   └── graph.py           GraphResponse / GraphRelationship (PostgreSQL prompt_id only — no Neo4j ids)
│   ├── providers/            LLMProvider abstraction (Phase 5)
│   │   ├── base.py            LLMProvider + typed ProviderError subclasses
│   │   ├── mock.py            MockProvider (provider "mock" — dev/tests, deterministic)
│   │   ├── openai.py          OpenAIProvider (real, httpx; needs OPENAI_API_KEY)
│   │   └── registry.py        models.provider string -> provider instance
│   ├── embeddings/           EmbeddingProvider abstraction (Phase 6)
│   │   ├── base.py            EmbeddingProvider + typed EmbeddingError subclasses
│   │   ├── mock.py            MockEmbeddingProvider (deterministic, dim 1536)
│   │   ├── openai.py          OpenAIEmbeddingProvider (text-embedding-3-small)
│   │   └── registry.py        one active provider from EMBEDDING_PROVIDER
│   ├── services/
│   │   ├── auth.py            register + login (authentication)
│   │   ├── prompt.py          create/append/patch transactions + authorization
│   │   ├── experiment.py      run experiment (2-transaction), score, retrieval, list_models
│   │   ├── embedding.py       (re)generate a version's embedding; status; auto-embed hook
│   │   ├── search.py          semantic search (embed query -> pgvector cosine, visibility-filtered)
│   │   └── graph.py           Phase 7 — PostgreSQL authorization + title re-read around graph traversal; post-commit projection hook
│   ├── repositories/
│   │   ├── user.py            get_by_id / get_by_email / add_user
│   │   ├── prompt.py          prompt/version access; visibility predicate; version-number; update
│   │   ├── model.py           get_by_id / list_all
│   │   ├── experiment.py      add / get / list_for_prompt|version / apply_result / update_score
│   │   └── version.py         embedding read/write + semantic_search (visibility inside the query)
│   └── db/
│       ├── base.py            DeclarativeBase + constraint naming convention
│       ├── models.py          the 9 Phase 1 tables (schema only — UNCHANGED)
│       ├── session.py         lazy engine + get_db dependency + build_engine
│       └── seed.py            deterministic, idempotent dev seed data
├── alembic/
│   ├── env.py                 target_metadata = models; URL from settings/-x
│   └── versions/              0001_initial_schema · 0002_pgvector_embeddings (Phase 6; no Phase 7 migration)
├── alembic.ini
├── scripts/
│   ├── generate_embeddings.py   Phase 6 — batch (re)embed versions
│   └── sync_neo4j.py            Phase 7 — idempotent PostgreSQL → Neo4j projection (--prune / --dry-run)
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
│   ├── test_lineage.py        Phase 4A: parent_prompt_id fork rules
│   ├── test_experiments.py    Phase 5: run/score/retrieve experiments (provider mocked)
│   ├── test_embeddings_unit.py  Phase 6: embedding provider (no DB, no pgvector)
│   ├── test_semantic_search.py  Phase 6: semantic search (pgvector — skips w/ reason if absent)
│   └── test_graph.py            Phase 7: projection idempotency, traversal, authz, outage safety (Neo4j — skips w/ reason if absent)
├── requirements.txt / requirements-dev.txt
└── pyproject.toml             pytest config
```

See `../docs/api.md`, `../docs/database-design.md`, and `../docs/decisions.md`.
