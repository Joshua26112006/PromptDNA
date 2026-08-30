# PromptDNA — Architectural Decision Record

Decisions below are **locked** for the current phases. Changes require explicit
approval.

---

## Decision 1 — PostgreSQL is the system of record

**Decision:** All authoritative data lives in PostgreSQL. Every other store is
derived from it.

**Reason:** Structured relational storage, normalization (3NF), rich SQL
querying, and ACID transactions. The project's core contribution is the
relational database design.

---

## Decision 2 — Neo4j is used for prompt relationship traversal

**Decision:** Neo4j holds a projection of prompt-to-prompt relationships
(lineage, forking, dependencies) for graph traversal. It is never the source of
truth.

**Reason:** Prompt lineage and variable-depth relationships are naturally
expressed as graph traversals, which are awkward and expensive as recursive SQL.

---

## Decision 3 — pgvector is used inside PostgreSQL

**Decision:** Embeddings and semantic similarity search use the `pgvector`
extension **within** PostgreSQL. pgvector is not a separate database.

**Reason:** Semantic retrieval requires vector similarity while keeping
embeddings physically close to the relational data they describe — no cross-store
consistency problem, one system of record.

---

## Decision 4 — Embeddings belong to prompt versions

**Decision:** An embedding is associated with a `Version`, not a `Prompt`.

**Reason:** Different versions contain different text and therefore may have
different semantic representations. Attaching embeddings to the prompt would lose
that distinction.

---

## Decision 5 — Versions are immutable

**Decision:** Editing a prompt creates a new `Version`. The content of an
existing version is never updated. `version_number` is unique per prompt.

**Reason:** Historical prompt states must remain reproducible and auditable
(needed for meaningful experiment comparison over time).

---

## Decision 6 — Embedding provider is an abstraction; vector dimension is deferred

**Decision:** The embedding provider is accessed through a replaceable
abstraction. OpenAI embeddings are a likely initial provider but nothing is
hard-coded around it. The vector dimension is **not** chosen in Phase 0.

**Reason:** The dimension must match the model actually selected during the
semantic-search phase; committing to `VECTOR(1536)` now would force a migration
later. Provider lock-in would compromise the "knowledge about prompts" goal.

---

## Decision 7 — Migration tool: Alembic

**Decision:** Schema migrations use Alembic, paired with SQLAlchemy in the
FastAPI backend.

**Reason:** Standard, well-supported choice for FastAPI/SQLAlchemy; integrates
with the app's configuration for the database URL. No schema or migrations are
created in Phase 0 — only the environment is wired up.

---

## Decision 8 — Monorepo project structure

**Decision:** Single repository with `frontend/`, `backend/`, `database/`,
`docs/`, `scripts/`.

**Reason:** One coherent project; simplifies coordinated changes and
documentation. No microservices, no Kubernetes, no extra infrastructure.

---

## Decision 9 — Local development databases via docker-compose (optional)

**Decision:** `database/docker-compose.yml` provides local PostgreSQL
(`pgvector/pgvector` image) and Neo4j for development only.

**Reason:** Lets contributors run the full stack locally without manual DB
installs. It is not a production deployment — production (Vercel / Neon /
Neo4j Aura) is planned for a later phase and is not configured now.

---

## Non-decisions (explicitly deferred)

- Final relational schema — Phase 1.
- SQLAlchemy models and first migration — Phase 1.
- Vector dimension and index type — semantic-search phase.
- Neo4j integration and sync mechanism — later phase.
- Authentication, CRUD, experiments, analytics — later phases.
- Production deployment configuration — later phase.
