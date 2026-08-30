# PromptDNA — Architecture

> **PromptDNA — An Intelligent Knowledge Database for Prompt Engineering and
> Large Language Models.**
>
> This is a **Database Systems** project. The database architecture is the core
> contribution. AI / LLM functionality is an application domain, not the primary
> contribution. The guiding idea: *we are not simply storing prompts — we are
> storing structured knowledge about prompts.*

## Hybrid database architecture

```
                         ┌──────────────────────────────────────┐
                         │            PostgreSQL                 │
   FastAPI  ────────────►│  system of record                    │
   (Python)              │                                      │
                         │   ├── relational data (3NF)          │
                         │   └── pgvector extension             │
                         │         └── embeddings / semantic    │
                         │             similarity search        │
                         └──────────────────────────────────────┘
                                        │
                                        │  projection of relationship data
                                        ▼
                         ┌──────────────────────────────────────┐
                         │              Neo4j                    │
                         │  supporting graph projection         │
                         │   prompt relationships / lineage     │
                         └──────────────────────────────────────┘
```

- **PostgreSQL is authoritative.** All writes go here first.
- **`pgvector` is a PostgreSQL extension**, *not* a separate database. Embeddings
  live next to the relational rows they describe.
- **Neo4j is a projection.** It holds prompt-to-prompt relationships for
  variable-depth traversal (lineage, forking, dependencies). It is derived from
  PostgreSQL and never the source of truth.

## Technology stack (locked)

| Layer              | Technology                                  |
| ------------------ | ------------------------------------------- |
| Frontend           | Next.js, React, Tailwind CSS                |
| Backend            | FastAPI, Python                             |
| Primary database   | PostgreSQL                                  |
| Vector search      | pgvector (PostgreSQL extension)             |
| Graph              | Neo4j                                       |
| Embedding provider | Provider abstraction (replaceable)          |

The embedding provider is deliberately **not** hard-coded. OpenAI embeddings are
a likely initial provider, but the integration must be replaceable, and the
**vector dimension is not chosen yet** — it will be derived from the model
selected during the semantic-search phase.

## Deployment (later — not configured in Phase 0)

Planned targets: Vercel (frontend), Neon (PostgreSQL), Neo4j Aura (graph). No
production deployment is configured in Phase 0.

## Repository layout

```
promptdna/
├── frontend/    Next.js + React + Tailwind (development shell only)
├── backend/     FastAPI app, config, Alembic scaffold, tests
├── database/    DB docs + optional local docker-compose (Postgres + Neo4j)
├── docs/        architecture / database-design / decisions
├── scripts/     developer helper scripts
├── .gitignore
├── README.md
└── .env.example
```

## Phase 0 scope

Establish a clean development foundation only:

- runnable frontend shell,
- runnable backend with `GET /health`,
- configuration + environment loading,
- migration tool wired up with **no schema**,
- documentation of the approved architecture.

Explicitly **out of scope** for Phase 0: dashboard, authentication, CRUD,
semantic search, Neo4j integration, experiments, analytics, and the final
database schema.

## Phase 1 scope (done)

PostgreSQL relational core: 9 tables as SQLAlchemy models + Alembic migration
`0001_initial_schema`, UUID PKs, locked `ON DELETE` behavior, `CHECK`
constraints, justified indexes, deterministic seed data, PostgreSQL-backed
tests. See `database-design.md`.

## Phase 2 scope (done) — database-backed backend + first Prompt APIs

Layered FastAPI backend over the (unchanged) Phase 1 schema:

```
HTTP request
  → FastAPI router        app/api/routes/{health,prompts}.py   — thin
  → Pydantic schema       app/schemas/prompt.py                 — shape validation
  → Service layer         app/services/prompt.py                — rules + transactions
  → Repository            app/repositories/prompt.py            — SQLAlchemy access
  → SQLAlchemy 2.x  →  PostgreSQL
  → Response schema  →  HTTP response
```

- **Session management**: one engine + `sessionmaker` per process (lazy,
  reused); `get_db` FastAPI dependency yields one session per request and closes
  it; the service layer owns commit/rollback. `DATABASE_URL` from config, never
  logged. PostgreSQL only.
- **Endpoints**: `GET /health`, `GET /health/db` (`SELECT 1`) outside the
  versioned prefix; `POST /api/v1/prompts`, `GET /api/v1/prompts`,
  `GET /api/v1/prompts/{id}`, `GET /api/v1/prompts/{id}/versions`.
- **Transaction**: creating a prompt inserts the prompt **and its Version 1**
  atomically; failure of either rolls back both.
- **Dev user**: `X-Dev-User-ID` header names an existing user (owner of created
  prompts). Development-only, not authentication — see `api.md`.
- **Errors**: uniform `{"detail": …}`; no SQL/credentials/stack traces to
  clients; app runs `debug=False`.
- **CORS**: explicit origin allow-list from `CORS_ORIGINS` (no `*`).
- **No schema change.** No new migration.

Explicitly **out of scope** for Phase 2 (later phases): authentication/JWT/OAuth,
Neo4j, pgvector/embeddings/semantic search, AI model calls, prompt
update/delete, version creation/editing, dashboard, analytics.

Full endpoint reference: `api.md`.
