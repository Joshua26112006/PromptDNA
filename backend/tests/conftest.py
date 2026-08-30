"""Shared fixtures.

Database tests need a **real PostgreSQL** database (SQLite does not enforce the
CHECK / FK ON DELETE semantics this schema relies on). Point them at a
throwaway database with either environment variable:

    PROMPTDNA_TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/promptdna_test

If neither that nor DATABASE_URL is set (or the server is unreachable), the
database tests are **skipped with a reason** — never silently run against a
different engine.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _resolve_test_url() -> str | None:
    url = os.environ.get("PROMPTDNA_TEST_DATABASE_URL")
    if url:
        return url
    try:
        from app.core.config import get_settings

        return get_settings().database_url
    except Exception:  # pragma: no cover - defensive
        return None


TEST_URL = _resolve_test_url()


def _apply_migrations(url: str) -> None:
    """Recreate an empty schema and run Alembic to HEAD.

    This is what exercises completion criterion #3 ("migration runs
    successfully from an empty database").
    """

    from alembic import command
    from alembic.config import Config

    reset_engine = create_engine(url, future=True)
    with reset_engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    reset_engine.dispose()

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def pg_engine() -> Engine:
    if not TEST_URL:
        pytest.skip(
            "No PostgreSQL test database configured "
            "(set PROMPTDNA_TEST_DATABASE_URL or DATABASE_URL). "
            "Database tests require real PostgreSQL and were NOT run."
        )

    dbname = TEST_URL.rsplit("/", 1)[-1].split("?")[0]
    if "test" not in dbname and os.environ.get("PROMPTDNA_TEST_ALLOW_ANY_DB") != "1":
        pytest.skip(
            f"Refusing to run destructive schema tests against database "
            f"{dbname!r} (name lacks 'test'). Set PROMPTDNA_TEST_ALLOW_ANY_DB=1 "
            f"to override."
        )

    try:
        engine = create_engine(TEST_URL, future=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        pytest.skip(
            f"PostgreSQL not reachable at the configured URL — database tests "
            f"NOT run. ({exc.__class__.__name__})"
        )

    _apply_migrations(TEST_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def db(pg_engine: Engine) -> Session:
    """Function-scoped session wrapped in a transaction that is rolled back.

    Constraint violations abort to a savepoint (``join_transaction_mode=
    "create_savepoint"``) so the outer transaction stays usable for assertions.
    """

    connection = pg_engine.connect()
    trans = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()
