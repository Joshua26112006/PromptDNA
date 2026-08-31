"""SQLAlchemy models for the PromptDNA relational schema (Phase 1).

These definitions are the single source of truth for the schema and MUST stay
in agreement with the Alembic migration ``0001_initial_schema``.

Scope notes:
* PostgreSQL only. No pgvector column, no embeddings, no graph concerns.
* Models carry schema (columns, constraints, indexes, relationships) only —
  no business logic, no validation beyond database constraints.
* ``versions`` rows are **immutable by design**: once written, ``content`` and
  the other columns are never updated. This is an application-level rule
  (documented here and covered by tests); no database trigger is used, to
  avoid over-engineering for this phase.
"""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.core.config import get_settings
from app.db.base import Base

# Allowed values for experiments.status. A CHECK constraint (rather than a
# native PostgreSQL ENUM type) is used so the set can evolve with an ordinary
# migration — see docs/decisions.md, Decision 15.
EXPERIMENT_STATUSES = ("PENDING", "SUCCESS", "FAILED")

# Fixed vector dimension for versions.embedding (Phase 6). Set at migration
# 0002. 1536 = OpenAI text-embedding-3-small; the mock provider matches it.
# Changing this requires a new migration and re-embedding all versions.
EMBEDDING_DIMENSION = 1536

# The versions.embedding / embedding_model columns (and their HNSW index) exist
# only where pgvector + migration 0002 are present. Gated so the rest of the
# schema is usable on a plain PostgreSQL. See docs/decisions.md.
PGVECTOR_ENABLED = get_settings().pgvector_enabled


def _uuid_pk() -> Mapped[uuid.UUID]:
    """A UUID primary key column.

    ``default`` gives ORM-created rows an id before flush; ``server_default``
    covers rows created by raw SQL (e.g. ``database/examples.sql``).
    ``gen_random_uuid()`` is built into PostgreSQL 13+.
    """

    return mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )


def _created_at() -> Mapped[datetime.datetime]:
    return mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = _created_at()
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    prompts: Mapped[list[Prompt]] = relationship(
        back_populates="owner",
        foreign_keys="Prompt.user_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    collections: Mapped[list[Collection]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Prompt(Base):
    __tablename__ = "prompts"

    prompt_id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_prompt_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("prompts.prompt_id", ondelete="SET NULL"),
        nullable=True,
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime.datetime] = _created_at()
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    owner: Mapped[User] = relationship(
        back_populates="prompts", foreign_keys=[user_id]
    )
    parent: Mapped[Prompt | None] = relationship(
        "Prompt",
        remote_side=[prompt_id],
        foreign_keys=[parent_prompt_id],
        backref="children",
    )
    versions: Mapped[list[Version]] = relationship(
        back_populates="prompt",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Version.version_number",
    )
    tags: Mapped[list[Tag]] = relationship(
        secondary="prompt_tags", back_populates="prompts", passive_deletes=True
    )
    collections: Mapped[list[Collection]] = relationship(
        secondary="prompt_collections",
        back_populates="prompts",
        passive_deletes=True,
    )


