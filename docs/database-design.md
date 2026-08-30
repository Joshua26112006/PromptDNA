# PromptDNA — Database Design

PostgreSQL is the **system of record**. This document has two parts:

- **Part A — Conceptual design**: entities, relationships, cardinalities. Stable
  since Phase 0.
- **Part B — Implemented schema (Phase 1)**: the actual PostgreSQL tables,
  columns, constraints, and indexes now created by Alembic migration
  `0001_initial_schema` and mirrored by the SQLAlchemy models in
  `backend/app/db/models.py`.

> Phase 1 is PostgreSQL only. No pgvector, embeddings, semantic search, or
> Neo4j. Those are later phases.

---

## Part A — Conceptual design

### Entities (7 core + 2 associative)

| # | Entity | Role |
|---|--------|------|
| 1 | User | Person who creates prompts and collections. |
| 2 | Prompt | Logical prompt: owns lineage + metadata; content lives in versions. |
| 3 | Version | Immutable snapshot of a prompt's content. |
| 4 | Model | An AI/LLM model that experiments run against. |
| 5 | Experiment | One execution of a prompt version against a model. |
| 6 | Tag | Free-form label for prompts. |
| 7 | Collection | User-curated grouping of prompts. |
| 8 | PromptTag | Associative table — Prompt M:N Tag. Not a core entity. |
| 9 | PromptCollection | Associative table — Prompt M:N Collection. Not a core entity. |

### Relationships and cardinalities

| Relationship | Cardinality | Mechanism |
|--------------|-------------|-----------|
| User → Prompt | 1 : N | `prompts.user_id` |
| User → Collection | 1 : N | `collections.user_id` |
| User → Version (as author) | 1 : N | `versions.created_by` |
| Prompt → Version | 1 : N | `versions.prompt_id` |
| Prompt → Prompt (lineage / fork) | 1 : N | `prompts.parent_prompt_id` (self-reference) |
| Version → Experiment | 1 : N | `experiments.version_id` |
| Model → Experiment | 1 : N | `experiments.model_id` |
| Prompt ↔ Tag | M : N | `prompt_tags(prompt_id, tag_id)` |
| Prompt ↔ Collection | M : N | `prompt_collections(prompt_id, collection_id)` |

### Why the junction tables exist

`prompt_tags` and `prompt_collections` resolve **many-to-many** relationships,
which cannot be represented with a single foreign-key column on either side. Each
junction row is a pure association (its own composite primary key, no surface
attributes), which keeps the schema in 3NF and lets either side be queried
independently. They are infrastructure, not domain entities — hence "7 core
entities", not 9.

---

## Part B — Implemented schema (Phase 1)

### Conventions

- Every core entity has a **UUID** primary key
  (`DEFAULT gen_random_uuid()`, also generated client-side by SQLAlchemy).
