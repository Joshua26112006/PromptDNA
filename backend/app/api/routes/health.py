"""Liveness endpoint.

This is a plain liveness check that confirms the FastAPI process is running.
Readiness checks (PostgreSQL / Neo4j connectivity) are intentionally out of
scope for Phase 0 and will be added when those integrations exist.
"""

from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness check")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "message": "PromptDNA backend is running",
        "service": settings.app_name,
        "environment": settings.environment,
        "version": __version__,
    }
