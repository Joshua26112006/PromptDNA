"""initial schema — PromptDNA Phase 1 (PostgreSQL relational core)

Creates the nine Phase 1 tables:
    users, prompts, versions, models, experiments,
    tags, collections, prompt_tags, prompt_collections

PostgreSQL only. No pgvector, no extensions beyond what ships with PostgreSQL
13+ (``gen_random_uuid()`` is built in).

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    # -- users ------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column(
            "user_id",
            UUID,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("user_id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    # -- tags -----------------------------------------------------------
    op.create_table(
        "tags",
        sa.Column(
            "tag_id",
            UUID,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("tag_id", name="pk_tags"),
        sa.UniqueConstraint("name", name="uq_tags_name"),
    )

    # -- models -------------------------------------------------------
    op.create_table(
        "models",
        sa.Column(
            "model_id",
            UUID,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("model_id", name="pk_models"),
        sa.UniqueConstraint("name", name="uq_models_name"),
    )

    # -- prompts (FK -> users; self-FK for lineage) --------------------
    op.create_table(
        "prompts",
        sa.Column(
            "prompt_id",
            UUID,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("parent_prompt_id", UUID, nullable=True),
        sa.Column(
            "is_public",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("prompt_id", name="pk_prompts"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name="fk_prompts_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_prompt_id"],
            ["prompts.prompt_id"],
            name="fk_prompts_parent_prompt_id_prompts",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_prompts_user_id", "prompts", ["user_id"])
    op.create_index(
        "ix_prompts_parent_prompt_id", "prompts", ["parent_prompt_id"]
    )

    # -- collections (FK -> users) ----------------------------------
    op.create_table(
        "collections",
        sa.Column(
            "collection_id",
            UUID,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("collection_id", name="pk_collections"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name="fk_collections_user_id_users",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_collections_user_id", "collections", ["user_id"])

    # -- versions (FK -> prompts CASCADE, users RESTRICT) -----------
    op.create_table(
        "versions",
        sa.Column(
            "version_id",
            UUID,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("prompt_id", UUID, nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("created_by", UUID, nullable=False),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("version_id", name="pk_versions"),
        sa.ForeignKeyConstraint(
            ["prompt_id"],
            ["prompts.prompt_id"],
            name="fk_versions_prompt_id_prompts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.user_id"],
            name="fk_versions_created_by_users",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "prompt_id",
            "version_number",
            name="uq_versions_prompt_id_version_number",
        ),
        sa.CheckConstraint(
            "version_number > 0", name="version_number_positive"
        ),
    )
    op.create_index("ix_versions_created_by", "versions", ["created_by"])

    # -- experiments (FK -> versions CASCADE, models RESTRICT) ------
    op.create_table(
        "experiments",
        sa.Column(
            "experiment_id",
            UUID,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("version_id", UUID, nullable=False),
        sa.Column("model_id", UUID, nullable=False),
        sa.Column(
            "executed_at", TS, server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("score", sa.Numeric(), nullable=True),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("experiment_id", name="pk_experiments"),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["versions.version_id"],
            name="fk_experiments_version_id_versions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["models.model_id"],
            name="fk_experiments_model_id_models",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "response_time_ms IS NULL OR response_time_ms >= 0",
            name="response_time_ms_non_negative",
        ),
        sa.CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 10)",
            name="score_between_0_and_10",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'SUCCESS', 'FAILED')",
            name="status_valid",
        ),
    )
    op.create_index("ix_experiments_version_id", "experiments", ["version_id"])
    op.create_index("ix_experiments_model_id", "experiments", ["model_id"])
    op.create_index(
        "ix_experiments_executed_at", "experiments", ["executed_at"]
    )

    # -- prompt_tags (M:N Prompt <-> Tag) ---------------------------
    op.create_table(
        "prompt_tags",
        sa.Column("prompt_id", UUID, nullable=False),
        sa.Column("tag_id", UUID, nullable=False),
        sa.PrimaryKeyConstraint(
            "prompt_id", "tag_id", name="pk_prompt_tags"
        ),
        sa.ForeignKeyConstraint(
            ["prompt_id"],
            ["prompts.prompt_id"],
            name="fk_prompt_tags_prompt_id_prompts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.tag_id"],
            name="fk_prompt_tags_tag_id_tags",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_prompt_tags_tag_id", "prompt_tags", ["tag_id"])

    # -- prompt_collections (M:N Prompt <-> Collection) ------------
    op.create_table(
        "prompt_collections",
        sa.Column("prompt_id", UUID, nullable=False),
        sa.Column("collection_id", UUID, nullable=False),
        sa.PrimaryKeyConstraint(
            "prompt_id", "collection_id", name="pk_prompt_collections"
        ),
        sa.ForeignKeyConstraint(
            ["prompt_id"],
            ["prompts.prompt_id"],
            name="fk_prompt_collections_prompt_id_prompts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["collections.collection_id"],
            name="fk_prompt_collections_collection_id_collections",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_prompt_collections_collection_id",
        "prompt_collections",
        ["collection_id"],
    )


def downgrade() -> None:
    op.drop_table("prompt_collections")
    op.drop_table("prompt_tags")
    op.drop_table("experiments")
    op.drop_table("versions")
    op.drop_table("collections")
    op.drop_table("prompts")
    op.drop_table("models")
    op.drop_table("tags")
    op.drop_table("users")
