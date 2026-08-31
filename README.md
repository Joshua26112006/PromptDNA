# PromptDNA

**PromptDNA — An Intelligent Knowledge Database for Prompt Engineering and Large
Language Models.**

PromptDNA is a database-driven knowledge management platform for AI prompts:
create, organize, version, search, test, and analyze prompts. The central idea is
that we are **not simply storing prompts — we are storing structured knowledge
about prompts.**

This is a **Database Systems** project: the database architecture is the core
contribution; AI/LLM functionality is an application domain on top of it.

## Architecture (hybrid database)

```
PostgreSQL  ── system of record
  ├── relational data (normalized to 3NF)
  └── pgvector extension ──► embeddings / semantic similarity search

Neo4j       ── supporting graph projection
  └── prompt relationships / lineage  (derived from PostgreSQL)
```

- **PostgreSQL is authoritative.** `pgvector` is a PostgreSQL *extension*, not a
  separate database.
- **Neo4j is a projection** of prompt-to-prompt relationships for variable-depth
  traversal; never the source of truth.
- The **embedding provider is a replaceable abstraction**; the vector dimension
  is intentionally undecided until the embedding model is chosen.

See [`docs/architecture.md`](docs/architecture.md),
[`docs/database-design.md`](docs/database-design.md), and
[`docs/decisions.md`](docs/decisions.md).

## Technology stack

| Layer            | Technology                        |
| ---------------- | -------------------------------- |
| Frontend         | Next.js, React, Tailwind CSS     |
| Backend          | FastAPI, Python                  |
| Primary database | PostgreSQL                       |
| Vector search    | pgvector (PostgreSQL extension)  |
| Graph            | Neo4j                           |
| Migrations       | Alembic                         |

Deployment (later, not configured now): Vercel, Neon, Neo4j Aura.

## Repository structure

```
PromptDNA/
├── frontend/     Next.js + React + Tailwind — development shell only
├── backend/      FastAPI app, config, Alembic scaffold, tests
├── database/     DB docs + optional local docker-compose (Postgres + Neo4j)
├── docs/         architecture / database-design / decisions
├── scripts/      dev helper scripts (dev.sh / dev.ps1)
├── .gitignore
├── README.md
└── .env.example
```

## Getting started

### 1. Environment

```bash
cp .env.example .env      # fill in as needed; never commit .env
# REQUIRED for the API to start (Phase 3):
#   JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(64))")
```

### 2. Backend (Python 3.11+)

```bash
cd backend
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements-dev.txt   # Windows
# ./.venv/bin/pip install -r requirements-dev.txt                   # macOS/Linux
# DATABASE_URL -> Phase 1 schema; JWT_SECRET_KEY -> a strong random value
./.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

- Liveness: <http://localhost:8000/health> · DB readiness: <http://localhost:8000/health/db>
- Auth: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`
- Prompts/versions: `/api/v1/prompts…` · Experiments: `/api/v1/prompts/{id}/versions/{vid}/experiments`, `/api/v1/experiments/{id}`, `/api/v1/models`
- API (v1): send `Authorization: Bearer <token>` · docs: <http://localhost:8000/docs>
- Experiments (Phase 5): set `OPENAI_API_KEY` for real OpenAI execution; without it the built-in `mock` provider (`ENABLE_MOCK_PROVIDER=true`) runs models whose `provider` is `mock`.
- Tests (need a real PostgreSQL test DB):
  `PROMPTDNA_TEST_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/promptdna_test ./.venv/Scripts/python.exe -m pytest`
- Full endpoint reference: [`docs/api.md`](docs/api.md)

### 3. Frontend (Node 20+)

```bash
cd frontend
npm install
cp .env.example .env.local     # set NEXT_PUBLIC_API_BASE_URL (default http://localhost:8000)
npm run dev        # http://localhost:3000  — open /login
npm run lint
npm run build
npm run test       # vitest — no backend needed
```

Pages: `/login`, `/register`, `/prompts` (Prompt Library), `/prompts/new`,
`/prompts/[prompt_id]` (Prompt Detail — versions, history, owner-only editing).

### 4. Database (Phase 1)

```bash
cd database && docker compose up -d          # optional local PostgreSQL + Neo4j
cd ../backend
./.venv/Scripts/alembic.exe upgrade head      # create the 9-table schema
./.venv/Scripts/python.exe -m app.db.seed     # deterministic dev data
```

See [`docs/database-design.md`](docs/database-design.md) for the full schema and
[`database/examples.sql`](database/examples.sql) for demonstration queries.

## Project status

