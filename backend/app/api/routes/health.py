"""Health endpoints.

``GET /health``     — liveness: the FastAPI process is up.
``GET /health/db``  — readiness: PostgreSQL is reachable (runs ``SELECT 1``).

Both live outside the versioned ``/api/v1`` namespace.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import __version__
from app.api.errors import ServiceUnavailableError
from app.core.config import get_settings
from app.db.session import get_db

logger = logging.getLogger("promptdna")

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


@router.get("/health/db", summary="Database readiness check")
def health_db(db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        # Do not surface the driver error to the client.
        logger.exception("Database readiness check failed")
        raise ServiceUnavailableError("PostgreSQL is not reachable.") from None
    return {"status": "ok", "database": "reachable"}
