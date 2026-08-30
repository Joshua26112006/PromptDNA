# PromptDNA API (Phase 2)

Database-backed HTTP API over the Phase 1 PostgreSQL schema.

> **Authentication will be implemented in a later phase. `X-Dev-User-ID` is a
> development-only mechanism and must not be used as production
> authentication.**

- Base URL (local): `http://localhost:8000`
- Versioned API prefix: `/api/v1`
- Interactive docs: `/docs` (Swagger UI), `/redoc`; raw spec: `/openapi.json`
- Health endpoints live **outside** the versioned prefix.

## Architecture

```
HTTP request
  → FastAPI router      app/api/routes/*        (thin: parse, call service, return schema)
  → Pydantic schema     app/schemas/prompt.py   (shape validation only)
  → Service layer       app/services/prompt.py  (business rules + transaction boundary)
  → Repository          app/repositories/prompt.py (all SQLAlchemy access; never commits)
  → SQLAlchemy 2.x  →  PostgreSQL
  → Response schema     app/schemas/prompt.py
  → HTTP response
```

The database session is a FastAPI dependency (`app/db/session.py::get_db`) that
yields one `Session` per request and always closes it. A single engine +
`sessionmaker` is created once per process (never per request). `DATABASE_URL`
comes from configuration; it is never logged.

## Development user mechanism (`X-Dev-User-ID`)

`POST /api/v1/prompts` needs an owner, but there is no auth yet. The client
sends header `X-Dev-User-ID: <uuid>` naming an existing `users.user_id`.

| Situation | Response |
|-----------|----------|
| header missing | `400` — "Missing 'X-Dev-User-ID' header…" |
| header not a UUID | `400` — "'X-Dev-User-ID' must be a valid UUID." |
| UUID valid but no such user | `404` — "No user exists for X-Dev-User-ID …" |
| UUID valid and user exists | request proceeds |

This is **not** secure, is not a session, grants no permissions, and performs no
password check. It exists only so prompt ownership is real while auth is pending.
Get a valid id from the seed data: `SELECT user_id FROM users LIMIT 1;` (after
`python -m app.db.seed`).

## Endpoints

### `GET /health`
Liveness. `200 {"status":"ok","message":"PromptDNA backend is running", …}`.
Does not touch the database.

### `GET /health/db`
Readiness. Runs `SELECT 1`.
`200 {"status":"ok","database":"reachable"}` or `503 {"detail":"PostgreSQL is not reachable."}`.

### `POST /api/v1/prompts`
Create a prompt **and its Version 1** in one transaction.

Request body (`PromptCreate`, unknown fields rejected):

| field | type | rules |
|-------|------|-------|
| `title` | string | required, 1–200 chars (trimmed) |
| `content` | string | required, non-empty, ≤ 100 000 chars — stored as Version 1's `content` |
| `description` | string \| null | optional, ≤ 20 000 chars |
| `purpose` | string \| null | optional, ≤ 20 000 chars |
| `is_public` | bool | optional, default `false` |

Not accepted from clients: `prompt_id`, `user_id`, `parent_prompt_id`,
`created_at`, `updated_at`.

Header: `X-Dev-User-ID: <uuid>` (see above).

Responses: `201` → `PromptRead`; `400` (dev-user header); `404` (dev user not
found); `422` (body validation).

### `GET /api/v1/prompts`
Paginated list. Query params:

| param | type | default | rules |
|-------|------|---------|-------|
| `limit` | int | 20 | 1–100 |
| `offset` | int | 0 | ≥ 0 |
| `search` | string | – | case-insensitive **substring match on `title`** — lexical only, **not** semantic search |
| `is_public` | bool | – | optional filter |

Ordering: `created_at DESC, prompt_id`. Response (`PromptListResponse`):

```json
{ "items": [ /* PromptListItem */ ], "limit": 20, "offset": 0, "total": 42 }
```

### `GET /api/v1/prompts/{prompt_id}`
One prompt with owner (`user_id`, `name` only) and **all** versions
(`version_number` ascending), plus `latest_version` and `tags` (names).
`collections` are intentionally not included in this phase.
Responses: `200` → `PromptRead`; `404`; `422` (path not a UUID).

### `GET /api/v1/prompts/{prompt_id}/versions`
Read-only list of versions, ordered by `version_number ASC`.
Response: `{ "items": [ /* VersionRead */ ], "total": n }`.
Responses: `200`; `404` (prompt missing); `422` (bad UUID).