- All timestamps are **`TIMESTAMPTZ`** stored in UTC, `DEFAULT now()`.
- `updated_at` is maintained by SQLAlchemy (`onupdate=now()`) plus a DB default
  for the initial write — see [Timestamps](#timestamps).
- Constraint / index names follow a fixed convention
  (`pk_`, `uq_`, `fk_`, `ck_`, `ix_`) so models and migration agree and tests
  can assert them.

### Table: `users`

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `user_id` | uuid | no | **PK** |
| `name` | varchar(100) | no | |
| `email` | varchar(255) | no | **UNIQUE** (`uq_users_email`) |
| `password_hash` | text | no | placeholder hashes only in Phase 1; no auth |
| `created_at` | timestamptz | no | `DEFAULT now()` |
| `updated_at` | timestamptz | no | `DEFAULT now()`, ORM `onupdate` |

### Table: `prompts`

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `prompt_id` | uuid | no | **PK** |
| `user_id` | uuid | no | **FK** → `users.user_id` **ON DELETE CASCADE** |
| `title` | varchar(200) | no | |
| `description` | text | yes | |
| `purpose` | text | yes | |
| `parent_prompt_id` | uuid | yes | **FK** → `prompts.prompt_id` **ON DELETE SET NULL** (self-reference: lineage / forking) |
| `is_public` | boolean | no | `DEFAULT false` |
| `created_at` | timestamptz | no | `DEFAULT now()` |
| `updated_at` | timestamptz | no | `DEFAULT now()`, ORM `onupdate` |

Indexes: `ix_prompts_user_id`, `ix_prompts_parent_prompt_id`.

### Table: `versions`  *(immutable — see [Versioning](#versioning-rules))*

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `version_id` | uuid | no | **PK** |
| `prompt_id` | uuid | no | **FK** → `prompts.prompt_id` **ON DELETE CASCADE** |
| `version_number` | integer | no | `CHECK (version_number > 0)` (`ck_versions_version_number_positive`) |
| `content` | text | no | |
| `change_summary` | text | yes | |
| `created_by` | uuid | no | **FK** → `users.user_id` **ON DELETE RESTRICT** |
| `created_at` | timestamptz | no | `DEFAULT now()` |

Constraints: `UNIQUE (prompt_id, version_number)`
(`uq_versions_prompt_id_version_number`).
Indexes: `ix_versions_created_by`.
`versions.prompt_id` is **not** separately indexed — it is the leading column of
the composite unique index, which already serves `WHERE prompt_id = ?`.

### Table: `models`

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `model_id` | uuid | no | **PK** |
| `name` | varchar(100) | no | **UNIQUE** (`uq_models_name`) |
| `provider` | varchar(100) | no | e.g. `OpenAI`, `Anthropic`, `Google` |
| `created_at` | timestamptz | no | `DEFAULT now()` |

### Table: `experiments`

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `experiment_id` | uuid | no | **PK** |
| `version_id` | uuid | no | **FK** → `versions.version_id` **ON DELETE CASCADE** |
| `model_id` | uuid | no | **FK** → `models.model_id` **ON DELETE RESTRICT** |
| `executed_at` | timestamptz | no | `DEFAULT now()` |
| `response_time_ms` | integer | yes | `CHECK (… IS NULL OR ≥ 0)` (`ck_experiments_response_time_ms_non_negative`) |
| `score` | numeric | yes | `CHECK (… IS NULL OR 0 ≤ score ≤ 10)` (`ck_experiments_score_between_0_and_10`) |
| `output` | text | yes | |
| `notes` | text | yes | |
| `status` | varchar(20) | no | `DEFAULT 'PENDING'`, `CHECK (status IN ('PENDING','SUCCESS','FAILED'))` (`ck_experiments_status_valid`) |
| `error_message` | text | yes | |

Indexes: `ix_experiments_version_id`, `ix_experiments_model_id`,
`ix_experiments_executed_at`.

### Table: `tags`

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `tag_id` | uuid | no | **PK** |
| `name` | varchar(50) | no | **UNIQUE** (`uq_tags_name`) |

### Table: `collections`

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `collection_id` | uuid | no | **PK** |
| `user_id` | uuid | no | **FK** → `users.user_id` **ON DELETE CASCADE** |
| `name` | varchar(150) | no | |
| `description` | text | yes | |
| `created_at` | timestamptz | no | `DEFAULT now()` |

Indexes: `ix_collections_user_id`.

### Table: `prompt_tags`

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `prompt_id` | uuid | no | **PK** part; **FK** → `prompts.prompt_id` **ON DELETE CASCADE** |
| `tag_id` | uuid | no | **PK** part; **FK** → `tags.tag_id` **ON DELETE CASCADE** |

Primary key: `(prompt_id, tag_id)`. Index: `ix_prompt_tags_tag_id`
(the `prompt_id` direction is served by the PK).

### Table: `prompt_collections`

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `prompt_id` | uuid | no | **PK** part; **FK** → `prompts.prompt_id` **ON DELETE CASCADE** |
| `collection_id` | uuid | no | **PK** part; **FK** → `collections.collection_id` **ON DELETE CASCADE** |

Primary key: `(prompt_id, collection_id)`. Index:
`ix_prompt_collections_collection_id`.

---

## Foreign-key delete behavior (summary)

| Parent → Child (FK column) | ON DELETE | Rationale |
|----------------------------|-----------|-----------|
| `users` → `prompts.user_id` | CASCADE | A user's prompts have no meaning without the user. |
| `users` → `collections.user_id` | CASCADE | Same — collections are owned. |
| `users` → `versions.created_by` | RESTRICT | Preserve authorship/audit history; a user who authored a version cannot be silently removed. |
| `prompts` → `versions.prompt_id` | CASCADE | Versions are parts of a prompt. |
| `prompts` → `prompts.parent_prompt_id` | SET NULL | Deleting an ancestor must not delete descendants; lineage link is simply lost. |
| `versions` → `experiments.version_id` | CASCADE | An experiment result is meaningless without the version it tested. |
| `models` → `experiments.model_id` | RESTRICT | Keep historical experiment results valid; a referenced model cannot be deleted. |
| `tags` → `prompt_tags.tag_id` | CASCADE | Remove the association only; prompts are untouched. |
| `collections` → `prompt_collections.collection_id` | CASCADE | Remove the association only; prompts are untouched. |
| `prompts` → `prompt_tags.prompt_id` | CASCADE | Remove associations with the prompt. |
| `prompts` → `prompt_collections.prompt_id` | CASCADE | Remove associations with the prompt. |

---

## Normalization

The schema is in **Third Normal Form (3NF)**.

### 1NF — atomic attributes
Every column holds a single value. There are no repeating groups or arrays: a
prompt's many tags are rows in `prompt_tags`, not a comma-separated column; a
prompt's many versions are rows in `versions`.

### 2NF — no partial dependency on a composite key
The only composite keys are in the junction tables `prompt_tags` and
`prompt_collections`, and those tables have **no non-key attributes at all**, so
a partial dependency is impossible. Every other table has a single-column
(`uuid`) key, so 2NF is automatically satisfied.

### 3NF — no transitive dependency of a non-key attribute on another non-key attribute
Descriptive data lives with its own key and is referenced by foreign key, never
copied:

- **Model** name/provider live in `models`. `experiments` stores only
  `model_id`; it never duplicates `models.name` or `models.provider`.
- **User** name/email live in `users`. `prompts`, `collections`, and `versions`
  store only `user_id` / `created_by`.
- **Tag** name lives in `tags`. `prompt_tags` stores only `tag_id`.
- **Prompt** title/description live in `prompts`. `versions` and `experiments`
  reach them through `prompt_id` / `version_id`, not by copy.

`updated_at` / `created_at` depend only on their row's key. `version_number`
depends on the whole `versions` row (identified by `version_id`), not on any
other non-key column. No computed or derived column is stored.

### Deliberately not stored (would violate 3NF or be redundant)
- "latest version number" on `prompts` — derivable via `MAX(version_number)`
  (see `database/examples.sql` query 3).
- "experiment count" / "average score" on `prompts` or `models` — derivable by
  aggregation (query 10).

---

## Indexes

Primary keys and `UNIQUE` constraints create their own indexes automatically
(`pk_*`, `uq_*`). The following **secondary** B-tree indexes are added because a
foreign key is not automatically indexed by PostgreSQL and each supports a
real access pattern:

| Index | Column(s) | Why |
|-------|-----------|-----|
| `ix_prompts_user_id` | `prompts.user_id` | "List a user's prompts" (examples.sql #1); speeds the `ON DELETE CASCADE` scan from `users`. |
| `ix_prompts_parent_prompt_id` | `prompts.parent_prompt_id` | Lineage traversal / "children of prompt X" (#8); needed for the `ON DELETE SET NULL` scan. |
| `ix_versions_created_by` | `versions.created_by` | "Versions authored by user X"; needed for the `ON DELETE RESTRICT` check. |
| `ix_experiments_version_id` | `experiments.version_id` | "Experiments for a version" (#4); CASCADE from `versions`. |
| `ix_experiments_model_id` | `experiments.model_id` | "Experiments / scores by model" (#5); RESTRICT check from `models`. |
| `ix_experiments_executed_at` | `experiments.executed_at` | Time-ordered listing / recent-activity queries (#9). |
| `ix_collections_user_id` | `collections.user_id` | "List a user's collections"; CASCADE from `users`. |
| `ix_prompt_tags_tag_id` | `prompt_tags.tag_id` | "Find prompts by tag" (#6). The `prompt_id` direction is served by the composite PK. |
| `ix_prompt_collections_collection_id` | `prompt_collections.collection_id` | "Find prompts in a collection" (#7). The `prompt_id` direction is served by the composite PK. |

**Not indexed on purpose** (would be redundant):
`versions.prompt_id` (leading column of `uq_versions_prompt_id_version_number`),
`prompt_tags.prompt_id` and `prompt_collections.prompt_id` (leading column of
their composite primary keys). No column is indexed "just in case", and there
are **no** GIN, GiST, HNSW, or vector indexes in Phase 1.

### Query-plan inspection

`database/examples.sql` ends with `EXPLAIN` statements showing how to check
index usage. With the tiny seed dataset (5 prompts / 8 versions / 8 experiments)
the index-vs-seqscan choice is not a meaningful performance signal — every plan
touches only a page or two. Observed on the seeded database: the equality query
on `experiments.model_id` **does** use `ix_experiments_model_id`, and the
"versions of a prompt" query uses the composite unique index
`uq_versions_prompt_id_version_number`. `SET enable_seqscan = off` is included to
show the indexes are usable by the planner regardless. No performance numbers
are claimed; meaningful benchmarking needs a bulk-loaded dataset.

---

## Versioning rules

- A `versions` row is **immutable**. Editing a prompt means inserting a **new**
  `versions` row with the next `version_number`; existing rows are never
  `UPDATE`d or `DELETE`d in normal operation.
- `version_number` starts at 1 and is unique per prompt
  (`UNIQUE (prompt_id, version_number)`, `CHECK (version_number > 0)`).
- Enforcement is **application-level plus tests/documentation**, not a database
  trigger. Rationale: a trigger to block `UPDATE`/`DELETE` on `versions` adds
  operational complexity (and fights migrations/back-fills) for little gain at
  this stage. `docs/decisions.md` Decision 13 records this; the test suite
  asserts the uniqueness and positivity constraints that make the rule
  enforceable.

---

## Timestamps

- All time columns are `TIMESTAMPTZ`; PostgreSQL stores them as UTC.
- `created_at` / `executed_at`: `server_default = now()`.
- `updated_at`: `server_default = now()` for the initial insert, and
  SQLAlchemy's `onupdate = now()` refreshes it on ORM updates.
  **Chosen over a database trigger** to keep the schema simple; the trade-off is
  that a raw `UPDATE` issued outside the ORM will not bump `updated_at`. If
  cross-tool guarantees are needed later, a `BEFORE UPDATE` trigger can be added
  in a migration. (Recorded as Decision 14.)

---

## Mapping to code

| Artifact | Location |
|----------|----------|
| SQLAlchemy models | `backend/app/db/models.py` |
| Declarative base + naming convention | `backend/app/db/base.py` |
| Migration | `backend/alembic/versions/0001_initial_schema.py` |
| Seed data | `backend/app/db/seed.py` |
| Schema tests | `backend/tests/test_database.py`, `test_seed.py`, `test_zz_migration.py` |
| Demonstration SQL | `database/examples.sql` |
