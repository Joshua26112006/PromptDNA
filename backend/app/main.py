"""FastAPI application entry point.

Phase 3: JWT authentication + per-user authorization on top of the Phase 2
layered architecture (router -> schema -> current-user -> authorization ->
service -> repository -> SQLAlchemy -> PostgreSQL). The Phase 2
``X-Dev-User-ID`` mechanism has been removed — see `docs/api.md`.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.errors import register_exception_handlers
from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("promptdna")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Fail clearly and early if authentication is misconfigured. Never fall
    # back to a hard-coded secret.
    if not settings.jwt_secret_key:
        raise RuntimeError(
            "JWT_SECRET_KEY is not set. The API cannot start without it "
            "(see .env.example). No insecure fallback secret is used."
        )
    logger.info("PromptDNA API starting (env=%s)", settings.environment)
    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    lifespan=lifespan,
    # debug is intentionally left False even in development: FastAPI/Starlette
    # debug mode returns raw tracebacks on 500s, which this API must never do.
    summary="Database-backed knowledge platform for prompt engineering (Phase 3).",
    description=(
        "JWT bearer authentication. Register at `POST /api/v1/auth/register`, "
        "log in at `POST /api/v1/auth/login`, then send "
        "`Authorization: Bearer <token>`. The Phase 2 `X-Dev-User-ID` header "
        "has been **removed** and is no longer accepted."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(health_router)  # /health, /health/db  (unversioned)
app.include_router(api_router)     # /api/v1/...


@app.get("/", tags=["meta"], summary="Service metadata")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "status": "ok",
        "environment": settings.environment,
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
        "api": settings.api_v1_prefix,
    }
