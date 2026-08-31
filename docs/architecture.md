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
- **Dev user (Phase 2 only, REMOVED in Phase 3)**: `X-Dev-User-ID` header named
  an existing user. Replaced by JWT auth below.
- **Errors**: uniform `{"detail": …}`; no SQL/credentials/stack traces to
  clients; app runs `debug=False`.
- **CORS**: explicit origin allow-list from `CORS_ORIGINS` (no `*`).
- **No schema change.** No new migration.

## Phase 3 scope (done) — authentication, authorization & user ownership

```
Next.js (login / register / me pages; token in localStorage)
    │  Authorization: Bearer <JWT>
    ▼
CORS  →  FastAPI
    ▼
get_current_user            app/api/deps.py
  • verify JWT signature + expiry (app/core/security.py, PyJWT / HS256)
  • sub -> user_id -> load User from PostgreSQL
    ▼
Authorization (per resource)   app/services/prompt.py
  • owner OR is_public  →  allowed
  • otherwise           →  404 (no existence oracle)
    ▼
Service layer  →  Repository  →  SQLAlchemy 2.x  →  PostgreSQL
```

- **Registration**: `POST /api/v1/auth/register` — validates name/email/password
  (8–128), normalises email to lower-case, checks for an existing account
  (`409`), stores only the **Argon2** hash (`pwdlib`). Returns the safe profile.
