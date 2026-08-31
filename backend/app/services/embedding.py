"""Embedding lifecycle.

Consistency model: **PostgreSQL version data is authoritative; the embedding is
derived data.** Generating or regenerating an embedding is a separate `UPDATE`
that never touches ``versions.content`` and never deletes the version — an
embedding-provider failure leaves the version exactly as it was, with a NULL
(or previous) embedding, and can be retried.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.api.errors import ForbiddenError, NotFoundError, ServiceUnavailableError
from app.core.config import get_settings
from app.db.models import User, Version
from app.embeddings.base import EmbeddingError
from app.embeddings.registry import get_embedding_dimension, get_embedding_provider
from app.repositories import version as repo
from app.schemas.search import VersionEmbeddingStatus

logger = logging.getLogger("promptdna")


def _assert_owner(version: Version, user: User) -> None:
    prompt = version.prompt
    if prompt.user_id == user.user_id:
        return
    if prompt.is_public:
        raise ForbiddenError("Only the prompt owner can generate embeddings.")
    raise NotFoundError("Version not found.")


def _assert_viewable(version: Version, user: User) -> None:
    prompt = version.prompt
    if not (prompt.user_id == user.user_id or prompt.is_public):
        raise NotFoundError("Version not found.")


def generate_for_version(
    db: Session, version_id: uuid.UUID, *, current_user: User
) -> VersionEmbeddingStatus:
    """Owner-only: (re)generate the embedding for one version."""

    if not get_settings().pgvector_enabled:
        raise ServiceUnavailableError(
            "Embeddings are not available on this deployment (pgvector is not "
            "installed)."
        )

    version = repo.get_version_with_prompt(db, version_id)
    if version is None:
        raise NotFoundError("Version not found.")
    _assert_owner(version, current_user)

    provider = get_embedding_provider()
    if not provider.is_configured():
        raise ServiceUnavailableError(
            "The embedding provider is not configured on this server."
        )

    try:
        vector = provider.embed(
            version.content,
            timeout_s=get_settings().embedding_provider_timeout_s,
        )
    except EmbeddingError as exc:
        # The version is untouched; this is retryable.
        logger.warning(
            "embedding for version %s failed: %s", version_id, type(exc).__name__
        )
        raise ServiceUnavailableError(
            f"Could not generate the embedding: {exc.safe_message}"
        ) from None

    try:
        repo.set_embedding(
            db, version, vector=vector, model_name=provider.model_name
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("storing embedding for version %s failed", version_id)
        raise

    return VersionEmbeddingStatus(
        version_id=version.version_id,
        has_embedding=True,
        embedding_model=provider.model_name,
        dimension=get_embedding_dimension(),
    )


def get_status(
    db: Session, version_id: uuid.UUID, *, current_user: User
) -> VersionEmbeddingStatus:
    version = repo.get_version_with_prompt(db, version_id)
    if version is None:
        raise NotFoundError("Version not found.")
    _assert_viewable(version, current_user)
    pgvector_on = get_settings().pgvector_enabled
    return VersionEmbeddingStatus(
        version_id=version.version_id,
        has_embedding=bool(pgvector_on and version.embedding is not None),
        embedding_model=version.embedding_model if pgvector_on else None,
        dimension=get_embedding_dimension(),
    )


def try_autogenerate(db: Session, version_id: uuid.UUID) -> None:
    """Best-effort embed right after a version is created.

    Never raises — a failure just leaves ``embedding`` NULL (recoverable via the
    endpoint or ``scripts/generate_embeddings.py``). Only runs when
    ``EMBEDDING_AUTOGENERATE`` is on (needs pgvector + migration 0002).
    """

    if not get_settings().embedding_autogenerate:
        return
    try:
        provider = get_embedding_provider()
        if not provider.is_configured():
            return
        version = db.get(Version, version_id)
        if version is None or version.embedding is not None:
            return
        vector = provider.embed(
            version.content,
            timeout_s=get_settings().embedding_provider_timeout_s,
        )
        repo.set_embedding(db, version, vector=vector, model_name=provider.model_name)
        db.commit()
    except Exception:
        db.rollback()
        logger.warning("auto-embed for version %s failed (left NULL)", version_id)
