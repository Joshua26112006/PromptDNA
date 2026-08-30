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
```

### 2. Backend (Python 3.11+)

```bash
cd backend
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements-dev.txt   # Windows
# ./.venv/bin/pip install -r requirements-dev.txt                   # macOS/Linux
./.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

- Health check: <http://localhost:8000/health>
- API docs: <http://localhost:8000/docs>
- Tests: `./.venv/Scripts/python.exe -m pytest`

### 3. Frontend (Node 20+)

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

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

### Not started (by design)
pgvector / embeddings / semantic search, Neo4j integration, authentication,
prompt CRUD APIs, dashboard, analytics UI, production deployment.
