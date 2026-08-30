"""Database engine and session management.

One :class:`~sqlalchemy.Engine` (and one ``sessionmaker``) is created lazily on
first use and reused for the process lifetime — never per request. The
:func:`get_db` generator is the FastAPI dependency: it hands a session to the
request and always closes it afterward. Commit/rollback is the service layer's
responsibility, not this module's.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _require_database_url() -> str:
    url = get_settings().database_url
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not configured. Set it in the repo-root .env "
            "(see .env.example) before starting the API."
        )
    return url


def get_engine() -> Engine:
    """Return the process-wide engine, creating it once."""

    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            _require_database_url(),
            echo=settings.db_echo,
            pool_pre_ping=True,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            future=True,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the process-wide ``sessionmaker``, creating it once."""

    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            future=True,
        )
    return _session_factory


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yield a session and guarantee it is closed."""

    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def dispose_engine() -> None:
    """Dispose the engine/factory (used by tests and clean shutdown)."""

    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def build_engine(url: str | None = None) -> Engine:
    """Create a standalone (non-shared) engine.

    Used by scripts such as ``app.db.seed`` that may target an explicit URL and
    manage their own engine lifecycle. Does not touch the process-wide engine.
    """

    return create_engine(
        url or _require_database_url(),
        pool_pre_ping=True,
        future=True,
    )
