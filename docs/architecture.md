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
