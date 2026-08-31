# PromptDNA API (Phase 4A / 4B)

Database-backed HTTP API over the Phase 1 PostgreSQL schema, with JWT bearer
authentication, per-user authorization, and the core prompt + immutable-version
management endpoints. Phase 4B added the **Prompt Library frontend** (Next.js) —
no API changes; the frontend consumes the endpoints below through
`frontend/lib/api.ts`.

> **Semantic search is not implemented yet. The current search is lexical title
> search backed by PostgreSQL (`ILIKE`).** Vector / semantic search is a later
> phase (pgvector).

> **The Phase 2 `X-Dev-User-ID` header has been removed and is no longer
> accepted.** Authenticated endpoints require `Authorization: Bearer <token>`.
>
> **Logout limitation:** access tokens are stateless JWTs. There is no
> server-side revocation in this phase — "logout" means the client discards its
> token. A refresh-token / revocation system is future scope.

- Base URL (local): `http://localhost:8000`
- Versioned API prefix: `/api/v1`
- Interactive docs: `/docs` (Swagger UI, has an **Authorize** button), `/redoc`;
  raw spec: `/openapi.json`
- Health endpoints live **outside** the versioned prefix.

## Architecture

```
HTTP request
  → CORS (configured origins only)
  → FastAPI router        app/api/routes/{auth,prompts,health}.py   (thin)
  → get_current_user      app/api/deps.py     — validates Bearer JWT, loads the user
  → Pydantic schema       app/schemas/*.py    — shape validation only
  → Service layer         app/services/*.py   — authN (auth.py) / authZ (prompt.py) + transactions
  → Repository            app/repositories/*.py — all SQLAlchemy access; never commits
  → SQLAlchemy 2.x  →  PostgreSQL
  → Response schema  →  HTTP response
```

Authentication ("who is this?") lives in `services/auth.py` + `core/security.py`.
Authorization ("what may they touch?") lives in `services/prompt.py`. They are
separate. The database session is the per-request `get_db` dependency; a single
engine + `sessionmaker` is created once per process. Secrets (`DATABASE_URL`,
`JWT_SECRET_KEY`) come from configuration and are never logged or returned.

## Authentication flow

1. `POST /api/v1/auth/register` → creates the account (password Argon2-hashed).
2. `POST /api/v1/auth/login` → returns a JWT **access token**.
3. Client stores the token and sends `Authorization: Bearer <token>` on every
   subsequent request.
4. `get_current_user` validates the signature + expiry, reads `sub` (the
   `user_id`), loads the user, and injects it into the route.
5. `GET /api/v1/auth/me` echoes the authenticated profile (useful to verify).
6. Logout = client deletes its token (no server call).

### Password policy
8–128 characters. No composition rules (no forced symbols/digits/case). The goal
is to demonstrate secure hashing, not to build an identity provider.

### Token structure
Signed JWT, `HS256` by default (`JWT_ALGORITHM`). Claims — the minimum only:

| claim | meaning |
|-------|---------|
| `sub` | the user's `user_id` (UUID string) |
| `iat` | issued-at (unix seconds) |
| `exp` | expiry = `iat + ACCESS_TOKEN_EXPIRE_MINUTES*60` (default 30 min) |

The token carries **no** email, name, password hash, roles, or other data.
`JWT_SECRET_KEY` has no default — the API refuses to start without it (no
insecure fallback).

## Endpoints

### `GET /health`  ·  `GET /health/db`
Unversioned. Liveness (no DB) and readiness (`SELECT 1`; `503` if PostgreSQL is
unreachable). No auth.

### `POST /api/v1/auth/register`
Body (`application/json`, unknown fields rejected):

| field | type | rules |
|-------|------|-------|
| `name` | string | required, 1–100 chars (trimmed) |
| `email` | string | required, valid email; normalised to lower-case |
| `password` | string | required, 8–128 chars |

Responses: `201` → `{user_id, name, email, created_at}` (never `password` /
`password_hash`); `409` if the email is already registered; `422` on validation
failure.

