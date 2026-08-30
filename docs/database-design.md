# PromptDNA — Database Design

> **Status: PLANNED. Not implemented in Phase 0.**
> No tables, columns, or migrations exist yet. Schema implementation is Phase 1.
> This document records the *approved* design so Phase 1 can execute it without
> redesign.

## Principles

- PostgreSQL is the system of record; schema normalized to **3NF**.
- Every main entity uses a **UUID** primary key.
- All foreign keys are **explicit**.
- Versions are **immutable** (see below).
- Embeddings belong to **versions**, not prompts.
- `pgvector` stores embeddings in PostgreSQL alongside relational data.
- Neo4j holds a **projection** of prompt-to-prompt relationships only.

## Core entities (7)

| # | Entity       | Purpose                                                            |
| - | ------------ | ----------------------------------------------------------------- |
| 1 | `User`       | A person who creates prompts.                                     |
| 2 | `Prompt`     | A logical prompt; owns a lineage and many versions.               |
| 3 | `Version`    | An immutable snapshot of a prompt's content.                      |
| 4 | `Model`      | An AI/LLM model that experiments run against.                     |
| 5 | `Experiment` | One test/execution of a specific version against a model.         |
| 6 | `Tag`        | A free-form label applied to prompts.                             |
| 7 | `Collection` | A user-curated grouping of prompts.                               |

## Associative / junction tables (2) — not counted as core entities

| # | Table                | Links                          |
| - | -------------------- | ------------------------------ |
| 8 | `prompt_tags`        | `Prompt` ↔ `Tag`               |
| 9 | `prompt_collections` | `Prompt` ↔ `Collection`        |

## Tables (final names)

```
users
prompts
versions
models
experiments
tags
collections
prompt_tags
prompt_collections
```

## Relationships

| Relationship                         | Cardinality | Implementation                         |
| ------------------------------------ | ----------- | -------------------------------------- |
| User → Prompt                        | 1 : N       | `prompts.user_id → users`             |
| Prompt → Version                     | 1 : N       | `versions.prompt_id → prompts`        |
| Version → Experiment                 | 1 : N       | `experiments.version_id → versions`   |
| Model → Experiment                   | 1 : N       | `experiments.model_id → models`       |
| Prompt ↔ Tag                         | M : N       | `prompt_tags(prompt_id, tag_id)`      |
| Prompt ↔ Collection                  | M : N       | `prompt_collections(prompt_id, collection_id)` |
| Prompt → Prompt (derivation/lineage) | 1 : N       | `prompts.parent_prompt_id → prompts` (self-reference) |

## Key constraints

- `users.email` **UNIQUE**
- `models.name` **UNIQUE**
- `tags.name` **UNIQUE**
- `(versions.prompt_id, versions.version_number)` **UNIQUE**
- Composite PK on `prompt_tags(prompt_id, tag_id)`
- Composite PK on `prompt_collections(prompt_id, collection_id)`

## Delete behavior (locked for Phase 1)

| Relationship                     | ON DELETE   |
| -------------------------------- | ----------- |
| `users` → `prompts`              | CASCADE     |
| `prompts` → `versions`           | CASCADE     |
| `prompts.parent_prompt_id`       | SET NULL    |
| `versions` → `experiments`       | CASCADE     |
| `models` → `experiments`         | RESTRICT    |
| `collections` → `prompt_collections` | CASCADE |
| `tags` → `prompt_tags`           | CASCADE     |

## Versioning

- Versions are **immutable**. Editing a prompt creates a **new** version; the
  content of an existing version is never updated.
- `version_number` is unique per prompt (e.g. P1 → v1, v2, v3).
- Rationale: historical prompt states must remain reproducible and auditable.

## Experiment (planned columns — not implemented in Phase 0)

```
experiment_id      UUID PK
version_id         UUID FK → versions
model_id           UUID FK → models
executed_at        timestamptz
response_time_ms   integer
score              numeric
output             text
notes              text
status             text
error_message      text
```

## Embeddings (planned — not implemented in Phase 0)

- An embedding is stored **per version** (each version has different content).
- Stored in PostgreSQL via `pgvector`.
- **Vector dimension is NOT decided.** Do not hard-code `VECTOR(1536)` or any
  other dimension. It will be fixed once the embedding model is selected in the
  semantic-search phase.
- The embedding provider is accessed through an abstraction (added later) so it
  stays replaceable.

## Neo4j projection (planned — not implemented in Phase 0)

PostgreSQL remains the source of truth; Neo4j mirrors prompt relationships for
variable-depth traversal.

```
(:Prompt)-[:DERIVED_FROM]->(:Prompt)
(:Prompt)-[:FORKED_FROM]->(:Prompt)
(:Prompt)-[:DEPENDS_ON]->(:Prompt)
```

No additional relationship types without approval.

## Migrations

- Tool: **Alembic** (`backend/alembic/`).
- Phase 0: environment wired to `DATABASE_URL`, `versions/` empty, no models.
- Phase 1: introduce SQLAlchemy models, set `target_metadata`, generate the
  first revision.