**Versions are immutable.** There is deliberately **no**
`POST/PUT/PATCH/DELETE` for versions in Phase 2.

## Response schemas (no sensitive fields)

- `PromptRead`: `prompt_id, user_id, title, description, purpose, is_public, parent_prompt_id, created_at, updated_at, owner{user_id,name}, versions[VersionRead], latest_version, tags[str]`
- `PromptListItem`: prompt columns + `latest_version_number`
- `VersionRead`: `version_id, prompt_id, version_number, content, change_summary, created_by, created_at`

`password_hash`, `email`, and other sensitive columns are never serialized.

## Error handling

Uniform body: `{"detail": "<safe message>"}`.

| Code | When |
|------|------|
| 400 | bad development-user header |
| 404 | prompt or development user not found |
| 409 | database integrity conflict (defensive; not expected in normal Phase 2 flows) |
| 422 | Pydantic / path / query validation |
| 500 | unexpected server error — body is exactly `{"detail":"Internal server error"}` |
| 503 | `/health/db` when PostgreSQL is unreachable |

Clients never receive SQL text, connection strings, credentials, or stack
traces. Diagnostics are logged server-side under the `promptdna` logger. The
FastAPI app runs with `debug=False` on purpose so tracebacks are never rendered
into responses.

## Transaction behavior

`POST /api/v1/prompts` (`services.prompt.create_prompt_with_initial_version`):

```
validate body (Pydantic)
check dev user exists            -> 404 if not
BEGIN
    INSERT prompts   (flush -> prompt_id)
    INSERT versions  (version_number = 1, content, created_by)
COMMIT
```

If the version insert raises, the service calls `Session.rollback()` and
re-raises → the prompt insert is undone. A prompt without Version 1 can never be
persisted. Covered by `tests/test_api_prompts.py::test_failed_initial_version_rolls_back_prompt`
(monkeypatches the version insert to fail, asserts `500` and that no prompt row
remains).

## Concurrency consideration (documented, not solved here)

Phase 2 does not expose version *creation*, so there is no version-number race
today. When a "create next version" workflow is added, two concurrent requests
could both compute `version_number = N+1`. Correctness is still guaranteed by
the Phase 1 constraint `UNIQUE (prompt_id, version_number)` — the second commit
fails with an integrity error. The recommended follow-up is for the service to
catch that specific unique-violation and retry with a recomputed number (a small
bounded loop), and/or to take a short row lock on the parent prompt
(`SELECT … FOR UPDATE`) while computing the next number. This is **not**
implemented yet and full concurrency control is **not** claimed.

## CORS

`CORSMiddleware` allows only the origins in `CORS_ORIGINS`
(default `http://localhost:3000`) with credentials enabled. `*` is rejected by
configuration validation. Production CORS is a later-phase concern.

## Testing approach

- Integration tests run against a **real PostgreSQL** database
  (`PROMPTDNA_TEST_DATABASE_URL`); SQLite is never substituted. Without a
  database URL the DB-backed tests **skip with a message**.
- Each test runs inside one connection-level transaction that is rolled back at
  teardown; service `commit()` calls execute against real PostgreSQL via
  SAVEPOINT, so nothing is written permanently and the dev database is never
  touched.
- `tests/test_api_prompts.py` covers health, DB health, create + atomic
  Version 1, unknown/missing/malformed dev user, body validation, list +
  pagination + search + filter, get one, 404s, invalid UUIDs, version listing +
  ordering + immutability, transaction rollback, OpenAPI/`/docs`, and a CORS
  preflight.

## Known limitations

- No authentication/authorization. `X-Dev-User-ID` is development-only.
- Anyone can read/list any prompt (no visibility enforcement beyond the optional
  `is_public` filter).
- No version-creation endpoint; no prompt update/delete endpoints.
- `search` is a plain `ILIKE` substring on `title` only — not full-text, not
  semantic.
- `collections` not exposed on the prompt detail endpoint yet.
- No rate limiting; no pagination cursor (offset/limit only).

## Run

```bash
cd backend
# DATABASE_URL must point at the Phase 1 schema (see .env.example)
./.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
# tests:
PROMPTDNA_TEST_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/promptdna_test \
  ./.venv/Scripts/python.exe -m pytest
```
