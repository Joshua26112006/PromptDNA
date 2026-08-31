-- ===========================================================================
-- PromptDNA — demonstration queries (Phases 1 + 6, PostgreSQL / pgvector)
-- ---------------------------------------------------------------------------
-- Read-only examples that exercise the hybrid database. They are NOT wired to
-- any API. Sections:
--   1..10   relational schema (JOINs, recursive lineage CTE, aggregates)
--   (a..d)  query-plan / index inspection
--   11..13  pgvector cosine similarity + semantic-search ordering (Phase 6)
--   (e)     EXPLAIN a nearest-neighbour ordering
--   Cypher  reference queries for the Neo4j graph projection (Phase 7)
--
-- Setup:
--     cd backend
--     ./.venv/Scripts/python.exe -m app.db.seed                 # relational rows
--     ./.venv/Scripts/python.exe scripts/generate_embeddings.py # needs pgvector
--
-- then run:  psql "$DATABASE_URL" -f database/examples.sql
--
-- The pgvector queries (11..13, e) require migration 0002 (the versions.embedding
-- column). Without generated embeddings they simply return no rows.
-- ===========================================================================


-- 1. List prompts belonging to a user (by email) ---------------------------
SELECT p.prompt_id, p.title, p.is_public, p.created_at
FROM prompts p
JOIN users u ON u.user_id = p.user_id
WHERE u.email = 'alice@promptdna.test'
ORDER BY p.created_at;


-- 2. Get all versions of a prompt (by title), oldest first ----------------
SELECT v.version_number, v.change_summary, v.created_at, v.created_by
FROM versions v
JOIN prompts p ON p.prompt_id = v.prompt_id
WHERE p.title = 'SQL Query Optimizer'
ORDER BY v.version_number;


-- 3. Latest version of every prompt --------------------------------------
--    (DISTINCT ON is the idiomatic PostgreSQL "greatest-per-group".)
SELECT DISTINCT ON (v.prompt_id)
       p.title,
       v.version_number AS latest_version,
       v.created_at
FROM versions v
JOIN prompts p ON p.prompt_id = v.prompt_id
ORDER BY v.prompt_id, v.version_number DESC;


-- 4. All experiments for one version -----------------------------------
SELECT e.executed_at, m.name AS model, e.status, e.score, e.response_time_ms
FROM experiments e
JOIN models m ON m.model_id = e.model_id
JOIN versions v ON v.version_id = e.version_id
JOIN prompts p ON p.prompt_id = v.prompt_id
WHERE p.title = 'SQL Query Optimizer'
  AND v.version_number = 3
ORDER BY e.executed_at;


-- 5. Compare experiment scores across models -------------------------
SELECT m.name AS model,
       m.provider,
       count(*)              AS runs,
       round(avg(e.score), 2) AS avg_score,
       max(e.score)          AS best_score
FROM experiments e
JOIN models m ON m.model_id = e.model_id
WHERE e.status = 'SUCCESS' AND e.score IS NOT NULL
GROUP BY m.name, m.provider
ORDER BY avg_score DESC;


-- 6. Find prompts by tag ---------------------------------------------
SELECT t.name AS tag, p.title
FROM prompt_tags pt
JOIN tags t    ON t.tag_id = pt.tag_id
JOIN prompts p ON p.prompt_id = pt.prompt_id
WHERE t.name = 'Programming'
ORDER BY p.title;


-- 7. Find prompts in a collection ----------------------------------
SELECT c.name AS collection, p.title
FROM prompt_collections pc
JOIN collections c ON c.collection_id = pc.collection_id
JOIN prompts p     ON p.prompt_id = pc.prompt_id
WHERE c.name = 'Programming Prompts'
ORDER BY p.title;


