"""FastAPI application entry point.

Phase 0 scope: application shell + configuration + a `/health` endpoint.
No authentication, no CRUD, no business logic.
"""

from __future__ import annotations

from fastapi import FastAPI

from app import __version__
from app.api.routes.health import router as health_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=__version__,
    debug=settings.debug,
    summary="Intelligent knowledge database for prompt engineering (Phase 0 foundation).",
)

app.include_router(health_router)


@app.get("/", tags=["meta"], summary="Service metadata")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "status": "ok",
        "environment": settings.environment,
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }
