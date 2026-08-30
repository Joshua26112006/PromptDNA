"""Deterministic development seed data for PromptDNA (Phase 1).

Run:  python -m app.db.seed          (uses DATABASE_URL)
      python -m app.db.seed --url postgresql+psycopg://...

Properties:
* **Deterministic** — every row has a fixed UUID derived with ``uuid5`` from a
  stable key, so ids never change between runs or machines.
* **Idempotent / safe to rerun** — rows are written with PostgreSQL
  ``INSERT ... ON CONFLICT DO UPDATE`` in strict foreign-key order, so a second
  run updates in place and never duplicates or errors.
* **No real personal data** — names/emails are obviously fictional and the
  password hashes are a constant placeholder (authentication is not implemented).

Demonstrates: 1:N (user→prompts, prompt→versions), self-referencing lineage
(``prompts.parent_prompt_id``), M:N (prompt↔tag, prompt↔collection), and
experiments spanning multiple versions and models (every ``status`` value, plus
a model that is RESTRICT-protected because experiments reference it).
"""

from __future__ import annotations

import argparse
import datetime as dt
import uuid

from sqlalchemy import Engine, Table
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.base import Base
from app.db.models import (  # noqa: F401  (import registers the tables)
    Collection,
    Experiment,
    Model,
    Prompt,
    PromptCollection,
    PromptTag,
    Tag,
    User,
    Version,
)
from app.db.session import build_engine

# Fixed namespace so uuid5-derived ids are stable forever.
NS = uuid.UUID("6f9619ff-8b86-d011-b42d-00cf4fc964ff")

# Obvious placeholder — NOT a usable credential. Auth is out of scope for Phase 1.
PLACEHOLDER_HASH = "$2b$12$seeddataplaceholderNOTAREALHASHxxxxxxxxxxxxxxxxxxxxxx"

_BASE_TS = dt.datetime(2026, 1, 5, 9, 0, 0, tzinfo=dt.timezone.utc)


def sid(kind: str, key: str) -> uuid.UUID:
    """Stable id for a seed row."""

    return uuid.uuid5(NS, f"promptdna:{kind}:{key}")


def _ts(hours: int) -> dt.datetime:
    return _BASE_TS + dt.timedelta(hours=hours)


# --------------------------------------------------------------------------- #
# Row data (plain dicts, keyed by the stable ids above)                      #
# --------------------------------------------------------------------------- #
def _users() -> list[dict]:
    people = [
        ("alice", "Alice Nguyen", "alice@promptdna.test"),
        ("bob", "Bob Ferreira", "bob@promptdna.test"),
        ("carol", "Carol Osei", "carol@promptdna.test"),
    ]
    return [
        {
            "user_id": sid("user", k),
            "name": name,
            "email": email,
            "password_hash": PLACEHOLDER_HASH,
        }
        for k, name, email in people
    ]


def _models() -> list[dict]:
    rows = [
        ("gpt-5", "GPT-5", "OpenAI"),
        ("claude", "Claude", "Anthropic"),
        ("gemini", "Gemini", "Google"),
    ]
    return [
        {"model_id": sid("model", k), "name": name, "provider": provider}
        for k, name, provider in rows
    ]


def _tags() -> list[dict]:
    names = ["Programming", "Research", "Education", "Writing"]
    return [{"tag_id": sid("tag", n.lower()), "name": n} for n in names]


