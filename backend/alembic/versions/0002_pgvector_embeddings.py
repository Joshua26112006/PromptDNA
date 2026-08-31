"""pgvector extension + versions.embedding (Phase 6, semantic search)

Adds ONLY derived-data columns to ``versions`` — no existing column, key,
foreign key, or relationship is changed:

* ``CREATE EXTENSION IF NOT EXISTS vector``
* ``versions.embedding``        ``vector(1536)``   NULL  (dimension = OpenAI
  text-embedding-3-small; the mock provider matches it)
* ``versions.embedding_model``  ``varchar(100)``   NULL  (which model produced it)
* HNSW index on ``embedding`` using ``vector_cosine_ops`` (matches the ``<=>``
  cosine-distance operator the semantic-search query uses)

**Requires** a PostgreSQL with the ``vector`` extension available
(``pgvector/pgvector`` image, Neon, or a local ``CREATE EXTENSION`` build). On a
database where ``vector`` is not available this migration cannot run — that is
intentional: the feature needs pgvector.

Revision ID: 0002_pgvector_embeddings
Revises: 0001_initial_schema
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0002_pgvector_embeddings"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DIMENSION = 1536
_HNSW_INDEX = "ix_versions_embedding_hnsw"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        "versions", sa.Column("embedding", Vector(_DIMENSION), nullable=True)
    )
    op.add_column(
        "versions", sa.Column("embedding_model", sa.String(length=100), nullable=True)
    )
    op.create_index(
        _HNSW_INDEX,
        "versions",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index(_HNSW_INDEX, table_name="versions")
    op.drop_column("versions", "embedding_model")
    op.drop_column("versions", "embedding")
    # Safe: only drops the extension if nothing else depends on it.
    op.execute("DROP EXTENSION IF EXISTS vector")
