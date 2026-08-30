"""Alembic migration environment.

Phase 0 note: there are NO models and NO migrations yet. This file only wires
Alembic to the application's ``DATABASE_URL`` so that Phase 1 can start adding
revisions without further plumbing. ``target_metadata`` stays ``None`` until the
SQLAlchemy models are introduced.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make the `app` package importable when Alembic runs from `backend/`.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Resolve the database URL from application settings unless one was passed
# explicitly on the command line (`-x db_url=...` or `sqlalchemy.url`).
_settings = get_settings()
if not config.get_main_option("sqlalchemy.url"):
    if _settings.database_url:
        config.set_main_option("sqlalchemy.url", _settings.database_url)

# No models yet — autogenerate is intentionally not wired up in Phase 0.
target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