### Phase 0 — foundation ✅
Monorepo structure, runnable frontend shell, runnable FastAPI backend with
`GET /health`, environment configuration, architecture documentation.

### Phase 1 — PostgreSQL relational core ✅
Nine tables (`users`, `prompts`, `versions`, `models`, `experiments`, `tags`,
`collections`, `prompt_tags`, `prompt_collections`) as SQLAlchemy models + one
Alembic migration (`alembic check` clean), UUID PKs, locked `ON DELETE`
behavior, `CHECK` constraints, justified B-tree indexes, `TIMESTAMPTZ`
timestamps, deterministic seed data, and a PostgreSQL-backed test suite
(15 mandated schema checks + extras).

### Phase 2 — database-backed backend + Prompt API ✅
Layered FastAPI backend (router → schema → service → repository → SQLAlchemy)
over the **unchanged** Phase 1 schema. Per-request DB session dependency;
`GET /health` + `GET /health/db`; `POST/GET /api/v1/prompts`,
`GET /api/v1/prompts/{id}`, `GET /api/v1/prompts/{id}/versions`. Creating a
prompt writes the prompt **and its Version 1** in one transaction (rollback
tested). Versions are read-only/immutable. Pagination + lexical `title` search.
Uniform error bodies (no SQL/credentials/traces). CORS allow-list.

### Phase 3 — authentication, authorization & ownership ✅
JWT bearer auth: `POST /api/v1/auth/register` (Argon2 password hashing),
`POST /api/v1/auth/login` (OAuth2 form → access token), `GET /api/v1/auth/me`.
Minimal token claims (`sub`, `iat`, `exp`); `JWT_SECRET_KEY` required (no
fallback). The Phase 2 `X-Dev-User-ID` header is **removed** — prompt ownership
comes from the token. Per-user authorization in the service layer: a prompt is
visible to its owner or if `is_public`; other users' private prompts return
`404`. Minimal Next.js `/login` + `/register` flow (token in `localStorage` —
XSS trade-off documented).

### Phase 4A — core prompt & version management ✅
`POST /api/v1/prompts/{id}/versions` (append an immutable version; owner-only;
`version_number` = max+1; bounded retry then `409` on the unique-constraint
race), `GET /api/v1/prompts/{id}/versions/{vid}` (belongs-to + visibility
checked; `404` otherwise), `PATCH /api/v1/prompts/{id}` (metadata only, owner
only). `parent_prompt_id` optional on create — fork/derive from any prompt you
can view; the fork is owned by the creator, the parent is untouched. Versions
have **no** PUT/PATCH/DELETE. Search stays lexical.

### Phase 4B — Prompt Library frontend ✅
Real authenticated UI on the existing frontend (Next.js App Router). Pages:
`/login`, `/register`, `/prompts` (library — backend `search`, `is_public`
filter, `limit`/`offset` pagination), `/prompts/new` (create prompt + Version 1),
`/prompts/[prompt_id]` (metadata, current version, version history, single
parent "Derived from" link, owner-only Edit Metadata / Create New Version).
Centralized `lib/api.ts` client; `AuthProvider` with
`loading`/`authenticated`/`unauthenticated`; protected route group. Vitest +
React Testing Library added.

### Phase 5 — experiment system + AI model execution ✅
`POST /api/v1/prompts/{id}/versions/{vid}/experiments` runs a **specific
immutable version's content** against a model behind an `LLMProvider`
abstraction (`app/providers/`: `MockProvider` for dev/tests, `OpenAIProvider`
real via `httpx`). Owner-only execution (public prompt → `403`). Lifecycle:
`PENDING` committed → provider call (timed with `perf_counter`, `EXPERIMENT_
PROVIDER_TIMEOUT_S`) → `SUCCESS` (output stored) or `FAILED` (safe
`error_message`) — never faked. No DB transaction is held across the external
call. `GET /api/v1/prompts/{id}/experiments`, `GET .../versions/{vid}/experiments`,
`GET /api/v1/experiments/{id}` (authorized via the owning prompt),
`PATCH /api/v1/experiments/{id}` (owner-only score 0–10 / notes),
`GET /api/v1/models` (with `execution_configured`, never keys). Frontend:
experiment history + owner-only "Run Experiment" on `/prompts/[id]`.
**No schema change, no migration.** Neo4j / pgvector / semantic search untouched.

### Not started (by design)
Prompt deletion, version editing, recursive/graph lineage APIs, refresh tokens /
token revocation, roles / RBAC / SSO, rate limiting, automatic AI scoring,
pgvector / embeddings / semantic search, Neo4j integration, tags/collections UI,
dashboard, analytics UI, production deployment.
