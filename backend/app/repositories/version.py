"""Data access for version embeddings + semantic (vector) search. No commits.

Semantic search applies the visibility predicate **inside the SQL query** (a
prompt is visible iff the viewer owns it OR it is public), so private prompts of
other users are never even scored — not retrieved-then-filtered.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import Row, and_, or_, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Prompt, Version


def get_version_with_prompt(db: Session, version_id: uuid.UUID) -> Version | None:
    stmt = (
        select(Version)
        .where(Version.version_id == version_id)
        .options(joinedload(Version.prompt))
    )
    return db.scalars(stmt).one_or_none()


def set_embedding(
    db: Session, version: Version, *, vector: list[float], model_name: str
) -> Version:
    version.embedding = vector
    version.embedding_model = model_name
    db.flush()
    return version


def versions_missing_embedding(
    db: Session, *, limit: int = 500
) -> Sequence[Version]:
    stmt = (
        select(Version)
        .where(Version.embedding.is_(None))
        .order_by(Version.created_at.asc())
        .limit(limit)
    )
    return db.scalars(stmt).all()


def semantic_search(
    db: Session,
    *,
    query_vector: list[float],
    viewer_id: uuid.UUID,
    limit: int,
    is_public: bool | None = None,
    owner_only: bool = False,
) -> Sequence[Row]:
    """Nearest versions by **cosine distance** (`<=>`), visibility-filtered.

    Returns rows with ``.Prompt``, ``.Version`` and ``.similarity``
    (``1 - cosine_distance`` ∈ roughly [-1, 1]; ~1 = very close). The raw vector
    is never selected.
    """

    visibility = or_(Prompt.user_id == viewer_id, Prompt.is_public.is_(True))
    filters = [Version.embedding.is_not(None), visibility]
    if owner_only:
        filters.append(Prompt.user_id == viewer_id)
    if is_public is not None:
        filters.append(Prompt.is_public.is_(is_public))

    distance = Version.embedding.cosine_distance(query_vector)
    stmt = (
        select(
            Prompt,
            Version,
            (1 - distance).label("similarity"),
        )
        .join(Prompt, Prompt.prompt_id == Version.prompt_id)
        .where(and_(*filters))
        .order_by(distance.asc())
        .limit(limit)
    )
    return db.execute(stmt).all()