- **Login**: `POST /api/v1/auth/login` — OAuth2 password form (`username` =
  email). Verifies against the hash; **generic `401`** ("Invalid email or
  password.") for any failure. Issues a JWT access token.
- **JWT**: minimal claims `sub` (= `user_id`), `iat`, `exp`
  (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 30). `JWT_SECRET_KEY` from environment;
  **no fallback** — the app refuses to start without it. Never logged/returned.
- **Current-user dependency**: `get_current_user` → `401` for missing /
  malformed / bad-signature / expired token, or a `sub` with no matching user
  (`WWW-Authenticate: Bearer`).
- **`GET /api/v1/auth/me`**: returns the authenticated profile.
- **X-Dev-User-ID removed**: no longer read anywhere; sending it does nothing.
  Prompt ownership (`prompts.user_id`, `versions.created_by`) is taken from the
  token — the client cannot set or spoof it.
- **Prompt authorization** (service layer, never in routes): a prompt is visible
  iff the caller owns it **or** `is_public = true`. `GET /prompts` applies this
  as a SQL predicate ANDed with user filters (no query param can widen it).
  Single-prompt / versions access → **404** when not visible.
- **Logout**: stateless — client discards the token. No server-side revocation,
  no sessions table.
- **Token storage (frontend)**: `localStorage` for this dev build; XSS
  trade-off documented in `decisions.md`.
- **No schema change.** `users.password_hash` (Phase 1) is sufficient. No new
  migration; `alembic check` stays clean.
- **CORS** unchanged: explicit origin allow-list + credentials.

Explicitly **out of scope** for Phase 3 (later phases): refresh tokens,
server-side revocation, RBAC / roles, SSO, rate limiting, Neo4j,
pgvector/embeddings/semantic search, AI model calls, dashboard, analytics.

## Phase 4A scope (done) — core prompt & version management

### Prompt / version model

```
Prompt  (prompts row: identity + metadata only — NO prompt text)
  user_id ............ owner            (set from the authenticated user)
  parent_prompt_id ... lineage parent  (optional; a prompt the creator can view)
  title / description / purpose / is_public
  │
  ├── Version 1   content = "Summarize this document."          created_by = <user>
  ├── Version 2   content = "Summarize in 5 bullet points."      created_by = <user>
  ├── Version 3   content = "5 bullet points + limitations."     created_by = <user>
  └── ...         (immutable; a new version is appended, never edited)
```

- **`Prompt.user_id` → ownership.** Only the owner may add versions or PATCH
  metadata. Visibility to others is `is_public`.
- **`Version.created_by` → who authored that version.** Taken from the
  authenticated user; the client cannot set it. (Today that is always the owner,
  since only the owner can create versions.)
- **Prompt content is never on the `prompts` row** — it lives in
  `versions.content`. Editing content = appending a new version.

### Endpoints added this phase

```
POST   /api/v1/prompts/{id}/versions          append version (owner only)
GET    /api/v1/prompts/{id}/versions/{vid}     one version (belongs-to + visibility checked)
PATCH  /api/v1/prompts/{id}                    metadata only (owner only)
```

plus `parent_prompt_id` accepted (optionally) on `POST /api/v1/prompts`.

### Behavior

- **Version numbering**: `MAX(version_number) + 1`, read fresh from PostgreSQL
  per attempt. `UNIQUE (prompt_id, version_number)` is the final guard; the
  service retries on the race (bounded), then returns `409`.
- **Transactions** (service-owned): create prompt = INSERT prompt + INSERT
  version 1, one commit; create version = SELECT max → INSERT version, one
  commit; PATCH = UPDATE prompts (metadata columns), one commit. Rollback on any
  failure.
- **Immutability**: no `PUT`/`PATCH`/`DELETE` for a version; `content` /
  `version_number` / `created_by` / `created_at` of an existing version are
  unreachable for mutation. No prompt `DELETE` (deferred).
- **Lineage**: `prompts.parent_prompt_id` only — a fork/derivation link. The
  child is owned by its creator; the parent is untouched. No recursive lineage
  APIs, no graph store.
- **Search** stays lexical (`ILIKE` on `title`), applied after the visibility
  predicate.
- **No schema change, no migration**; `alembic check` clean. Neo4j, pgvector,
  embeddings, and semantic search remain untouched.

Explicitly **out of scope** for Phase 4A: prompt deletion, version editing,
recursive lineage / graph APIs, tags/collections management, dashboard, and all
Phase 4B+ features.

Full endpoint reference: `api.md`.

## Phase 4B scope (done) — Prompt Library frontend

```
Browser (Next.js App Router, React, TypeScript, Tailwind)
   │   fetch() with Authorization: Bearer <JWT from localStorage>
   ▼
lib/api.ts  — single client: NEXT_PUBLIC_API_BASE_URL, bearer header, JSON
              parsing, ApiError + friendlyMessage()
   ▼
FastAPI  →  service  →  repository  →  PostgreSQL   (unchanged)
```

- **No backend or database change.** Frontend only.
- **Auth state** (`lib/auth-context.tsx`): `status` is `loading` →
  `authenticated` | `unauthenticated`. On mount it resolves the stored token via
  `GET /auth/me`. `login`/`register` store the token and refetch the user.
  `logout` clears the token + state and routes to `/login` (client-side only —
  Phase 3 stateless JWT).
- **Protected route group** `app/(app)/*` renders inside `<ProtectedShell>`:
  spinner while `loading`, `router.replace("/login")` while `unauthenticated`,
  the app shell (brand, nav, current user, logout) once `authenticated`. `/login`
  and `/register` bounce to `/prompts` when already authenticated.
- **Pages**: `/login`, `/register`, `/prompts` (library), `/prompts/new`,
  `/prompts/[prompt_id]` (detail).
- **Prompt Library**: calls `GET /api/v1/prompts` with `search` (lexical title),
  `is_public` (All/Public/Private filter) and `limit`/`offset`; pagination uses
  the backend `total`. No client-side filtering of a downloaded page.
- **Prompt Detail**: `GET /api/v1/prompts/{id}` (metadata + current version) and
  `GET /api/v1/prompts/{id}/versions` (history). Owner-only, in-page:
  `PATCH /api/v1/prompts/{id}` (metadata) and
  `POST /api/v1/prompts/{id}/versions` (`content` + `change_summary` only).
  Historical versions render read-only with an "IMMUTABLE" marker and **no**
  edit/delete controls anywhere. A single `parent_prompt_id` shows a "Derived
  from" link (or "not accessible to you" on a 404).

### Ownership / creator in the UI

```
Prompt.user_id      → the prompt's owner  → controls "Edit Metadata" and
                      "Create New Version" visibility (backend enforces 403/404)
Version.created_by  → who wrote that version → shown as "you" / "another user"
```

Hidden buttons are UX only. The FastAPI backend remains the sole authority for
authentication, authorization, ownership, visibility, validation, version
numbering, and version immutability.

### Testing

Vitest + React Testing Library (`frontend/__tests__/`, jsdom, `lib/api` and
`lib/auth-context` mocked — no backend, no real AI). 18 tests: page render,
list display, search-param wiring, pagination offset, detail loading/404,
version history, owner vs non-owner controls, immutable-version controls,
create-prompt payload, create-version payload, logout state.

**Semantic search is not implemented yet. The current search is lexical title
search backed by PostgreSQL (`ILIKE`).**

Explicitly **out of scope** for Phase 4B: semantic search,
tags/collections/graph/analytics UI, prompt deletion UI.

## Phase 5 scope (done) — experiment system + AI model execution

```
Prompt ─ Version N ──(experiments.version_id)──►  Experiment  ──(experiments.model_id)──►  Model
                                                     │
                                       app/services/experiment.py
                                                     │
                                       app/providers/  (LLMProvider abstraction)
                                        ├── MockProvider   (provider "mock" — dev/tests, deterministic)
                                        └── OpenAIProvider  (provider "OpenAI" — real, httpx, needs OPENAI_API_KEY)
                                                     │
                                              AI model API
```

An **experiment records the execution of a specific immutable prompt version
against a specific model, preserving the result and execution metadata for
later comparison.** It references `version_id` directly (not "the prompt") and
runs `version.content` **verbatim** — never a prompt reconstructed from
title/description — so a run is reproducible.

- **Provider abstraction** (`app/providers/base.py`): `LLMProvider` with
  `is_configured()` and `generate(model_name, prompt_text, timeout_s) -> str`,
  raising typed `ProviderError` (`ProviderNotConfigured`, `ProviderTimeout`,
  `ProviderRequestError`). The service never sees HTTP. `registry.get_provider`
  maps a `models.provider` string → provider instance.
- **Providers**: `MockProvider` (key `mock`, always configured, deterministic
  echo — an explicit dev/test provider, not a fake of a vendor);
  `OpenAIProvider` (key `openai`, `httpx` POST to `/chat/completions`, per-call
  timeout, `is_configured()` = `OPENAI_API_KEY` set). GPT-5/Claude/Gemini seed
  rows have a registered provider but are unconfigured without a key → runs
  against them return `503` cleanly (no experiment row).
- **Endpoints** (all auth-required):
  `POST /api/v1/prompts/{id}/versions/{vid}/experiments` (owner only — `403`
  for a public prompt owned by another user, `404` for private/missing),
  `GET /api/v1/prompts/{id}/experiments`,
  `GET /api/v1/prompts/{id}/versions/{vid}/experiments`,
  `GET /api/v1/experiments/{id}` (authorized through its prompt — an experiment
  id cannot bypass visibility),
  `PATCH /api/v1/experiments/{id}` (owner-only `score` 0–10 / `notes`),
  `GET /api/v1/models` (`execution_configured` flag; **no keys**).
- **Lifecycle & transactions**: validate → `BEGIN; INSERT experiment PENDING;
  COMMIT` → `provider.generate()` (**no DB transaction held**) → `BEGIN; UPDATE
  experiment SUCCESS|FAILED (+output/error, response_time_ms, executed_at);
  COMMIT`. A failed/timed-out/malformed provider call is recorded as `FAILED`
  with a safe `error_message` — never faked as `SUCCESS`.
- **Response time**: wall-clock duration of the provider call via
  `time.perf_counter()` (monotonic), stored as integer milliseconds. Not
  fabricated; not derived from timestamps.
- **Score** (`experiments.score`, DB `CHECK 0..10`) is a **human** rating set
  via `PATCH` by the owner — no automatic AI scoring algorithm.
- **API-key security**: keys are server-side settings only — never in a
  response, a log line, a DB row, or an error message.
- **No schema change** (the Phase 1 `experiments` / `models` tables already fit)
  and **no migration**; `alembic check` clean. Neo4j / pgvector / semantic
  search untouched.
- **Frontend**: `/prompts/[id]` gains an Experiments section — history (status,
  model, version, response time, score-or-"Not scored", output/error) and, for
  the owner, a "Run Experiment" form (model select + notes) that shows exactly
  which version is being tested. Vitest suite mocks the API — no real AI.

Explicitly **out of scope** for Phase 5: pgvector / embeddings / semantic
search, Neo4j, automatic scoring, analytics, rate limiting, retries beyond a
bounded/none policy.

## Phase 6 scope (done) — pgvector + embeddings + semantic search

```
Next.js  (Prompt Library: "Search by text" | "Semantic Search")
   ▼
FastAPI  /api/v1/search/semantic ,  /api/v1/versions/{id}/embedding
   ▼
Semantic Search Service        app/services/{search,embedding}.py
   ▼
Embedding Provider             app/embeddings/  (EmbeddingProvider)
   ├── MockEmbeddingProvider    deterministic bag-of-hashed-tokens, dim 1536 (dev/tests)
   └── OpenAIEmbeddingProvider  text-embedding-3-small -> 1536-d (needs OPENAI_API_KEY)
   ▼
PostgreSQL + pgvector          versions.embedding  vector(1536)   (migration 0002)
   ▼
vector similarity search       ORDER BY embedding <=> :query   (cosine), HNSW index
```

**The relational database stays authoritative. The embedding is derived from
`Version.content`:**

```
Version
  ├── content          (immutable, authoritative)
  └── embedding         (derived, nullable, recoverable — pgvector)
      embedding_model   (which model produced it)
```

- **Embedding belongs to `versions`** (each version's text has its own meaning),
  associated by `versions.version_id`. `versions.content` is never modified when
  an embedding is generated.
- **Vector dimension = 1536** — chosen to match OpenAI `text-embedding-3-small`
  (the intended real provider). The mock provider is configured to the same
  1536, so switching to OpenAI needs no migration. The column dimension is fixed
  by migration `0002`; changing the model/dimension later needs a new migration
  + re-embed (documented as future work).
- **Distance metric = cosine.** Query: `1 - (embedding <=> :qvec)` as
  `similarity`, `ORDER BY embedding <=> :qvec`. HNSW index with
  `vector_cosine_ops` (`ix_versions_embedding_hnsw`). "similarity" is a
  **semantic-similarity** score (meaning closeness) — *not* an experiment score
  (model-run quality); they are different concepts.
- **Provider abstraction** (`app/embeddings/base.py`): `EmbeddingProvider` with
  `dimension`, `is_configured()`, `embed(text, timeout_s) -> list[float]`,
  typed `EmbeddingError` subclasses (`NotConfigured`, `Timeout`, `RequestError`,
  `DimensionMismatch`). One active provider per deployment (`EMBEDDING_PROVIDER`).
- **Endpoints** (auth required): `GET /api/v1/search/semantic` (`query`,
  `limit`, `is_public`, `owner`); `POST /api/v1/versions/{id}/embedding`
  (owner-only (re)generate — it can cost money); `GET /api/v1/versions/{id}/embedding`
  (status). Raw vectors are **never** returned.
- **Authorization is part of the SQL query** — `WHERE embedding IS NOT NULL AND
  (prompts.user_id = :viewer OR prompts.is_public)` — so another user's private
  prompts are never even scored, let alone returned. Not
  retrieve-all-then-filter.
- **Embedding lifecycle**: best-effort synchronous embed after a version is
  committed (`EMBEDDING_AUTOGENERATE`, off by default; needs pgvector). On
  failure the version is untouched and the embedding stays NULL — recoverable
  via the endpoint or `scripts/generate_embeddings.py`. Immutable versions mean
  an embedding is generated once, not on every view.
- **Lexical search is unchanged** (`GET /api/v1/prompts?search=` — `ILIKE` on
  title). Two clearly-labelled modes; lexical search is never called "AI search".
- **Failure / availability**: missing key → `503`; provider timeout/HTTP/
  malformed → `503` with a safe message (no keys, no raw payloads); empty query
  → `422`/`400`; dimension mismatch → typed error. On a PostgreSQL without
  pgvector, `PGVECTOR_ENABLED=false` leaves the embedding columns unmapped and
  the semantic endpoints return `503` — the rest of the API is unaffected.
- **Schema**: migration `0002` adds only `versions.embedding` +
  `versions.embedding_model` + the HNSW index + `CREATE EXTENSION vector`. No
  existing column, key, foreign key, relationship, or index is changed.
- **Neo4j remains untouched.**

Explicitly **out of scope** for Phase 6: Neo4j / graph sync / graph queries,
hybrid (lexical+vector) ranking, recommendations, prompt-optimization,
analytics.

## Phase 7 scope (done) — Neo4j graph projection + prompt relationships

```
                          PromptDNA
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
        PostgreSQL         pgvector          Neo4j
        structured         semantic          graph
          truth             search          traversal
             │  (authoritative) │                │  (derived projection)
             └────────┬─────────┴────────┬───────┘
                      ▼                  ▼
                 FastAPI            Next.js UI
```

- **"Where is the authoritative data?"** → PostgreSQL.
  **"Which prompts are semantically similar?"** → pgvector.
  **"How are prompts explicitly related?"** → Neo4j.
- **PostgreSQL is the system of record; Neo4j is a one-way derived projection**
  (`PostgreSQL → Neo4j`, never `↔`). If the two disagree, PostgreSQL wins — the
  graph API even re-reads every node's `title` from PostgreSQL and drops any
  Neo4j node PostgreSQL doesn't have.

### Why Neo4j when PostgreSQL already stores the relationships

PostgreSQL (`prompts.parent_prompt_id`, a self-referencing FK with
`ON DELETE SET NULL`) is optimal for authoritative storage and structured
queries. Relationship-centric questions — *what came from this prompt? what is
its ancestry? which prompts depend on it? what is connected across several
hops?* — are naturally expressed as Cypher graph traversals (variable-length
`-[:DERIVED_FROM|FORKED_FROM*1..N]->` patterns) rather than recursive SQL. The
projection lets those traversals be written directly against a graph.

### Node & relationship model (the ONLY things in Neo4j)

```
(:Prompt { prompt_id, title })          -- prompt_id == PostgreSQL prompts.prompt_id (identity bridge)

(:Prompt)-[:DERIVED_FROM]->(:Prompt)     -- child was created as a derivation of parent
(:Prompt)-[:FORKED_FROM]->(:Prompt)      -- child was forked from parent
(:Prompt)-[:DEPENDS_ON]->(:Prompt)       -- explicit prompt-to-prompt dependency
```

No `User` / `Version` / `Model` / `Experiment` / `Tag` / `Collection` nodes. No
`HAS_VERSION` / `USES_MODEL` / `HAS_TAG` / `OWNS` / `IN_COLLECTION` / … edges.
The graph is **not** a mirror of PostgreSQL — only prompt-to-prompt links.

### Authoritative source for each relationship

| Relationship | PostgreSQL source | Projected by sync? |
|---|---|---|
| `DERIVED_FROM` | `prompts.parent_prompt_id` (the only relationship column in the locked schema) | **yes** |
| `FORKED_FROM` | *(none — the schema doesn't record a fork flag)* | **no** — modelled, but nothing to project |
| `DEPENDS_ON` | *(none — no dependency column/table)* | **no** — modelled, but nothing to project |

`FORKED_FROM` and `DEPENDS_ON` are first-class in the graph model and fully
supported by the service/traversal layer; the **projection** creates none
because the locked relational schema has no authoritative source for them
(relationships are never inferred from text or AI). Adding one would require a
schema change, which Phase 7 does not do.

### Projection & consistency

```
1. write authoritative data to PostgreSQL
2. COMMIT PostgreSQL
3. best-effort project to Neo4j  (MERGE node, MERGE DERIVED_FROM edge)
```

Step 3 runs after `create_prompt` / `update_prompt_metadata` commit, and is
also done in bulk by `scripts/sync_neo4j.py`. Every write is an idempotent
`MERGE` — re-running creates no duplicate nodes or relationships.
`app/main.py`'s lifespan runs an idempotent `init_schema()` (unique constraint
on `Prompt.prompt_id`) — it never deletes data. **If Neo4j is unavailable, the
PostgreSQL write is not rolled back** (eventual consistency; reconcile later
with `sync_neo4j.py`). No distributed transaction, no two-phase commit.
Reconciliation (`sync_neo4j.py --prune`) removes graph nodes whose `prompt_id`
is no longer in PostgreSQL via scoped single-node `DETACH DELETE` — never
`MATCH (n) DETACH DELETE n`.

### Graph API + authorization

`GET /api/v1/graph/prompts/{prompt_id}/{ancestors|descendants|dependencies|related}`
(auth required). All Cypher is in `app/graph/service.py` — never in routes.
**Neo4j must not bypass PostgreSQL authorization:** every request (1) verifies
the caller may view the subject prompt in PostgreSQL (`404` otherwise), then
(2) filters every returned node through PostgreSQL visibility (owner or
`is_public`) — a private prompt the caller can't see is dropped even if the
graph connects to it. Public identifiers are always PostgreSQL `prompt_id`;
Neo4j internal ids / credentials / driver objects are never exposed. There is no
`GET /graph/all`. `NEO4J_ENABLED=false` → `503`.

### Frontend

`/prompts/[prompt_id]` gains a **"Prompt Relationships (Knowledge Graph)"**
section: an ancestry list + directly-connected prompts (relationship type,
direction, depth), each linking to the prompt. It states plainly that this is
distinct from semantic search. On `503`/error it shows "Graph relationships
unavailable" and never breaks the page.

Explicitly **out of scope** for Phase 7: any non-Prompt node, any other
relationship type, hybrid graph+vector ranking, AI-generated relationships /
GraphRAG, recommendations, Kafka/Redis/Celery/event bus, another database.