class Version(Base):
    __tablename__ = "versions"

    version_id: Mapped[uuid.UUID] = _uuid_pk()
    prompt_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("prompts.prompt_id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime.datetime] = _created_at()

    # -- Phase 6: derived semantic embedding of `content` -----------------
    # Present only where pgvector + migration 0002 are installed
    # (PGVECTOR_ENABLED). Nullable: PostgreSQL version data is authoritative,
    # the embedding is derived and recoverable. `deferred`: never in a default
    # `SELECT versions.*` — the search query names the column explicitly.
    if PGVECTOR_ENABLED:  # noqa: SIM108 - conditional column mapping
        embedding: Mapped[list[float] | None] = mapped_column(
            Vector(EMBEDDING_DIMENSION), nullable=True, deferred=True
        )
        embedding_model: Mapped[str | None] = mapped_column(
            String(100), nullable=True, deferred=True
        )

    __table_args__ = (
        UniqueConstraint("prompt_id", "version_number"),
        CheckConstraint("version_number > 0", name="version_number_positive"),
    )

    prompt: Mapped[Prompt] = relationship(
        back_populates="versions", foreign_keys=[prompt_id]
    )
    author: Mapped[User] = relationship(foreign_keys=[created_by])
    experiments: Mapped[list[Experiment]] = relationship(
        back_populates="version",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Model(Base):
    __tablename__ = "models"

    model_id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime.datetime] = _created_at()

    experiments: Mapped[list[Experiment]] = relationship(
        back_populates="model", passive_deletes=True
    )


class Experiment(Base):
    __tablename__ = "experiments"

    experiment_id: Mapped[uuid.UUID] = _uuid_pk()
    version_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("versions.version_id", ondelete="CASCADE"),
        nullable=False,
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("models.model_id", ondelete="RESTRICT"),
        nullable=False,
    )
    executed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'PENDING'")
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "response_time_ms IS NULL OR response_time_ms >= 0",
            name="response_time_ms_non_negative",
        ),
        CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 10)",
            name="score_between_0_and_10",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'SUCCESS', 'FAILED')",
            name="status_valid",
        ),
    )

    version: Mapped[Version] = relationship(back_populates="experiments")
    model: Mapped[Model] = relationship(back_populates="experiments")


class Tag(Base):
    __tablename__ = "tags"

    tag_id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    prompts: Mapped[list[Prompt]] = relationship(
        secondary="prompt_tags", back_populates="tags", passive_deletes=True
    )


class Collection(Base):
    __tablename__ = "collections"

    collection_id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = _created_at()

    owner: Mapped[User] = relationship(back_populates="collections")
    prompts: Mapped[list[Prompt]] = relationship(
        secondary="prompt_collections",
        back_populates="collections",
        passive_deletes=True,
    )


class PromptTag(Base):
    """Associative table for the Prompt M:N Tag relationship."""

    __tablename__ = "prompt_tags"

    prompt_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("prompts.prompt_id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tags.tag_id", ondelete="CASCADE"),
        primary_key=True,
    )


class PromptCollection(Base):
    """Associative table for the Prompt M:N Collection relationship."""

    __tablename__ = "prompt_collections"

    prompt_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("prompts.prompt_id", ondelete="CASCADE"),
        primary_key=True,
    )
    collection_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("collections.collection_id", ondelete="CASCADE"),
        primary_key=True,
    )


# --- Explicit secondary (non-primary, non-unique) indexes --------------------
# Declared here so the rationale lives in one place. See
# docs/database-design.md "Indexes" for the full justification table.
Index("ix_prompts_user_id", Prompt.user_id)
Index("ix_prompts_parent_prompt_id", Prompt.parent_prompt_id)
Index("ix_versions_created_by", Version.created_by)
if PGVECTOR_ENABLED:
    # Phase 6: HNSW approximate-nearest-neighbour index over the embedding,
    # using the cosine-distance operator class (matches the `<=>` operator the
    # semantic search query uses). Built by migration 0002.
    Index(
        "ix_versions_embedding_hnsw",
        Version.embedding,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
Index("ix_experiments_version_id", Experiment.version_id)
Index("ix_experiments_model_id", Experiment.model_id)
Index("ix_experiments_executed_at", Experiment.executed_at)
Index("ix_collections_user_id", Collection.user_id)
Index("ix_prompt_tags_tag_id", PromptTag.tag_id)
Index("ix_prompt_collections_collection_id", PromptCollection.collection_id)

# Intentionally NOT indexed separately (would be redundant):
#   versions.prompt_id            -> leading column of
#                                    uq_versions_prompt_id_version_number
#   prompt_tags.prompt_id         -> leading column of pk_prompt_tags
#   prompt_collections.prompt_id  -> leading column of pk_prompt_collections

__all__ = [
    "Base",
    "User",
    "Prompt",
    "Version",
    "Model",
    "Experiment",
    "Tag",
    "Collection",
    "PromptTag",
    "PromptCollection",
    "EXPERIMENT_STATUSES",
]
