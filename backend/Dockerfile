# Production image for the PromptDNA FastAPI backend (Railway).
FROM python:3.13-slim

WORKDIR /app

# psycopg[binary], pwdlib[argon2] and the neo4j driver all ship prebuilt
# wheels for this base image — no extra system packages are needed.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Apply migrations, then serve on the platform-assigned $PORT (Railway injects
# PORT; defaults to 8000 for a plain `docker run`). Migrations are idempotent
# (alembic no-ops at head), so re-running them on every restart is safe.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
