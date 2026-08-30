"""Engine helper.

Phase 1 uses this for the seed script and the database test suite; no
request-scoped session dependency is wired into FastAPI yet (Phase 2).
"""

from __future__ import annotations

from sqlalchemy import Engine, create_engine

from app.core.config import get_settings


def build_engine(url: str | None = None) -> Engine:
    """Create an :class:`Engine` from an explicit URL or ``DATABASE_URL``."""

    resolved = url or get_settings().database_url
    if not resolved:
        raise RuntimeError(
            "DATABASE_URL is not configured. Set it in the repo-root .env "
            "(see .env.example) before using the database."
        )
    return create_engine(resolved, future=True, pool_pre_ping=True)
