# PromptDNA — Live Demonstration Guide

This guide walks through a short demo using the data created by
`backend/scripts/seed_demo.py`. Everything in the demo account was created
through the application's own API, so it follows the same validation, ownership,
versioning and lineage rules as real data.

## 0. Setup (local)

1. Start Docker Desktop, then `cd database && docker compose up -d`
   (PostgreSQL + pgvector, Neo4j).
2. `cd backend && ./.venv/Scripts/alembic.exe upgrade head`
3. Start the backend: `./.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000`
4. Seed (safe to repeat; it only creates what is missing):

   ```
   DEMO_PASSWORD='<the demo password>' ./.venv/Scripts/python.exe scripts/seed_demo.py --sync-graph
   ```

   If `DEMO_PASSWORD` is not set the script prompts for it. The password is
   never stored in source or docs. Use the same password every time: it is only
   used on first creation and to log in afterwards.
5. Start the frontend: `cd frontend && npm run dev`, open <http://localhost:3000/login>.

**Demo account:** `demo.promptdna@example.com` (name: *PromptDNA Demo User*).
`example.com` is a reserved documentation domain, so this is not a real address.
(`.local` addresses are rejected by the application's own email validation.)

## 1. What the demo data contains

| | |
|---|---|
| Prompts | 10, all private to the demo user |
| Versions | 20 (Summarizer 3, Code Reviewer 3, most others 2, three prompts 1) |
| Experiments | 10, all run on the real **PromptDNA Mock** provider, all scored manually |
| Embeddings | 20 (one per demo version), via the configured embedding provider |
| Lineage | Summarizer → Research Article Analyzer → Literature Review Assistant |
| Independent prompts | Python Code Reviewer, Python Debugging Assistant, SQL Query Generator, Database Design Assistant, Exam Preparation Study Planner, Technical Concept Explainer, Data Analysis Report Assistant |

Honesty notes (say these out loud if asked):

- Experiment **scores are manually assigned demonstration scores** (7, 8, 9 …),
  not automatic evaluations.
- Experiment **outputs come from the deterministic Mock provider** (it echoes the
  prompt). No real LLM was called; no OpenAI key is configured.
- Embeddings use the **mock embedding provider** (hashed bag-of-words). Similarity
  therefore reflects *shared wording*, not deep meaning. With
  `EMBEDDING_PROVIDER=openai` and a key, the same code path produces true
  semantic embeddings; re-run `backend/scripts/generate_embeddings.py`.
- Only `DERIVED_FROM` is demonstrable. `FORKED_FROM` and `DEPENDS_ON` have no
  authoritative PostgreSQL source in the current schema, so none exist.
- **Tags and collections** exist in the schema, but the application has no way to
  create or attach them (no API, no UI), so none were created for the demo.

## 2. Demo flow

### 1. Login — *Authentication*
Open `/login`, sign in as the demo account.
> **Professor explanation:** "JWT bearer authentication. Passwords are hashed with
> Argon2; the token carries only a subject and an expiry. Every API call is
> authorized against the token's user."

### 2. Prompt Library
Open **Prompts**. You see the 10 demo prompts.
> "The library is a paginated query over PostgreSQL, filtered to what the user
> is allowed to see: their own prompts plus public ones."

### 3. Open *Academic Research Paper Summarizer*
Open it from the library.

### 4–6. Versions 1, 2 and 3
Use the version history to show how the prompt evolved:
v1 is a one-line instruction, v2 adds a structure and limitations, v3 adds
research problem, practical implications and the "do not invent information"
guardrail. Each version has a change summary.

### 7. Immutable versions
Point out there is no edit or delete on a version; **Create New Version** only
appends.
> "Versions are append-only, so every experiment result stays tied to the exact
> text that produced it. `UNIQUE(prompt_id, version_number)` plus a bounded retry
> keeps numbering correct under concurrent writes."

### 8–9. Experiments and scores
In the experiment history show the four runs: v1 = 7, v2 = 8, v3 = 9, plus a
second v3 run = 8. Show the model
(*PromptDNA Mock*), status `SUCCESS`, response time and output.
> "An experiment records which immutable version ran on which model, the output,
> the latency and a score. The scores here are manual demonstration scores, and
> the model is the project's deterministic mock provider."

### 10. Lexical search
Back in the library, with **Search by text**, search: `research paper`.
Expected: **Academic Research Paper Summarizer**. Lexical search matches the
*title* (case-insensitive substring), so *Research Article Analyzer* and
*Literature Review Assistant* are not returned.
> "Lexical search matches characters. It is fast and exact but knows nothing
> about meaning."

### 11. Semantic search
Switch to **Semantic Search** and try:

- `How can I summarize a scholarly research article?` — expect the three
  academic prompts (*Literature Review Assistant*, *Academic Research Paper
  Summarizer*, *Research Article Analyzer*) to rank at the top.
- `Help me understand and summarize scholarly research` — expect the academic
  prompts near the top; with the mock embedder a generic prompt such as
  *Database Design Assistant* can also appear because it shares common words
  ("help", "me", "and").
- `Find prompts for reviewing Python programs` — expect **Python Code Reviewer**
  at the top by a clear margin.

Results show a similarity value (1 − cosine distance). Do not rely on exact
numbers or ordering — they depend on the embedding provider. Avoid short generic
queries (for example `Help me prepare for an exam`): with word-overlap
embeddings they match shared filler words rather than the exam prompt.
> "Each version's text is turned into a 1536-dimension vector stored in
> PostgreSQL by the pgvector extension. A query is embedded the same way and
> compared with cosine distance, using an HNSW index."

### 12. Open *Research Article Analyzer*
Open it from the library or the search results.

### 13. Show DERIVED_FROM
In **Prompt Relationships** show that it is *derived from* the Summarizer and that
*Literature Review Assistant* is derived from it.
> "The parent link is a foreign key on `prompts.parent_prompt_id` in
> PostgreSQL. That is the authoritative relationship."

### 14. Knowledge Graph
Show the ancestors/related lists on the Analyzer and Literature Review pages.
The chain is:

```
Academic Research Paper Summarizer
        ▲  DERIVED_FROM
Research Article Analyzer
        ▲  DERIVED_FROM
Literature Review Assistant
```

> "Neo4j holds a *projection* of those links as `(:Prompt)-[:DERIVED_FROM]->(:Prompt)`
> so variable-depth traversals (all ancestors, all descendants) are one
> query. Every traversal result is re-checked against PostgreSQL visibility."

(The Neo4j Browser at <http://localhost:7474> can show the same graph with
`MATCH p=(:Prompt)-[:DERIVED_FROM*]->(:Prompt) RETURN p`.)

### 15. PostgreSQL vs pgvector vs Neo4j

| Component | Role | One-line explanation |
|---|---|---|
| **PostgreSQL** | System of record | "Stores authoritative, normalized (3NF) structured data: users, prompts, versions, experiments, models." |
| **pgvector** | Extension *inside* PostgreSQL | "Finds semantically similar prompts using vector similarity — same database, no second data store." |
| **Neo4j** | Derived graph projection | "Traverses explicit prompt relationships and lineage; it can be rebuilt from PostgreSQL at any time." |

> "pgvector answers *'is it similar in meaning?'* — Neo4j answers *'how is it
> explicitly connected?'* — PostgreSQL is the source of truth for both."

## 3. Resetting / re-running

`seed_demo.py` never deletes anything. Re-running it reports `NEW THIS RUN` with
all zeros once the data exists. To rebuild the graph projection from PostgreSQL
at any time: `cd backend && PYTHONPATH=. ./.venv/Scripts/python.exe scripts/sync_neo4j.py`
(idempotent).