def _prompts() -> list[dict]:
    # Order matters: a parent must appear before any child that references it.
    return [
        {
            "prompt_id": sid("prompt", "sql-opt"),
            "user_id": sid("user", "alice"),
            "title": "SQL Query Optimizer",
            "description": "Rewrites slow SQL queries and explains the changes.",
            "purpose": "Help developers improve query performance.",
            "parent_prompt_id": None,
            "is_public": True,
        },
        {
            "prompt_id": sid("prompt", "code-review"),
            "user_id": sid("user", "alice"),
            "title": "Code Review Bot",
            "description": "Reviews a diff and flags correctness and style issues.",
            "purpose": "Automate first-pass code review.",
            # Lineage: derived / forked from the SQL Query Optimizer prompt.
            "parent_prompt_id": sid("prompt", "sql-opt"),
            "is_public": False,
        },
        {
            "prompt_id": sid("prompt", "lit-review"),
            "user_id": sid("user", "bob"),
            "title": "Literature Review Assistant",
            "description": "Summarizes academic papers and extracts key findings.",
            "purpose": "Speed up literature reviews.",
            "parent_prompt_id": None,
            "is_public": True,
        },
        {
            "prompt_id": sid("prompt", "essay-outline"),
            "user_id": sid("user", "carol"),
            "title": "Essay Outline Generator",
            "description": "Turns a topic into a structured essay outline.",
            "purpose": "Teaching aid for academic writing.",
            "parent_prompt_id": None,
            "is_public": True,
        },
        {
            "prompt_id": sid("prompt", "unit-test"),
            "user_id": sid("user", "bob"),
            "title": "Unit Test Writer",
            "description": "Generates unit tests for a given function.",
            "purpose": "Improve test coverage quickly.",
            "parent_prompt_id": None,
            "is_public": False,
        },
    ]


def _collections() -> list[dict]:
    return [
        {
            "collection_id": sid("collection", "research"),
            "user_id": sid("user", "bob"),
            "name": "Research Prompts",
            "description": "Prompts used for academic research workflows.",
        },
        {
            "collection_id": sid("collection", "programming"),
            "user_id": sid("user", "alice"),
            "name": "Programming Prompts",
            "description": "Prompts that assist with software development.",
        },
    ]


def _versions() -> list[dict]:
    raw = [
        ("sql-opt", 1, "alice", 0,
         "You are a SQL expert. Optimize the following query.",
         "Initial version."),
        ("sql-opt", 2, "alice", 24,
         "You are a SQL expert. Optimize the query and list the indexes it "
         "would benefit from.", "Ask for index suggestions."),
        ("sql-opt", 3, "alice", 48,
         "You are a senior SQL performance engineer. Optimize the query, "
         "explain each change, and suggest supporting indexes.",
         "Stronger persona + require explanations."),
        ("lit-review", 1, "bob", 5,
         "Summarize this paper in five bullet points.", "Initial version."),
        ("lit-review", 2, "bob", 30,
         "Summarize this paper in five bullet points and list its stated "
         "limitations.", "Also extract limitations."),
        ("code-review", 1, "alice", 50,
         "Review this diff. Report bugs first, then style nits.",
         "Initial version."),
        ("essay-outline", 1, "carol", 8,
         "Create a five-section outline for an essay on the given topic.",
         "Initial version."),
        ("unit-test", 1, "bob", 12,
         "Write pytest unit tests for the following function.",
         "Initial version."),
    ]
    return [
        {
            "version_id": sid("version", f"{p}:{n}"),
            "prompt_id": sid("prompt", p),
            "version_number": n,
            "content": content,
            "change_summary": summary,
            "created_by": sid("user", author),
            "created_at": _ts(hours),
        }
        for p, n, author, hours, content, summary in raw
    ]