### `POST /api/v1/auth/login`
OAuth2 "password" flow — body is `application/x-www-form-urlencoded` with:

| field | value |
|-------|-------|
| `username` | the account email |
| `password` | the account password |

Responses: `200` → `{access_token, token_type: "bearer", expires_in}`
(`expires_in` is seconds); `401` → `{"detail": "Invalid email or password."}`
for **any** failure (unknown email or wrong password — never distinguished).

### `GET /api/v1/auth/me`
Requires `Authorization: Bearer <token>`. Returns the same safe profile shape as
register. `401` if the token is missing / malformed / bad signature / expired /
for a user that no longer exists (with `WWW-Authenticate: Bearer`).

> **Prompt content is stored in Version entities. Existing versions are
> immutable; modifying prompt content creates a new version.** A `prompts` row
> holds only identity/metadata (`title`, `description`, `purpose`,
> `parent_prompt_id`, `is_public`) — never prompt text.

### `POST /api/v1/prompts`  *(auth required)*
Create a prompt **and its Version 1** in one transaction. The owner is **always**
the authenticated user — there is no way for a client to set it.

Body (`PromptCreate`, unknown fields rejected — including `user_id`):

| field | type | rules |
|-------|------|-------|
| `title` | string | required, 1–200 chars (trimmed) |
| `content` | string | required, non-empty, ≤ 100 000 — stored as Version 1's `content` |
| `description` | string \| null | optional, ≤ 20 000 |
| `purpose` | string \| null | optional, ≤ 20 000 |
| `is_public` | bool | optional, default `false` |
| `parent_prompt_id` | uuid \| null | optional — lineage; see below |

Responses: `201` → `PromptRead`; `401` (no/invalid token); `404` (bad/inaccessible
`parent_prompt_id`); `422` (validation). Transaction: if the Version 1 insert
fails, the prompt insert is rolled back.