-- 8. Traverse parent/child prompt lineage with a recursive CTE ------
WITH RECURSIVE lineage AS (
    SELECT prompt_id, parent_prompt_id, title, 0 AS depth
    FROM prompts
    WHERE parent_prompt_id IS NULL          -- roots

    UNION ALL

    SELECT child.prompt_id, child.parent_prompt_id, child.title, l.depth + 1
    FROM prompts child
    JOIN lineage l ON l.prompt_id = child.parent_prompt_id
)
SELECT repeat('  ', depth) || title AS tree, depth, prompt_id, parent_prompt_id
FROM lineage
ORDER BY depth, title;


-- 9. Wide multi-table JOIN: newest experiment per prompt, fully labelled --
SELECT u.name        AS owner,
       p.title       AS prompt,
       v.version_number,
       m.name        AS model,
       e.status,
       e.score,
       e.executed_at
FROM experiments e
JOIN versions v     ON v.version_id = e.version_id
JOIN prompts p      ON p.prompt_id = v.prompt_id
JOIN users u        ON u.user_id = p.user_id
JOIN models m       ON m.model_id = e.model_id
ORDER BY e.executed_at DESC;


-- 10. Aggregate analytics: per-prompt experiment summary -----------
SELECT p.title,
       count(e.experiment_id)                                   AS total_experiments,
       count(*) FILTER (WHERE e.status = 'SUCCESS')             AS successes,
       count(*) FILTER (WHERE e.status = 'FAILED')              AS failures,
       count(*) FILTER (WHERE e.status = 'PENDING')             AS pending,
       round(avg(e.score) FILTER (WHERE e.status = 'SUCCESS'), 2) AS avg_success_score,
       round(avg(e.response_time_ms) FILTER (WHERE e.response_time_ms IS NOT NULL)) AS avg_response_ms
FROM prompts p
JOIN versions v    ON v.prompt_id = p.prompt_id
JOIN experiments e ON e.version_id = v.version_id
GROUP BY p.title
ORDER BY total_experiments DESC, p.title;


-- ===========================================================================
-- Query plan / index inspection
-- ---------------------------------------------------------------------------
-- Use EXPLAIN (or EXPLAIN ANALYZE) to see whether an index is used.
--
-- NOTE: the seed dataset is tiny (5 prompts, 8 versions, 8 experiments).
-- At this size, whether the planner picks an index scan or a sequential scan
-- is NOT a meaningful performance signal -- both touch only a page or two and
-- the cost estimates are dominated by fixed overheads. (In practice the
-- planner does use, e.g., ix_experiments_model_id for the equality query in
-- (a) below, and the composite unique index for (c).) The statements here
-- demonstrate *how* to inspect planning. No performance numbers are claimed;
-- meaningful benchmarking requires bulk-loading many thousands of rows.
-- ===========================================================================

-- (a) Filter that an index (ix_experiments_model_id) can serve:
EXPLAIN
SELECT * FROM experiments WHERE model_id =
    (SELECT model_id FROM models WHERE name = 'GPT-5');

-- (b) Force the planner to consider indexes (session-local, for demonstration
--     only). With enable_seqscan off you can confirm the index is *usable*:
SET enable_seqscan = off;
EXPLAIN
SELECT * FROM experiments WHERE model_id =
    (SELECT model_id FROM models WHERE name = 'GPT-5');
RESET enable_seqscan;

-- (c) Confirm the composite UNIQUE index backs "versions of a prompt":
SET enable_seqscan = off;
EXPLAIN
SELECT * FROM versions WHERE prompt_id =
    (SELECT prompt_id FROM prompts WHERE title = 'SQL Query Optimizer');
RESET enable_seqscan;

-- (d) List every index PostgreSQL knows about for the core tables:
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;


-- ===========================================================================
-- pgvector — semantic search (Phase 6)
-- ---------------------------------------------------------------------------
-- pgvector runs INSIDE PostgreSQL. `<=>` is the cosine-distance operator;
-- cosine similarity = 1 - (a <=> b). The API embeds the user's query text and
-- runs query 12; here we use an existing embedding as the "query vector" so no
-- 1536-number literal is needed. Requires migration 0002 + generated embeddings.
-- ===========================================================================

