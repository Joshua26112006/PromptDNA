# Deployment — Vercel (frontend) + Railway (backend) + Neon + Neo4j Aura

This matches the target already named in `README.md` ("Deployment (later): Vercel,
Neon, Neo4j Aura"), with **Railway** added to run the FastAPI backend as a
persistent process (Vercel only runs serverless functions, which does not fit
this app's lifespan hook, cached Neo4j driver, and connection pools).

No application code, schema, or architecture changes were made for this.
Everything below is configuration: two small deploy files
(`backend/Dockerfile`, `backend/railway.toml`) plus environment variables set
in each platform's dashboard.

```
Neon (PostgreSQL 16 + pgvector) ──┐
Neo4j Aura (Neo4j 5, free tier) ──┼──► Railway (FastAPI, Docker) ──► Vercel (Next.js)
```

## 0. Order of operations

Do these in order — each later step needs a value produced by the one before:

1. Neon (get a PostgreSQL connection string)
2. Neo4j Aura (get a Bolt URI + password)
3. Railway — deploy the backend with both of the above
4. Vercel — deploy the frontend pointed at the Railway backend URL
5. Go back to Railway and tighten `CORS_ORIGINS` to the real Vercel URL

## 1. Neon — PostgreSQL 16 + pgvector

1. Sign up at neon.tech, create a project (region close to Railway's).
2. Neon gives a connection string like:
   `postgresql://USER:PASSWORD@ep-xxxx.REGION.aws.neon.tech/DBNAME?sslmode=require`
3. This app uses the `psycopg` (v3) SQLAlchemy driver, so change only the
   scheme:
   `postgresql+psycopg://USER:PASSWORD@ep-xxxx.REGION.aws.neon.tech/DBNAME?sslmode=require`
   → this full string is your **`DATABASE_URL`**.
4. Nothing else to do by hand: `CREATE EXTENSION vector` and all 9 tables are
   created automatically the first time the backend container starts (its
   `CMD` runs `alembic upgrade head` before `uvicorn`). Neon's default role
   has permission to create the `vector` extension.
5. Do **not** run `app/db/seed.py` against this database unless you want the
   fictional demo rows (Alice/Bob/Carol) in production — it's optional and
   idempotent, not required.

## 2. Neo4j Aura — Free tier

1. Sign up at console.neo4j.io → "New instance" → **AuraDB Free**.
2. Download/copy the generated credentials. You get:
   - a URI like `neo4j+s://xxxxxxxx.databases.neo4j.io` → this is **`NEO4J_URI`**
     (the driver auto-detects the `neo4j+s://` scheme; no code change needed)
   - username `neo4j` → **`NEO4J_USERNAME`**
   - a generated password → **`NEO4J_PASSWORD`** (shown once — save it)
   - database name is fixed to `neo4j` → **`NEO4J_DATABASE`**
3. Nothing else to do: the backend's startup hook calls `init_schema()`
   (creates the `prompt_id_unique` constraint) automatically, and it's
   idempotent.

## 3. Railway — backend (FastAPI)

1. Sign up at railway.app → **New Project → Deploy from GitHub repo** → pick
   `Joshua26112006/PromptDNA`.
2. In the new service's **Settings**:
   - **Root Directory**: `backend`
   - Railway will find `backend/Dockerfile` and `backend/railway.toml`
     automatically (build via Docker, health check on `/health`).
3. In **Variables**, set:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | the Neon string from step 1 (`postgresql+psycopg://…`) |
   | `JWT_SECRET_KEY` | a **new** strong secret — generate one yourself: `python -c "import secrets; print(secrets.token_urlsafe(64))"`. **Never reuse a value from any local `.env`.** |
   | `JWT_ALGORITHM` | `HS256` |
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` |
   | `ENVIRONMENT` | `production` |
   | `DEBUG` | `false` |
   | `LOG_LEVEL` | `INFO` |
   | `CORS_ORIGINS` | *(temporary)* `https://placeholder.vercel.app` — you'll replace this in step 5 |
   | `PGVECTOR_ENABLED` | `true` |
   | `EMBEDDING_PROVIDER` | `mock` (no key needed) — switch to `openai` + add `OPENAI_API_KEY` if you want real embeddings |
   | `EMBEDDING_DIMENSION` | `1536` |
   | `EMBEDDING_MODEL_NAME` | `text-embedding-3-small` |
   | `EMBEDDING_AUTOGENERATE` | `false` |
   | `NEO4J_ENABLED` | `true` |
   | `NEO4J_URI` | the Aura URI from step 2 |
   | `NEO4J_USERNAME` | `neo4j` |
   | `NEO4J_PASSWORD` | the Aura password from step 2 |
   | `NEO4J_DATABASE` | `neo4j` |
   | `ENABLE_MOCK_PROVIDER` | `true` |
   | `OPENAI_API_KEY` | leave blank unless you have one — experiments against GPT-5/Claude/Gemini seed rows stay `503 not configured`, which is correct behaviour, not a bug |

4. Deploy. Railway builds the image, runs `alembic upgrade head`, then starts
   `uvicorn`. Watch the deploy log for `Application startup complete.` and
   `Neo4j graph projection initialised`.
5. Railway assigns a public domain under **Settings → Networking → Generate
   Domain**, e.g. `promptdna-backend-production.up.railway.app`. Save it —
   this is your backend's public URL.
6. Sanity check: `curl https://<your-railway-domain>/health` and
   `/health/db` should both return `{"status":"ok", …}`.

## 4. Vercel — frontend (Next.js)

1. Sign up at vercel.com → **Add New → Project** → import
   `Joshua26112006/PromptDNA`.
2. In **Configure Project**:
   - **Root Directory**: `frontend`
   - Framework Preset: Next.js (auto-detected)
3. In **Environment Variables**, add:

   | Variable | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE_URL` | your Railway backend URL from step 3.5, e.g. `https://promptdna-backend-production.up.railway.app` |

   (`NEXT_PUBLIC_*` vars are baked in at build time — set this *before*
   clicking Deploy, or trigger a redeploy after adding it.)
4. Deploy. Vercel gives you a URL like `https://promptdna.vercel.app` (plus a
   unique preview URL per branch/PR).

## 5. Close the loop — tighten CORS

1. Back in Railway → your backend service → **Variables** → set
   `CORS_ORIGINS` to your real Vercel URL(s), comma-separated, e.g.:
   `https://promptdna.vercel.app,https://promptdna-<your-team>.vercel.app`
   (Vercel preview deployments get random per-branch URLs; add one explicitly
   if you need a preview branch to also call the API. Wildcards and `*` are
   rejected on purpose — credentialed CORS must name exact origins.)
2. Redeploy/restart the Railway service so the new `CORS_ORIGINS` takes
   effect (settings are cached per-process).

## 6. Verify the deployed system

From your machine:
```bash
curl https://<railway-domain>/health
curl https://<railway-domain>/health/db
```
From the browser, open the Vercel URL:
- Register a new account, create a prompt + versions.
- Run an experiment against the **PromptDNA Mock** model — wait, the seed
  data doesn't include a mock model row by default; either run
  `app/db/seed.py` once against the Neon database, or insert one row:
  `INSERT INTO models (name, provider) VALUES ('PromptDNA Mock', 'mock');`
  (This is reference data, not a schema or code change.)
- Semantic Search and the Knowledge Graph section should both work without
  a `503` — that confirms pgvector on Neon and Neo4j Aura are both reachable.

## Rollback / troubleshooting

- **CORS errors in the browser console**: `CORS_ORIGINS` on Railway doesn't
  exactly match the Vercel URL shown in the address bar (scheme + host must
  match exactly, no trailing slash).
- **`/health/db` fails**: check the Neon connection string's scheme is
  `postgresql+psycopg://` (not `postgresql://`) and that `sslmode=require`
  is present.
- **Graph endpoints return 503**: check `NEO4J_ENABLED=true` and that the
  Aura instance isn't paused (Aura Free instances pause after inactivity and
  need a manual resume in the console).
- **A bad deploy**: Railway and Vercel both keep every previous deployment —
  use "Redeploy" on the last good one from either dashboard; no `git revert`
  needed for a deployment-only rollback.