**Lineage (`parent_prompt_id`).** If given, it must reference a prompt the
caller can VIEW (their own, or a public one). The new prompt is a
derivation/fork: it records `parent_prompt_id` but is **owned by the caller** —
ownership is never transferred, and the parent is not modified. A missing or
inaccessible parent returns `404` ("Parent prompt not found or not
accessible.") — the same response either way, so a private parent's existence is
not leaked. Self-parenting is structurally impossible (the client cannot know
the new prompt's id) and the service also guards against it. Recursive lineage
APIs (ancestors/descendants) are **not** part of this phase.

### `PATCH /api/v1/prompts/{prompt_id}`  *(auth required — owner only)*
Update **metadata only**. Body (`PromptUpdate`, all fields optional, unknown
fields rejected): `title` (1–200), `description`, `purpose`, `is_public`. Only
the fields present in the body are changed. It **cannot** change version
`content`, `version_number`, `created_by`, `created_at`, `user_id`, or
`parent_prompt_id` — those are `422` if sent.

Authorization: owner → `200` → `PromptRead`; public prompt owned by someone
else → `403`; private prompt owned by someone else, or missing → `404`;
unauthenticated → `401`. An empty body is a `200` no-op.

### `GET /api/v1/prompts`  *(auth required)*
Returns prompts **visible to the caller**: their own prompts **plus** public
prompts. Query params:

| param | type | default | rules |
|-------|------|---------|-------|
| `limit` | int | 20 | 1–100 |
| `offset` | int | 0 | ≥ 0 |
| `search` | string | – | case-insensitive substring on `title` — **lexical, not semantic** |
| `is_public` | bool | – | optional filter |

The visibility predicate (`owner OR public`) is applied by the repository and
**ANDed** with any query filter, so `?is_public=false` returns only the caller's
own private prompts — never anyone else's. Response: `PromptListResponse`
`{items, limit, offset, total}`.

### `GET /api/v1/prompts/{prompt_id}`  *(auth required)*
Authorization:

```
if caller owns the prompt        → 200
elif prompt.is_public            → 200
else                             → 404   (same body as a genuinely missing id)
```

**404 (not 403) for an inaccessible private prompt** so a caller cannot use the
endpoint as an existence oracle for other users' private prompts. Response:
`PromptRead` (owner = `{user_id, name}` only; never `email` / `password_hash`).

### `GET /api/v1/prompts/{prompt_id}/versions`  *(auth required)*
Version history. Same visibility rule as the prompt itself (`404` if the caller
may not view the parent). Read-only, ordered `version_number ASC`. Each item:
`{version_id, prompt_id, version_number, content, change_summary, created_by,
created_at}`. Response: `VersionListResponse` `{items, total}`.

### `GET /api/v1/prompts/{prompt_id}/versions/{version_id}`  *(auth required)*
Return one version. It must both **belong to `prompt_id`** and be under a prompt
the caller can view. Any mismatch — wrong prompt, unknown version, inaccessible
private prompt — returns `404` ("Version not found."), so a version cannot be
reached through a different prompt's URL and inaccessible versions are not
revealed.

### `POST /api/v1/prompts/{prompt_id}/versions`  *(auth required — owner only)*
Append a new immutable version. Body (`VersionCreate`, unknown fields rejected —
including `version_number` / `created_by`):

| field | type | rules |
|-------|------|-------|
| `content` | string | required, non-empty, ≤ 100 000 |
| `change_summary` | string \| null | optional, ≤ 20 000 |

Behavior:
1. Only the **prompt owner** may add a version. A public prompt does **not**
   grant other users this right → `403`. A private prompt owned by someone
   else, or a missing prompt → `404`.
2. `version_number` = `MAX(version_number) + 1` for that prompt, read fresh from
   the database (never from application memory).
3. `created_by` = the authenticated user (the client cannot choose it).
4. A **new** `versions` row is inserted in its own transaction. Existing
   versions are never read-modified-written.

Responses: `201` → `VersionRead`; `403` / `404` as above; `401`; `422`
(validation); `409` — see concurrency below.

**Concurrency / version numbering.** Two requests can both read the same
`MAX(version_number)` and try to insert `N+1`. The Phase 1 constraint
`UNIQUE (prompt_id, version_number)` guarantees only one wins; the loser's
insert raises an integrity error, which the service catches and **retries**
(recomputing the number) up to 5 times. If it still cannot place a number, the
API returns `409` ("Could not allocate a version number due to concurrent
writes. Please retry.") rather than a `500` or a silent overwrite. This is a
best-effort strategy — the API does not claim unlimited lock-free concurrent
version creation; a serialized "next version" allocation (row lock / advisory
lock) is possible future hardening.

**Immutability (project rule).** There is **no** `PUT`, `PATCH`, or `DELETE` for
a version, at either `/versions` or `/versions/{id}` (any such method → `405`).
`content`, `version_number`, `created_by`, and `created_at` of an existing
version cannot be changed through the API. Version history is preserved
indefinitely.

## Experiments & models (Phase 5)  *(auth required)*

> **An experiment records the execution of a specific immutable prompt version
> against a specific model, preserving the result and execution metadata for
> later comparison.** It runs `version.content` verbatim — never a prompt
> reconstructed from title/description — so it is reproducible.

### `GET /api/v1/models`
Every `models` row + `execution_configured` (a registered provider for its
`provider` has credentials on this server). **Never** returns API keys.

### `POST /api/v1/prompts/{prompt_id}/versions/{version_id}/experiments`  *(owner only)*
Body (`ExperimentRunRequest`, unknown fields rejected — incl. `output`,
`status`, `response_time_ms`, `executed_at`, `version_id`, `prompt_id`):

| field | type | rules |
|-------|------|-------|
| `model_id` | uuid | required — must exist |
| `notes` | string \| null | optional, ≤ 20 000 |

Authorization: only the **prompt owner** may execute. A public prompt owned by
someone else → `403`; a private prompt owned by someone else, or missing →
`404`. Version must belong to the prompt (`404` otherwise).

Flow: validate → create a `PENDING` experiment and **commit** → call the
provider (timed with `perf_counter`, capped by `EXPERIMENT_PROVIDER_TIMEOUT_S`,
default 30 s; **no DB transaction is held during the call**) → **commit** the
result:

- success → `status = "SUCCESS"`, `output` stored, `response_time_ms` (int),
  `executed_at`.
- provider failure / timeout / malformed response → `status = "FAILED"`,
  a **safe** `error_message` (no keys, no raw payloads), `response_time_ms`,
  `executed_at`. **Never** faked as success.

Responses: `201` → `ExperimentRead` (SUCCESS or FAILED); `403` / `404`;
`503` if the model has **no registered/configured execution provider** (no
experiment row is created); `422` (validation); `401`.

`ExperimentRead`: `experiment_id, version_id, prompt_id, model_id, model_name,
provider, version_number, executed_at, response_time_ms, score, output, notes,
status, error_message`.

### `GET /api/v1/prompts/{prompt_id}/experiments`  ·  `.../versions/{version_id}/experiments`
Experiments for a prompt's versions / one version, newest first. Visibility =
the parent prompt's (owner or `is_public`; else `404`). `ExperimentListResponse`
`{items, total}`.

### `GET /api/v1/experiments/{experiment_id}`
One experiment, authorized **through its owning prompt** — an experiment id
cannot bypass prompt visibility (`404` if the caller may not view the prompt).

### `PATCH /api/v1/experiments/{experiment_id}`  *(owner only)*
Body (`ExperimentScoreRequest`): `score` (number, **0–10**, also a DB `CHECK`) and/or
`notes`. Partial (`model_fields_set`). This is a **human** rating — there is no
automatic AI scoring. Non-owner → `403` (public) / `404` (private). Never touches
the version or the execution result. Semantic-similarity scores (a later phase)
are a different concept.

## Search — two modes

### Lexical (`GET /api/v1/prompts?search=`)
Case-insensitive `ILIKE` substring match on `prompts.title` (wildcards escaped),
applied *after* the visibility predicate. Never called "AI search".

### Semantic (`GET /api/v1/search/semantic`, Phase 6)  *(auth required)*

Finds prompts with similar **meaning** even when the wording differs, by
comparing embedding vectors in pgvector.

| param | type | rules |
|-------|------|-------|
| `query` | string | required, 1–2000 chars |
| `limit` | int | default 10, 1–50 |
| `is_public` | bool | optional filter |
| `owner` | bool | restrict to the caller's own prompts |

Flow: authenticate → validate (empty → `422`/`400`) → embed the query with the
active `EmbeddingProvider` → nearest `versions` by **cosine distance**
(`embedding <=> :qvec`, HNSW index) → **the visibility predicate is part of the
SQL query** (`prompts.user_id = :viewer OR prompts.is_public`), so other users'
private prompts are never scored → return results with a `similarity`
(`1 - cosine_distance`; higher = closer). **Raw vectors are never returned.**

`SemanticSearchResponse`: `{query, count, results: [{prompt_id, version_id,
prompt_title, version_number, content_preview, similarity, is_public,
created_at}]}`. `similarity` is a **semantic-similarity** score (meaning
closeness) — not an experiment `score` (model-run quality).

Responses: `200`; `422`/`400` (bad/empty query); `401`; `503` if the embedding
provider is unconfigured, temporarily failing, or pgvector is not available on
this deployment.

### `POST /api/v1/versions/{version_id}/embedding`  *(owner only)*
(Re)generate the embedding for one version. Only the prompt owner may trigger it
(it can cost money). Never modifies `versions.content`; a provider failure
leaves the version intact and can be retried. `503` if the provider is
unconfigured / pgvector absent. → `VersionEmbeddingStatus {version_id,
has_embedding, embedding_model, dimension}`.

### `GET /api/v1/versions/{version_id}/embedding`
Embedding status for a version (visibility = the parent prompt's).

### Batch backfill
`backend/scripts/generate_embeddings.py [--limit N] [--dry-run]` — finds versions
without an embedding, generates + stores them, reports successes/failures. A
dev/admin tool, not an HTTP endpoint (avoids unbounded API cost).

## Authorization rules (summary)

| Action | Own prompt (private) | Own prompt (public) | Other's prompt (public) | Other's prompt (private) |
|--------|:---:|:---:|:---:|:---:|
| `GET /{id}` | 200 | 200 | 200 | **404** |
| `GET /{id}/versions` | 200 | 200 | 200 | **404** |
| `GET /{id}/versions/{vid}` | 200 | 200 | 200 | **404** |
| appears in `GET /prompts` list | yes | yes | yes | **no** |
| `POST /{id}/versions` (add version) | 201 | 201 | **403** | **404** |
| `PATCH /{id}` (metadata) | 200 | 200 | **403** | **404** |

`POST /prompts`: any authenticated user; owner is always the caller.
Unauthenticated: every `/api/v1/prompts*` route → `401`. Anonymous public access
is **not** provided. `403` is used only where the resource's existence is
already public (a public prompt) but the caller lacks write permission; private
resources always answer `404`.

## Error handling

Uniform body `{"detail": "<safe message>"}`.

| Code | When |
|------|------|
| 401 | not authenticated / bad / expired token (adds `WWW-Authenticate: Bearer`) |
| 403 | the resource's existence is already public (a public prompt) but the caller lacks write permission — `POST /{id}/versions`, `PATCH /prompts/{id}`, `POST .../experiments`, `PATCH /experiments/{id}` by a non-owner. **Never** for private resources (those are `404`). |
| 404 | prompt/version/experiment/model not found, **or** a private resource the caller may not see, **or** a version/experiment requested under the wrong prompt id, **or** a bad/inaccessible `parent_prompt_id` |
| 409 | email already registered; or a version-number could not be allocated after retries under concurrent writes |
| 422 | Pydantic / query / path validation (incl. rejected unknown body fields; `score` outside 0–10) |
| 500 | unexpected server error — body is exactly `{"detail":"Internal server error"}` |
| 503 | `/health/db` when PostgreSQL is unreachable; **or** an experiment run against a model whose provider is unregistered / has no credentials on this server (no experiment row is created) |

Never returned to clients: SQL text, connection strings, credentials, the JWT
secret, password hashes, **AI provider API keys**, raw provider error payloads,
or stack traces. The app runs with `debug=False`. A failed provider call is
recorded as a `FAILED` experiment (with a safe message), not surfaced as a 5xx.

## CORS

`CORSMiddleware` allows only the origins in `CORS_ORIGINS`
(default `http://localhost:3000`), `allow_credentials=True`,
`allow_methods=["*"]`, `allow_headers=["*"]` (covers `Authorization`). `*` is
rejected by configuration validation. Production CORS is a later-phase concern.

## Rate limiting

Not implemented in this phase. Login and registration are unthrottled.
Documented as future security hardening (rate limiting on `/auth/*`, lockouts,
etc.).

## Testing approach

- All DB-backed tests run against **real PostgreSQL**
  (`PROMPTDNA_TEST_DATABASE_URL`); SQLite is never substituted. Without a
  database URL they **skip with a message**.
- Each test runs in one connection-level transaction rolled back at teardown;
  service `commit()` calls run via SAVEPOINT, so nothing persists and the dev
  database is untouched.
- `tests/test_auth.py` — registration, Argon2 hashing (asserts the stored value
  is a hash, not the password), duplicate email (409), validation (422),
  login success/failure, JWT claims + TTL, `/auth/me`, missing/malformed/
  wrong-secret/expired/deleted-user tokens (401).
- `tests/test_authz.py` — ownership on create, own vs. other users' public vs.
  private prompts, version access, the query-parameter-bypass attempt, the
  explicit "User B probes User A's private prompt by UUID → 404" scenario,
  `X-Dev-User-ID` no longer accepted, all prompt routes require a token,
  transaction still atomic under auth.
- `tests/test_api_prompts.py` — prompt list/get/validation + `PATCH` metadata,
  with bearer auth.
- `tests/test_versions.py` — append version (owner-only), numbering, immutability
  (no PUT/PATCH/DELETE; existing rows untouched), history ordering, single-version
  retrieval + cross-prompt 404, version-number-conflict → `409`.
- `tests/test_lineage.py` — `parent_prompt_id` on create: valid parent, missing
  parent → 404, malformed → 422, private parent of another user → 404,
  self-parent guard, child owned by creator not parent's owner, public parent
  forkable.

## Known limitations

- No token revocation / logout endpoint (stateless JWT). A stolen token is valid
  until it expires.
- No refresh tokens; the client must re-login when the access token expires.
- No rate limiting / brute-force protection on `/auth/*`.
- No roles/permissions — every authenticated user has the same capabilities.
- Authorization covers prompts/versions only (the only user-owned resources
  exposed so far).
- `search` is `ILIKE` on `title` only — not full-text, not semantic.
- **Version-number allocation is best-effort** (compute-then-insert with a
  bounded retry, `409` on give-up). Under heavy concurrent version creation on
  one prompt a caller may get a `409` and must retry. No serialized allocation
  (row/advisory lock) yet.
- Lineage is a single `parent_prompt_id` link only. No ancestor/descendant
  traversal endpoints, no cycle detection beyond the (structurally impossible)
  self-parent case, no graph store (Neo4j is a later phase).
- `PATCH /prompts/{id}` cannot change `parent_prompt_id` (lineage is set once,
  at creation).
- No prompt `DELETE` endpoint (deferred to a later lifecycle-management phase).
- Token stored in `localStorage` by the dev frontend (XSS trade-off — see
  `docs/decisions.md`).

## Frontend (Phase 4B)

The Next.js app is a thin client over these endpoints. It never re-implements
authorization — hidden write controls are UX only; the API returns `401`/`403`/
`404` regardless.

| Page | Endpoints used |
|------|----------------|
| `/login`, `/register` | `POST /auth/login`, `POST /auth/register`, `GET /auth/me` |
| `/prompts` (Prompt Library) | `GET /api/v1/prompts` with `search` (lexical), `is_public`, `limit`, `offset`; pagination from `total` |
| `/prompts/new` | `POST /api/v1/prompts` (title, content, description, purpose, is_public — no ownership fields) |
| `/prompts/[id]` (Prompt Detail) | `GET /api/v1/prompts/{id}`, `GET /api/v1/prompts/{id}/versions`; owner-only `PATCH /api/v1/prompts/{id}` and `POST /api/v1/prompts/{id}/versions` ({content, change_summary}); parent link via `GET /api/v1/prompts/{parent_id}` |

Token: stored in `localStorage`, sent as `Authorization: Bearer`. Base URL from
`NEXT_PUBLIC_API_BASE_URL`. Logout is client-side only.

## Run

```bash
cd backend
# DATABASE_URL -> Phase 1 schema; JWT_SECRET_KEY -> a strong random value
export JWT_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(64))')"
./.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000

# quick check
curl -X POST localhost:8000/api/v1/auth/register -H 'content-type: application/json' \
     -d '{"name":"Ada","email":"ada@example.com","password":"password123"}'
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login \
     -d 'username=ada@example.com&password=password123' | jq -r .access_token)
curl localhost:8000/api/v1/auth/me -H "Authorization: Bearer $TOKEN"
curl -X POST localhost:8000/api/v1/prompts -H "Authorization: Bearer $TOKEN" \
     -H 'content-type: application/json' \
     -d '{"title":"Demo","content":"You are helpful.","is_public":true}'

# tests
PROMPTDNA_TEST_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/promptdna_test \
  ./.venv/Scripts/python.exe -m pytest
```
