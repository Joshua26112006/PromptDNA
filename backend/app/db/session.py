"""Engine / session factory.

Phase 1 uses this only for the seed script and the database test suite; no
request-scoped session dependency is wired into FastAPI yet.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

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


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )


def session_scope(engine: Engine) -> Iterator[Session]:
    """Context-manager-style helper: commit on success, rollback on error."""

    factory = build_session_factory(engine)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
