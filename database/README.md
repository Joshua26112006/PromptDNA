# PromptDNA — Database

PostgreSQL is the **system of record**. Neo4j is a **supporting graph
projection** for prompt relationships / lineage. `pgvector` is a PostgreSQL
extension (not a separate database) used for embeddings and semantic
similarity search.

```
PostgreSQL
  ├── relational data
  └── pgvector  ──►  embeddings / semantic search

Neo4j
  └── prompt relationships / lineage  (projection of PostgreSQL)
```

## Phase 0 status

- **No schema exists yet.** The relational schema is designed and implemented
  in Phase 1. See `../docs/database-design.md` for the approved plan.
- Migrations are managed with **Alembic**, configured under
  `../backend/alembic/` (`../backend/alembic.ini`). The `versions/` directory
  is intentionally empty.
- Neo4j is **not** integrated in Phase 0.

## Local development databases (optional)

`docker-compose.yml` starts a local PostgreSQL (with the `pgvector` extension
available) and a local Neo4j, for development only. It is **not** a production
deployment (production is planned later on Neon + Neo4j Aura).

```bash
cd database
docker compose up -d      # start
docker compose down       # stop
docker compose down -v    # stop and delete local data
```

Then set `DATABASE_URL` / `NEO4J_*` in the repo-root `.env` to match.

## Running migrations (Phase 1 onward)

```bash
cd backend
./.venv/Scripts/alembic upgrade head          # Windows
# .venv/bin/alembic upgrade head              # macOS / Linux
```

The database URL is read from the application's `DATABASE_URL` setting
(`backend/app/core/config.py`); `alembic.ini` deliberately leaves
`sqlalchemy.url` blank.
