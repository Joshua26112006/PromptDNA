"""Migration round-trip test (runs last — it rebuilds the schema).

Verifies completion criterion: the database is reproducible from empty via
Alembic, and `downgrade base` -> `upgrade head` works.
"""

from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from tests.conftest import BACKEND_DIR, TEST_URL
from tests.test_database import EXPECTED_TABLES


def _cfg() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_URL)
    return cfg


def test_downgrade_base_then_upgrade_head(pg_engine):
    cfg = _cfg()

    command.downgrade(cfg, "base")
    tables_after_down = set(inspect(pg_engine).get_table_names())
    assert EXPECTED_TABLES.isdisjoint(tables_after_down), (
        f"downgrade base left tables behind: "
        f"{EXPECTED_TABLES & tables_after_down}"
    )

    command.upgrade(cfg, "head")
    tables_after_up = set(inspect(pg_engine).get_table_names())
    assert EXPECTED_TABLES <= tables_after_up, (
        f"upgrade head missing tables: {EXPECTED_TABLES - tables_after_up}"
    )
