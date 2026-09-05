# Deployment — Vercel (frontend) + Render (backend) + Neon + Neo4j Aura

This matches the target already named in `README.md` ("Deployment (later): Vercel,
Neon, Neo4j Aura"), with **Render** added to run the FastAPI backend as a
persistent process (Vercel only runs serverless functions, which does not fit
this app's lifespan hook, cached Neo4j driver, and connection pools). Render's
free tier was chosen over Railway to keep the whole deployment at **$0** — the
tradeoff is that a free Render web service spins down after ~15 minutes idle
and takes 30–60s to wake up on the next request. (`backend/railway.toml` is
still in the repo — the exact same `backend/Dockerfile` deploys to Railway too
if you ever want an always-warm backend and are OK paying for it.)

No application code, schema, or architecture changes were made for this.
Everything below is configuration: three small deploy files
(`backend/Dockerfile`, `render.yaml`, `backend/railway.toml`) plus environment
variables set in each platform's dashboard.

```
Neon (PostgreSQL 16 + pgvector) ──┐
Neo4j Aura (Neo4j 5, free tier) ──┼──► Render (FastAPI, Docker, free) ──► Vercel (Next.js)
```

## 0. Order of operations

Do these in order — each later step needs a value produced by the one before:

1. Neon (get a PostgreSQL connection string)
2. Neo4j Aura (get a Bolt URI + password)
3. Render — deploy the backend with both of the above
4. Vercel — deploy the frontend pointed at the Render backend URL
5. Go back to Render and tighten `CORS_ORIGINS` to the real Vercel URL

## 1. Neon — PostgreSQL 16 + pgvector

1. Sign up at neon.tech, create a project. Only the **Postgres database**
   service is needed — leave Object storage / Functions / AI gateway / Neon
   Auth off.
2. On the project page, click **Connect**, turn **off "Connection pooling"**
   (this app manages its own connection pool, so use the direct connection,
   not Neon's PgBouncer proxy), then copy the connection string. It looks like:
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

1. Sign up at console.neo4j.io → **Data services → Instances → Create
   instance** → **AuraDB Free**.
2. Save the one-time credentials shown right after creation (or use "Reset
   password" on the instance card if you missed them):
   - **Connection URI** (on the instance's detail page), e.g.
     `neo4j+s://xxxxxxxx.databases.neo4j.io` → this is **`NEO4J_URI`**
     (the driver auto-detects the `neo4j+s://` scheme; no code change needed)
   - username `neo4j` → **`NEO4J_USERNAME`**
   - password → **`NEO4J_PASSWORD`**
   - database name is fixed to `neo4j` → **`NEO4J_DATABASE`**
3. Wait for the instance status to show **Running**.
4. Nothing else to do: the backend's startup hook calls `init_schema()`
   (creates the `prompt_id_unique` constraint) automatically, and it's
   idempotent.

## 3. Render — backend (FastAPI, free web service)

This repo includes `render.yaml` (a Render **Blueprint**), so Render can
create and pre-configure the service for you:

1. Sign up at render.com (GitHub login is easiest).
2. Dashboard → **New + → Blueprint** → connect/select
   `Joshua26112006/PromptDNA` → Render reads `render.yaml` and shows a
   `promptdna-backend` **Web Service** (free plan, Docker, root dir
   `backend`, health check `/health`) ready to create.
3. Render will prompt you to fill in the variables marked "sync: false" in
   the blueprint (these are never stored in the file/git) — enter:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | the Neon string from step 1 (`postgresql+psycopg://…`) |
   | `NEO4J_URI` | the Aura URI from step 2 |
   | `NEO4J_USERNAME` | `neo4j` |
   | `NEO4J_PASSWORD` | the Aura password from step 2 |
   | `CORS_ORIGINS` | *(temporary)* `https://placeholder.vercel.app` — you'll replace this in step 5 |
   | `JWT_SECRET_KEY` | a **new** strong secret — generate one yourself: `python -c "import secrets; print(secrets.token_urlsafe(64))"`. **Never reuse a value from any local `.env`.** |

   Everything else (`NEO4J_ENABLED`, `PGVECTOR_ENABLED`, `EMBEDDING_PROVIDER=mock`,
   etc.) is already set by the blueprint.

   *(No Blueprint / prefer manual setup: New + → Web Service → same repo →
   Root Directory `backend` → Runtime "Docker" → Instance Type **Free** →
   add all the variables listed in `render.yaml` by hand → Advanced → Health
   Check Path `/health`.)*
4. Click **Create Web Service** / **Apply**. Render builds the Docker image,
   runs `alembic upgrade head`, then starts `uvicorn`. Watch the logs for
   `Application startup complete.` and `Neo4j graph projection initialised`.
5. Render assigns a URL automatically, shown at the top of the service page:
   `https://promptdna-backend.onrender.com` (or similar) — **save it**, you
   need it for Vercel.
6. Sanity check (the **first** request after a fresh deploy is instant, but
   later ones after 15 min of idling take 30–60s to wake the service — that's
   expected on the free plan, not an error):
   ```bash
   curl https://<your-render-domain>/health
   curl https://<your-render-domain>/health/db
   ```
   Both should return `{"status":"ok", …}`.

## 4. Vercel — frontend (Next.js)

1. Sign up at vercel.com → **Add New → Project** → import
   `Joshua26112006/PromptDNA`.
2. In **Configure Project**:
   - **Root Directory**: `frontend`
   - Framework Preset: Next.js (auto-detected)
3. In **Environment Variables**, add:

   | Variable | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE_URL` | your Render backend URL from step 3.5, e.g. `https://promptdna-backend.onrender.com` |

   (`NEXT_PUBLIC_*` vars are baked in at build time — set this *before*
   clicking Deploy, or trigger a redeploy after adding it.)
4. Deploy. Vercel gives you a URL like `https://promptdna.vercel.app` (plus a
   unique preview URL per branch/PR).

## 5. Close the loop — tighten CORS

1. Back in Render → your backend service → **Environment** → set
   `CORS_ORIGINS` to your real Vercel URL(s), comma-separated, e.g.:
   `https://promptdna.vercel.app,https://promptdna-<your-team>.vercel.app`
   (Vercel preview deployments get random per-branch URLs; add one explicitly
   if you need a preview branch to also call the API. Wildcards and `*` are
   rejected on purpose — credentialed CORS must name exact origins.)
2. Save — Render redeploys automatically so the new `CORS_ORIGINS` takes
   effect (settings are cached per-process).

## 6. Verify the deployed system

From your machine:
```bash
curl https://<render-domain>/health
curl https://<render-domain>/health/db
```
From the browser, open the Vercel URL (give the backend ~60s first if it's
been idle):
- Register a new account, create a prompt + versions.
- Run an experiment against the **PromptDNA Mock** model — the seed data
  doesn't include a mock model row by default; either run `app/db/seed.py`
  once against the Neon database, or insert one row:
  `INSERT INTO models (name, provider) VALUES ('PromptDNA Mock', 'mock');`
  (This is reference data, not a schema or code change.)
- Semantic Search and the Knowledge Graph section should both work without
  a `503` — that confirms pgvector on Neon and Neo4j Aura are both reachable.

## Rollback / troubleshooting

- **CORS errors in the browser console**: `CORS_ORIGINS` on Render doesn't
  exactly match the Vercel URL shown in the address bar (scheme + host must
  match exactly, no trailing slash).
- **`/health/db` fails**: check the Neon connection string's scheme is
  `postgresql+psycopg://` (not `postgresql://`) and that `sslmode=require`
  is present.
- **Graph endpoints return 503**: check `NEO4J_ENABLED=true` and that the
  Aura instance isn't paused (Aura Free instances pause after inactivity and
  need a manual resume in the console).
- **First request is very slow / times out**: expected on Render's free
  plan after ~15 min idle — the container is cold-starting. Retry after
  30–60s. If it never comes back, check the Render deploy logs instead.
- **A bad deploy**: Render and Vercel both keep every previous deployment —
  use "Redeploy" / "Rollback" on the last good one from either dashboard; no
  `git revert` needed for a deployment-only rollback.
