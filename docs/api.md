# PromptDNA API (Phase 3)

Database-backed HTTP API over the Phase 1 PostgreSQL schema, with JWT bearer
authentication and per-user authorization.

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

Responses: `201` → `PromptRead`; `401` (no/invalid token); `422` (validation).
Transaction: if the Version 1 insert fails, the prompt insert is rolled back.

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
Same visibility rule as the prompt itself (404 if the caller may not view the
parent). Read-only, ordered `version_number ASC`. **Versions are immutable** —
there is no create/update/delete endpoint for versions.

## Authorization rules (summary)

| Actor | Own prompt (private) | Own prompt (public) | Other's prompt (public) | Other's prompt (private) |
|-------|:---:|:---:|:---:|:---:|
| create | — | — | — | — (owner is always self) |
| `GET /{id}` | 200 | 200 | 200 | **404** |
| `GET /{id}/versions` | 200 | 200 | 200 | **404** |
| appears in `GET /prompts` | yes | yes | yes | **no** |

Unauthenticated: every `/api/v1/prompts*` route → `401`. Anonymous public access
is **not** provided.

## Error handling

Uniform body `{"detail": "<safe message>"}`.

| Code | When |
|------|------|
| 401 | not authenticated / bad / expired token (adds `WWW-Authenticate: Bearer`) |
| 403 | reserved for "resource exists and you may not" cases (not used for private prompts — those are 404 by design) |
| 404 | prompt not found **or** private prompt the caller may not see |
| 409 | email already registered |
| 422 | Pydantic / query / path validation |
| 500 | unexpected server error — body is exactly `{"detail":"Internal server error"}` |
| 503 | `/health/db` when PostgreSQL is unreachable |

Never returned to clients: SQL text, connection strings, credentials, the JWT
secret, password hashes, or stack traces. The app runs with `debug=False`.

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
- `tests/test_api_prompts.py` — Phase 2 prompt behavior, now with bearer auth.

## Known limitations

- No token revocation / logout endpoint (stateless JWT). A stolen token is valid
  until it expires.
- No refresh tokens; the client must re-login when the access token expires.
- No rate limiting / brute-force protection on `/auth/*`.
- No roles/permissions — every authenticated user has the same capabilities.
- Authorization covers prompts/versions only (the only user-owned resources
  exposed so far).
- `search` is `ILIKE` on `title` only — not full-text, not semantic.
- Token stored in `localStorage` by the dev frontend (XSS trade-off — see
  `docs/decisions.md`).

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