-- 11. Cosine distance / similarity between versions of one prompt ---------
SELECT a.version_number                    AS from_version,
       b.version_number                    AS to_version,
       a.embedding <=> b.embedding         AS cosine_distance,
       1 - (a.embedding <=> b.embedding)   AS cosine_similarity
FROM versions a
JOIN versions b ON b.prompt_id = a.prompt_id AND b.version_id <> a.version_id
JOIN prompts p  ON p.prompt_id = a.prompt_id
WHERE p.title = 'SQL Query Optimizer'
  AND a.embedding IS NOT NULL
  AND b.embedding IS NOT NULL
ORDER BY from_version, to_version;


-- 12. Semantic-search ordering: nearest versions to a chosen query vector -
--     Mirrors app/repositories/version.py::semantic_search — closest by cosine
--     distance first, with the same visibility rule (owner OR public) the API
--     applies inside the SQL. Here the "query" is the oldest embedded version.
WITH query AS (
    SELECT embedding AS qvec
    FROM versions
    WHERE embedding IS NOT NULL
    ORDER BY created_at
    LIMIT 1
)
SELECT p.title,
       v.version_number,
       v.embedding_model,
       1 - (v.embedding <=> q.qvec) AS similarity
FROM versions v
JOIN prompts p ON p.prompt_id = v.prompt_id
CROSS JOIN query q
WHERE v.embedding IS NOT NULL
  AND p.is_public                       -- API also allows: OR p.user_id = :viewer
ORDER BY v.embedding <=> q.qvec         -- cosine distance ASC = most similar first
LIMIT 5;


-- 13. Confirm the HNSW index and its cosine operator class --------------
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname = 'ix_versions_embedding_hnsw';


-- (e) EXPLAIN a nearest-neighbour ordering. (See the NOTE above: at seed-data
--     size the planner may still choose a sequential scan — this shows *how* to
--     inspect it, not a performance result.)
EXPLAIN
WITH query AS (
    SELECT embedding AS qvec FROM versions WHERE embedding IS NOT NULL LIMIT 1
)
SELECT v.version_id
FROM versions v CROSS JOIN query q
WHERE v.embedding IS NOT NULL
ORDER BY v.embedding <=> q.qvec
LIMIT 5;


-- ===========================================================================
-- Neo4j graph projection (Phase 7) — CYPHER, not SQL
-- ---------------------------------------------------------------------------
-- Run these in the Neo4j Browser (http://localhost:7474) or cypher-shell, NOT
-- in psql. Neo4j is a derived, one-way projection of PostgreSQL. Populate it:
--     cd backend && ./.venv/Scripts/python.exe -m scripts.sync_neo4j
--
-- It contains ONLY (:Prompt {prompt_id, title}) nodes (prompt_id == the
-- PostgreSQL prompts.prompt_id) and the relationship types DERIVED_FROM /
-- FORKED_FROM / DEPENDS_ON. FORKED_FROM and DEPENDS_ON are modelled but never
-- populated: the relational schema has no authoritative source for them.
--
--   // The whole derivation forest (transitive DERIVED_FROM chains):
--   MATCH p = (:Prompt)-[:DERIVED_FROM*]->(:Prompt)
--   RETURN p;
--
--   // Ancestors of one prompt, with depth (the data the
--   // GET /api/v1/graph/prompts/{id}/ancestors endpoint returns, before it
--   // re-authorizes every node against PostgreSQL):
--   MATCH path = (start:Prompt {prompt_id: $prompt_id})
--                -[:DERIVED_FROM|FORKED_FROM*1..10]->(ancestor:Prompt)
--   RETURN ancestor.prompt_id, ancestor.title, length(path) AS depth
--   ORDER BY depth;
--
--   // Inventory — should be ONLY the Prompt label and (currently) DERIVED_FROM:
--   MATCH (n)          RETURN DISTINCT labels(n) AS labels, count(*) AS n;
--   MATCH ()-[r]->()   RETURN type(r) AS rel_type, count(*) AS n ORDER BY rel_type;
--
--   // The single schema object created by init_schema():
--   SHOW CONSTRAINTS;
-- ===========================================================================
