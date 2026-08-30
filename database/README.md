# PromptDNA — Database

PostgreSQL is the **system of record**. Neo4j is a **supporting graph
projection** for prompt relationships / lineage (later phase). `pgvector` is a
PostgreSQL extension (not a separate database) for embeddings / semantic search
(later phase).

```
PostgreSQL
  ├── relational data                 <-- Phase 1 (implemented)
  └── pgvector  ──►  embeddings / semantic search   (later)

Neo4j
  └── prompt relationships / lineage  (projection of PostgreSQL, later)
```

## Phase 1 status — implemented

- **9 tables**: `users`, `prompts`, `versions`, `models`, `experiments`,
  `tags`, `collections`, `prompt_tags`, `prompt_collections`.
- Schema is defined by SQLAlchemy models in
  `../backend/app/db/models.py` and created by the Alembic migration
  `../backend/alembic/versions/0001_initial_schema.py`. `alembic check` confirms
  the two agree.
- UUID primary keys, explicit foreign keys with locked `ON DELETE` behavior,
  `CHECK` constraints, `TIMESTAMPTZ` timestamps, and a small set of justified
  B-tree indexes. Full details: `../docs/database-design.md`.
- **No** pgvector, embeddings, semantic search, or Neo4j — those are later
  phases.

## Files here

| File | Purpose |
|------|---------|
| `examples.sql` | 10 demonstration queries + an `EXPLAIN` / index-inspection section. Read-only; not wired to any API. |
| `docker-compose.yml` | Optional local PostgreSQL (`pgvector/pgvector` image) + Neo4j for development. Not a production deployment. |

## Create and populate the schema

From an empty PostgreSQL database:

```bash
cd ../backend
./.venv/Scripts/alembic.exe upgrade head        # create all 9 tables
./.venv/Scripts/python.exe -m app.db.seed        # deterministic dev data (rerunnable)
```

Reset / round-trip:

```bash
./.venv/Scripts/alembic.exe downgrade base       # drop everything
./.venv/Scripts/alembic.exe upgrade head
```

The URL comes from `DATABASE_URL` (see repo-root `.env.example`);
`alembic.ini`'s `sqlalchemy.url` is intentionally blank.

## Run the demonstration queries

With a client that has `psql`:

```bash
psql "$DATABASE_URL" -f examples.sql
```

(Load the seed data first so the queries return rows.)

## Local development databases (optional)

```bash
cd database
docker compose up -d      # start PostgreSQL + Neo4j
docker compose down       # stop
docker compose down -v    # stop and delete local data
```

Then set `DATABASE_URL` in the repo-root `.env` to match, e.g.
`postgresql+psycopg://promptdna:promptdna@localhost:5432/promptdna`.
