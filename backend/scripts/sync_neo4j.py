"""Project PostgreSQL prompt relationships into the Neo4j graph.

    cd backend
    ./.venv/Scripts/python.exe scripts/sync_neo4j.py [--prune] [--dry-run]

Flow:  PostgreSQL (authoritative)  ->  read prompts + parent_prompt_id
       ->  Neo4j:  MERGE (:Prompt {prompt_id, title})
                   MERGE (child)-[:DERIVED_FROM]->(parent)   where parent_prompt_id is set

Idempotent — every write is a MERGE, so re-running creates no duplicate nodes
or relationships. `--prune` additionally removes Neo4j :Prompt nodes whose
prompt_id no longer exists in PostgreSQL (scoped single-node DETACH DELETE, not
a full-graph wipe).

Only DERIVED_FROM is projected: `prompts.parent_prompt_id` is the only
authoritative relationship field in the schema. FORKED_FROM / DEPENDS_ON are
part of the graph model but have no PostgreSQL source column, so the projection
creates none (documented limitation).

Requires NEO4J_ENABLED=true + NEO4J_URI/NEO4J_PASSWORD + DATABASE_URL. Fails
clearly if Neo4j is unavailable; PostgreSQL is never modified.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Prompt
from app.db.session import build_engine
from app.graph import service as graph
from app.graph.client import GraphUnavailable, close_driver, verify_connectivity


def main() -> int:
    parser = argparse.ArgumentParser(description="Project prompts to Neo4j.")
    parser.add_argument("--prune", action="store_true",
                        help="remove Neo4j :Prompt nodes not in PostgreSQL")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        verify_connectivity()
    except GraphUnavailable as exc:
        print(f"Neo4j unavailable: {exc}", file=sys.stderr)
        return 2

    graph.init_schema()

    engine = build_engine()
    nodes_created = rels_created = nodes_pruned = 0
    with Session(engine) as db:
        rows = db.execute(
            select(Prompt.prompt_id, Prompt.title, Prompt.parent_prompt_id)
        ).all()
        print(f"PostgreSQL: {len(rows)} prompt(s).")
        pg_ids = {str(r.prompt_id) for r in rows}

        for r in rows:
            if args.dry_run:
                print(f"  would MERGE node {r.prompt_id}"
                      + (f" -[:DERIVED_FROM]-> {r.parent_prompt_id}"
                         if r.parent_prompt_id else ""))
                continue
            nodes_created += graph.merge_prompt_node(str(r.prompt_id), r.title)
            if r.parent_prompt_id is not None:
                rels_created += graph.merge_relationship(
                    str(r.prompt_id), str(r.parent_prompt_id), "DERIVED_FROM"
                )

        if args.prune and not args.dry_run:
            for orphan in graph.all_prompt_ids() - pg_ids:
                nodes_pruned += graph.delete_prompt_node(orphan)

    engine.dispose()
    close_driver()

    if args.dry_run:
        print("dry run — no changes made.")
    else:
        print(f"done — nodes created: {nodes_created}, relationships created: "
              f"{rels_created}, nodes pruned: {nodes_pruned} "
              f"(existing nodes/relationships were left unchanged).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
