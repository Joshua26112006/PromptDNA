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
