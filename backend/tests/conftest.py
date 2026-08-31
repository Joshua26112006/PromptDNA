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
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

# A JWT secret must exist before `app.*` is imported (the app validates it at
# startup). Tests use a fixed, obviously-non-production value (>= 32 bytes).
os.environ.setdefault(
    "JWT_SECRET_KEY", "test-only-jwt-secret-not-for-production-use-0123456789"
)

import pytest
from sqlalchemy import Connection, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

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


# Phase 6: the `vector` extension is required for the embedding column and
# semantic search. Where it is unavailable, migrations stop before 0002 and the
# pgvector-dependent test modules skip with a reason (they never run against a
# different engine). Detected once, at import, against the test database.
def _detect_pgvector(url: str | None) -> bool:
    if not url:
        return False
    try:
        eng = create_engine(url, future=True)
        with eng.connect() as conn:
            row = conn.execute(
                text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
            ).first()
        eng.dispose()
        return row is not None
    except Exception:
        return False


PGVECTOR_AVAILABLE = _detect_pgvector(TEST_URL)

# Tell the app whether to map the versions.embedding columns. Must be set
# before any `app.*` import (conftest is imported first by pytest).
os.environ.setdefault("PGVECTOR_ENABLED", "true" if PGVECTOR_AVAILABLE else "false")


def _target_revision() -> str:
    """`head` when pgvector is available, else the last pre-vector revision."""

    return "head" if PGVECTOR_AVAILABLE else "0001_initial_schema"


def _apply_migrations(url: str) -> None:
    """Recreate an empty schema and run Alembic to the target revision.

    Exercises "migration runs successfully from an empty database".
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
    command.upgrade(cfg, _target_revision())


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


# --------------------------------------------------------------------------- #
# API-test fixtures                                                          #
# --------------------------------------------------------------------------- #
# `txn_connection`, `db_session`, and `client` all bind to ONE connection with
# ONE outer transaction that is rolled back at the end of each test. Sessions
# created on it use SAVEPOINTs, so a service that calls `commit()` is exercised
# for real, yet nothing is persisted to the test database.
@pytest.fixture
def txn_connection(pg_engine: Engine) -> Iterator[Connection]:
    connection = pg_engine.connect()
    trans = connection.begin()
    try:
        yield connection
    finally:
        trans.rollback()
        connection.close()


@pytest.fixture
def _session_factory(txn_connection: Connection) -> sessionmaker[Session]:
    return sessionmaker(
        bind=txn_connection,
        join_transaction_mode="create_savepoint",
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )


@pytest.fixture
def db_session(_session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """A session on the shared connection — for arranging test data."""

    session = _session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(_session_factory: sessionmaker[Session]):
    """A ``TestClient`` whose ``get_db`` dependency uses the shared connection."""

    from fastapi.testclient import TestClient

    from app.db.session import get_db
    from app.main import app

    def _override_get_db() -> Iterator[Session]:
        session = _session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    # raise_server_exceptions=False so 500 responses are returned, not re-raised.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


# --------------------------------------------------------------------------- #
# Authentication helpers for API tests                                        #
# --------------------------------------------------------------------------- #
DEFAULT_PASSWORD = "password123"


@dataclass
class AuthUser:
    user_id: str
    name: str
    email: str
    password: str
    token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


def register_and_login(client, *, name="Test User", email=None,
                       password=DEFAULT_PASSWORD) -> AuthUser:
    """Register a fresh user through the API and return them with a live token."""

    import uuid

    email = email or f"user-{uuid.uuid4().hex[:12]}@example.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert reg.status_code == 201, reg.text
    body = reg.json()
    tok = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert tok.status_code == 200, tok.text
    return AuthUser(
        user_id=body["user_id"],
        name=body["name"],
        email=body["email"],
        password=password,
        token=tok.json()["access_token"],
    )


@pytest.fixture
def user_a(client) -> AuthUser:
    return register_and_login(client, name="User A")


@pytest.fixture
def user_b(client) -> AuthUser:
    return register_and_login(client, name="User B")
