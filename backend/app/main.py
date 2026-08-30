"""FastAPI application entry point.

Phase 2: database-backed API with a layered architecture
(router -> schema -> service -> repository -> SQLAlchemy -> PostgreSQL).
No authentication yet — see `app/api/deps.py` and `docs/api.md` for the
development-only `X-Dev-User-ID` mechanism.
"""

from __future__ import annotations

import logging

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

app = FastAPI(
    title=settings.app_name,
    version=__version__,
    # debug is intentionally left False even in development: FastAPI/Starlette
    # debug mode returns raw tracebacks on 500s, which this API must never do
    # (see docs/api.md → error handling). Our own handlers format every error.
    summary="Database-backed knowledge platform for prompt engineering (Phase 2).",
    description=(
        "Authentication will be implemented in a later phase. `X-Dev-User-ID` "
        "is a **development-only** mechanism and must not be used as production "
        "authentication."
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
