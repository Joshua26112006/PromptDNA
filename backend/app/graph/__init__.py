"""Neo4j graph projection (Phase 7).

**PostgreSQL is the system of record. Neo4j is a derived projection** of prompt
relationships only. If the two ever disagree, PostgreSQL wins. Neo4j holds
``(:Prompt {prompt_id, title})`` nodes and only these relationships:
``DERIVED_FROM``, ``FORKED_FROM``, ``DEPENDS_ON``. No other node label or
relationship type is created.
"""