def _experiments() -> list[dict]:
    raw = [
        ("sqlopt-v3-gpt5", "sql-opt", 3, "gpt-5", 60, "SUCCESS",
         8.5, 1200, "Rewrote subquery as JOIN.", "Good baseline.", None),
        ("sqlopt-v3-claude", "sql-opt", 3, "claude", 61, "SUCCESS",
         9.0, 1500, "Rewrote subquery as JOIN; suggested composite index.",
         None, None),
        ("sqlopt-v2-gpt5", "sql-opt", 2, "gpt-5", 36, "SUCCESS",
         7.0, 1400, "Partial optimization.", None, None),
        ("litrev-v2-gemini", "lit-review", 2, "gemini", 40, "SUCCESS",
         8.0, 900, "Five bullets + three limitations.", None, None),
        ("litrev-v2-claude", "lit-review", 2, "claude", 41, "FAILED",
         None, None, None, "Retry later.", "Provider rate limit exceeded."),
        ("codereview-v1-gpt5", "code-review", 1, "gpt-5", 55, "PENDING",
         None, None, None, "Queued; not executed yet.", None),
        ("essay-v1-gemini", "essay-outline", 1, "gemini", 20, "SUCCESS",
         6.5, 750, "Five-section outline.", None, None),
        ("unittest-v1-claude", "unit-test", 1, "claude", 18, "SUCCESS",
         7.5, 1100, "Generated 4 tests incl. edge cases.", None, None),
    ]
    return [
        {
            "experiment_id": sid("experiment", key),
            "version_id": sid("version", f"{p}:{vnum}"),
            "model_id": sid("model", model),
            "executed_at": _ts(hours),
            "status": status,
            "score": score,
            "response_time_ms": rt,
            "output": output,
            "notes": notes,
            "error_message": err,
        }
        for key, p, vnum, model, hours, status, score, rt, output, notes, err in raw
    ]


def _prompt_tags() -> list[dict]:
    links = [
        ("sql-opt", "programming"),
        ("code-review", "programming"),
        ("code-review", "education"),
        ("lit-review", "research"),
        ("essay-outline", "education"),
        ("essay-outline", "writing"),
        ("unit-test", "programming"),
    ]
    return [
        {"prompt_id": sid("prompt", p), "tag_id": sid("tag", t)}
        for p, t in links
    ]


def _prompt_collections() -> list[dict]:
    links = [
        ("sql-opt", "programming"),
        ("code-review", "programming"),
        ("unit-test", "programming"),
        ("lit-review", "research"),
        ("essay-outline", "research"),
    ]
    return [
        {"prompt_id": sid("prompt", p), "collection_id": sid("collection", c)}
        for p, c in links
    ]


def _plan() -> list[tuple[Table, list[dict]]]:
    """Every (table, rows) pair in strict foreign-key order."""

    md = Base.metadata.tables
    return [
        (md["users"], _users()),
        (md["models"], _models()),
        (md["tags"], _tags()),
        (md["prompts"], _prompts()),
        (md["collections"], _collections()),
        (md["versions"], _versions()),
        (md["experiments"], _experiments()),
        (md["prompt_tags"], _prompt_tags()),
        (md["prompt_collections"], _prompt_collections()),
    ]


def _upsert(conn, table: Table, rows: list[dict]) -> int:
    if not rows:
        return 0
    pk_cols = [c.name for c in table.primary_key.columns]
    present = list(rows[0].keys())
    stmt = pg_insert(table).values(rows)
    update_cols = {c: stmt.excluded[c] for c in present if c not in pk_cols}
    if update_cols:
        stmt = stmt.on_conflict_do_update(
            index_elements=pk_cols, set_=update_cols
        )
    else:
        stmt = stmt.on_conflict_do_nothing(index_elements=pk_cols)
    conn.execute(stmt)
    return len(rows)


def seed(engine: Engine) -> dict[str, int]:
    """Upsert all seed rows in one transaction. Returns a per-table count."""

    counts: dict[str, int] = {}
    with engine.begin() as conn:
        for table, rows in _plan():
            counts[table.name] = _upsert(conn, table, rows)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Load PromptDNA seed data.")
    parser.add_argument("--url", default=None, help="SQLAlchemy database URL")
    args = parser.parse_args()

    engine = build_engine(args.url)
    counts = seed(engine)
    engine.dispose()

    total = sum(counts.values())
    print(f"Seed complete — {total} rows upserted:")
    for table, n in counts.items():
        print(f"  {table:<20} {n}")


if __name__ == "__main__":
    main()
