"""Seed-data tests — verify the deterministic dev seed loads and is rerunnable.

These run against the real PostgreSQL test database and COMMIT (unlike the
transactional tests in test_database.py). They execute after test_database.py.
"""

from __future__ import annotations

import sqlalchemy as sa

from app.db.models import Experiment, Prompt
from app.db.seed import seed

EXPECTED_COUNTS = {
    "users": 3,
    "models": 3,
    "tags": 4,
    "prompts": 5,
    "versions": 8,
    "experiments": 8,
    "collections": 2,
    "prompt_tags": 7,
    "prompt_collections": 5,
}


def _table_count(engine, table: str) -> int:
    with engine.connect() as conn:
        return conn.scalar(sa.text(f"SELECT count(*) FROM {table}"))


def test_seed_loads_expected_counts(pg_engine):
    counts = seed(pg_engine)
    assert counts == EXPECTED_COUNTS
    for table, expected in EXPECTED_COUNTS.items():
        assert _table_count(pg_engine, table) == expected


def test_seed_is_idempotent(pg_engine):
    seed(pg_engine)
    first = {t: _table_count(pg_engine, t) for t in EXPECTED_COUNTS}
    seed(pg_engine)
    second = {t: _table_count(pg_engine, t) for t in EXPECTED_COUNTS}
    assert first == second == EXPECTED_COUNTS


def test_seed_demonstrates_prompt_lineage(pg_engine):
    seed(pg_engine)
    with pg_engine.connect() as conn:
        n = conn.scalar(
            sa.select(sa.func.count())
            .select_from(Prompt)
            .where(Prompt.parent_prompt_id.is_not(None))
        )
    assert n >= 1


def test_seed_covers_every_experiment_status(pg_engine):
    seed(pg_engine)
    with pg_engine.connect() as conn:
        statuses = set(
            conn.scalars(sa.select(Experiment.status).distinct()).all()
        )
    assert statuses == {"PENDING", "SUCCESS", "FAILED"}
