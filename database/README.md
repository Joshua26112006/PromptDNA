# PromptDNA — Database

PromptDNA uses a **hybrid database** design. PostgreSQL is the **system of
record**; the other two capabilities are strictly derived from it.

```
PostgreSQL 16            ── system of record (all 7 entities + 2 junctions,
  ├── relational data       normalized to 3NF, all writes, all authorization)
  └── pgvector 0.8.6     ── PostgreSQL EXTENSION (not a separate database):
                            versions.embedding vector(1536) + HNSW index
                            → cosine semantic search

Neo4j 5.26 Community     ── derived, ONE-WAY graph projection of prompt-to-prompt
  └── (:Prompt) nodes +     relationships, for variable-depth traversal.
      DERIVED_FROM etc.      Never authoritative; fully rebuildable from PostgreSQL.
```

- **PostgreSQL is authoritative.** If PostgreSQL and Neo4j ever disagree,
  PostgreSQL wins. `pgvector` runs *inside* PostgreSQL — same database, same
  connection, same transaction, same authorization filter.
- **Neo4j is a projection**, written only in the direction `PostgreSQL → Neo4j`
  (never `↔`). It can lag or be wiped without data loss.

Full rationale: `../docs/architecture.md`, `../docs/database-design.md`,
`../docs/decisions.md`.

## Current state (Phases 0–7 implemented)

### PostgreSQL — relational core (Phase 1)

- **9 tables**: `users`, `prompts`, `versions`, `models`, `experiments`,
  `tags`, `collections`, `prompt_tags`, `prompt_collections`.
- Schema is defined by the SQLAlchemy models in
  `../backend/app/db/models.py` and created by Alembic migrations. `alembic
  check` confirms models and migrations agree.
- UUID primary keys, explicit foreign keys with locked `ON DELETE` behavior
  (`CASCADE` / `SET NULL` / `RESTRICT`), `CHECK` constraints, `TIMESTAMPTZ`
  timestamps, immutable `versions` rows, and a small set of justified B-tree
  indexes. Full details: `../docs/database-design.md`.

### pgvector — semantic search (Phase 6)

- Migration **`0002_pgvector_embeddings`** runs `CREATE EXTENSION vector` and
  adds two nullable columns to `versions`:
  - `embedding vector(1536)` — the embedding of that version's `content`.
  - `embedding_model varchar(100)` — which model produced the vector.
- Index `ix_versions_embedding_hnsw` — **HNSW**, operator class
  `vector_cosine_ops` (matches the `<=>` cosine-distance operator the search
  query uses). Similarity returned by the API is `1 - cosine_distance`.
- The embedding is **derived data**: PostgreSQL `content` is authoritative, a
  provider failure never changes a version, and embeddings can be rebuilt with
  `../backend/scripts/generate_embeddings.py`.
- Feature-gated by `PGVECTOR_ENABLED`. When `false`, the embedding columns are
  not mapped, migration `0002` is not applied, and the semantic-search
  endpoints return `503` — lexical search and everything else are unaffected.

### Neo4j — graph projection (Phase 7)

- Contains **only** `(:Prompt {prompt_id, title})` nodes. `prompt_id` is the
  **same value** as `prompts.prompt_id` (the identity bridge). No `User`,
  `Version`, `Model`, `Experiment`, `Tag`, or `Collection` nodes.
- **Only three relationship types**, all `(:Prompt)->(:Prompt)`:

  | Type | Meaning | Authoritative source | Projected today |
  |------|---------|----------------------|-----------------|
  | `DERIVED_FROM` | child prompt was created from parent | `prompts.parent_prompt_id` | **yes** |
  | `FORKED_FROM` | child is an independent copy of parent | *none in the schema* | no — modelled, not populated |
  | `DEPENDS_ON` | prompt explicitly requires another prompt | *none in the schema* | no — modelled, not populated |

  `FORKED_FROM` and `DEPENDS_ON` are first-class in the graph service and
  traversal layer, but the **projection creates none** because the locked
  relational schema has no authoritative column for them. Relationships are
  never inferred from prompt text, embeddings, or an AI model.
- One schema object: `CREATE CONSTRAINT prompt_id_unique … REQUIRE
  p.prompt_id IS UNIQUE` (idempotent; never deletes data).
- **No PostgreSQL schema change and no Alembic migration** were added for
  Phase 7 — `alembic check` is still clean.
- Feature-gated by `NEO4J_ENABLED` (default `false`). When disabled or
  unreachable, `/api/v1/graph/*` returns `503`; the core app is unaffected and
  a Neo4j outage never rolls back a PostgreSQL write (eventual consistency).

## Files here

| File | Purpose |
|------|---------|
| `examples.sql` | Read-only demonstration queries: relational (JOINs, recursive lineage CTE, aggregates), pgvector cosine similarity + semantic-search ordering, `EXPLAIN`/index inspection, plus reference Cypher for the graph projection. Not wired to any API. |
| `docker-compose.yml` | Optional local **PostgreSQL 16 + pgvector** (`pgvector/pgvector:pg16`) and **Neo4j 5 Community** for development. Throwaway credentials; **not** a production deployment. |

## Create and populate

From an empty PostgreSQL database (with the `vector` extension available):

```bash
cd ../backend
./.venv/Scripts/alembic.exe upgrade head          # 0001 (9 tables) + 0002 (pgvector)
./.venv/Scripts/python.exe -m app.db.seed          # deterministic dev data (rerunnable)
./.venv/Scripts/python.exe scripts/generate_embeddings.py   # backfill version embeddings (needs pgvector)
```

Project the graph into Neo4j (idempotent; needs `NEO4J_ENABLED=true` +
`NEO4J_URI` / `NEO4J_PASSWORD`):

```bash
./.venv/Scripts/python.exe -m scripts.sync_neo4j            # MERGE a node per prompt + DERIVED_FROM edges
./.venv/Scripts/python.exe -m scripts.sync_neo4j --prune    # also drop nodes whose prompt is gone from PostgreSQL
./.venv/Scripts/python.exe -m scripts.sync_neo4j --dry-run  # print the plan; never contacts Neo4j
```

Reset / round-trip:

```bash
./.venv/Scripts/alembic.exe downgrade base        # drop everything
./.venv/Scripts/alembic.exe upgrade head
```

The PostgreSQL URL comes from `DATABASE_URL` (see the repo-root `.env.example`);
`alembic.ini`'s `sqlalchemy.url` is intentionally blank.

## Run the demonstration queries

```bash
psql "$DATABASE_URL" -f examples.sql               # relational + pgvector sections
```

(Load the seed data and generate embeddings first so the pgvector queries
return rows.) The Cypher block at the end of `examples.sql` is for the Neo4j
Browser (`http://localhost:7474`) or `cypher-shell` — not `psql`.

## Local development databases (optional)

```bash
cd database
docker compose up -d      # start PostgreSQL (+pgvector) + Neo4j
docker compose down       # stop
docker compose down -v    # stop and delete local data
```

Then set, in the repo-root `.env`:

```
DATABASE_URL=postgresql+psycopg://promptdna:promptdna@localhost:5432/promptdna
NEO4J_ENABLED=true
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=promptdna_dev
```
