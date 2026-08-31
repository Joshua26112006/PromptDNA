"""Neo4j graph service — all Cypher lives here (never in routes).

Node model:        (:Prompt {prompt_id, title})   — prompt_id is the SAME value
                   as PostgreSQL prompts.prompt_id (the identity bridge).
Relationship model: (:Prompt)-[:DERIVED_FROM]->(:Prompt)
                    (:Prompt)-[:FORKED_FROM]->(:Prompt)
                    (:Prompt)-[:DEPENDS_ON]->(:Prompt)
                    direction: child/dependent -> parent/dependency.

Every write is a MERGE and is idempotent. No other label or relationship type
is ever created. Authorization is NOT done here — callers must have already
checked PostgreSQL visibility (see app/services/graph.py).
"""

from __future__ import annotations

import logging

from neo4j.exceptions import Neo4jError, ServiceUnavailable

from app.graph.client import GraphUnavailable, get_database, get_driver

logger = logging.getLogger("promptdna")

REL_TYPES = frozenset({"DERIVED_FROM", "FORKED_FROM", "DEPENDS_ON"})
LINEAGE_RELS = ("DERIVED_FROM", "FORKED_FROM")
_MAX_DEPTH = 10


def _clamp_depth(depth: int) -> int:
    return max(1, min(int(depth), _MAX_DEPTH))


def _run_write(cypher: str, **params):
    try:
        with get_driver().session(database=get_database()) as session:
            return session.execute_write(
                lambda tx: tx.run(cypher, **params).consume()
            )
    except (ServiceUnavailable, Neo4jError, OSError) as exc:
        logger.warning("Neo4j write failed: %s", type(exc).__name__)
        raise GraphUnavailable("The graph service is currently unavailable.") from None


def _run_read(cypher: str, **params) -> list[dict]:
    try:
        with get_driver().session(database=get_database()) as session:
            return session.execute_read(
                lambda tx: [r.data() for r in tx.run(cypher, **params)]
            )
    except (ServiceUnavailable, Neo4jError, OSError) as exc:
        logger.warning("Neo4j read failed: %s", type(exc).__name__)
        raise GraphUnavailable("The graph service is currently unavailable.") from None


# --------------------------------------------------------------------------- #
# Schema / upserts                                                           #
# --------------------------------------------------------------------------- #
def init_schema() -> None:
    """Idempotent: unique constraint on Prompt.prompt_id. Never deletes data."""

    _run_write(
        "CREATE CONSTRAINT prompt_id_unique IF NOT EXISTS "
        "FOR (p:Prompt) REQUIRE p.prompt_id IS UNIQUE"
    )


def merge_prompt_node(prompt_id: str, title: str) -> int:
    """MERGE a Prompt node by prompt_id, refresh its title. Returns nodes_created."""

    summary = _run_write(
        "MERGE (p:Prompt {prompt_id: $prompt_id}) SET p.title = $title",
        prompt_id=str(prompt_id),
        title=title,
    )
    return summary.counters.nodes_created


def merge_relationship(child_id: str, parent_id: str, rel_type: str) -> int:
    """MERGE (child)-[:REL_TYPE]->(parent). Both nodes are MERGEd first so the
    call is safe in any order. Returns relationships_created (0 if it existed).
    """

    if rel_type not in REL_TYPES:
        raise ValueError(f"Unsupported relationship type: {rel_type!r}")
    if str(child_id) == str(parent_id):
        raise ValueError("A prompt cannot relate to itself.")

    cypher = (
        "MERGE (child:Prompt {prompt_id: $child_id}) "
        "MERGE (parent:Prompt {prompt_id: $parent_id}) "
        f"MERGE (child)-[:{rel_type}]->(parent)"
    )
    summary = _run_write(
        cypher, child_id=str(child_id), parent_id=str(parent_id)
    )
    return summary.counters.relationships_created


def delete_prompt_node(prompt_id: str) -> int:
    """Scoped single-node delete (used by reconciliation). Returns nodes_deleted."""

    summary = _run_write(
        "MATCH (p:Prompt {prompt_id: $prompt_id}) DETACH DELETE p",
        prompt_id=str(prompt_id),
    )
    return summary.counters.nodes_deleted


def all_prompt_ids() -> set[str]:
    rows = _run_read("MATCH (p:Prompt) RETURN p.prompt_id AS prompt_id")
    return {r["prompt_id"] for r in rows}


# --------------------------------------------------------------------------- #
# Traversals                                                                 #
# --------------------------------------------------------------------------- #
def _lineage_pattern() -> str:
    return "|".join(LINEAGE_RELS)


def ancestors(prompt_id: str, max_depth: int = _MAX_DEPTH) -> list[dict]:
    """Prompts this prompt was DERIVED_FROM / FORKED_FROM, transitively."""

    d = _clamp_depth(max_depth)
    cypher = (
        f"MATCH path = (p:Prompt {{prompt_id: $prompt_id}})"
        f"-[r:{_lineage_pattern()}*1..{d}]->(a:Prompt) "
        "RETURN a.prompt_id AS prompt_id, a.title AS title, "
        "length(path) AS depth, "
        "[rel IN relationships(path) | type(rel)] AS rel_types "
        "ORDER BY depth"
    )
    return _run_read(cypher, prompt_id=str(prompt_id))


def descendants(prompt_id: str, max_depth: int = _MAX_DEPTH) -> list[dict]:
    """Prompts that were DERIVED_FROM / FORKED_FROM this prompt, transitively."""

    d = _clamp_depth(max_depth)
    cypher = (
        f"MATCH path = (c:Prompt)"
        f"-[r:{_lineage_pattern()}*1..{d}]->(p:Prompt {{prompt_id: $prompt_id}}) "
        "RETURN c.prompt_id AS prompt_id, c.title AS title, "
        "length(path) AS depth, "
        "[rel IN relationships(path) | type(rel)] AS rel_types "
        "ORDER BY depth"
    )
    return _run_read(cypher, prompt_id=str(prompt_id))


def dependencies(prompt_id: str, max_depth: int = _MAX_DEPTH) -> list[dict]:
    """Prompts this prompt DEPENDS_ON, transitively. Explicit dependency only —
    NOT semantic similarity (that is pgvector)."""

    d = _clamp_depth(max_depth)
    cypher = (
        f"MATCH path = (p:Prompt {{prompt_id: $prompt_id}})"
        f"-[:DEPENDS_ON*1..{d}]->(dep:Prompt) "
        "RETURN dep.prompt_id AS prompt_id, dep.title AS title, "
        "length(path) AS depth "
        "ORDER BY depth"
    )
    return _run_read(cypher, prompt_id=str(prompt_id))


def related(prompt_id: str) -> list[dict]:
    """One hop out on any approved relationship, in either direction."""

    cypher = (
        "MATCH (p:Prompt {prompt_id: $prompt_id})-[r]-(other:Prompt) "
        "WHERE type(r) IN $types "
        "RETURN other.prompt_id AS prompt_id, other.title AS title, "
        "type(r) AS type, "
        "CASE WHEN startNode(r) = p THEN 'outgoing' ELSE 'incoming' END AS direction, "
        "1 AS depth"
    )
    return _run_read(cypher, prompt_id=str(prompt_id), types=list(REL_TYPES))
