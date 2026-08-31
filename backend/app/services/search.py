"""Semantic search: embed the query, nearest versions by cosine similarity,
visibility-filtered **in the database query**.

Lexical search (``GET /api/v1/prompts?search=``) is unchanged and still lives in
``services/prompt.py``. This is the separate *semantic* mode.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.api.errors import BadRequestError, ServiceUnavailableError
from app.core.config import get_settings
from app.db.models import User
from app.embeddings.base import EmbeddingError
from app.embeddings.registry import get_embedding_provider
from app.repositories import version as repo
from app.schemas.search import SemanticSearchResponse, SemanticSearchResult

logger = logging.getLogger("promptdna")

_PREVIEW = 240


def semantic_search(
    db: Session,
    *,
    current_user: User,
    query: str,
    limit: int,
    is_public: bool | None = None,
    owner_only: bool = False,
) -> SemanticSearchResponse:
    q = query.strip()
    if not q:
        raise BadRequestError("Search query must not be empty.")

    if not get_settings().pgvector_enabled:
        raise ServiceUnavailableError(
            "Semantic search is not available on this deployment (pgvector is "
            "not installed). Use lexical search: GET /api/v1/prompts?search=…"
        )

    provider = get_embedding_provider()
    if not provider.is_configured():
        raise ServiceUnavailableError(
            "Semantic search is unavailable: the embedding provider is not "
            "configured on this server."
        )
    try:
        query_vector = provider.embed(
            q, timeout_s=get_settings().embedding_provider_timeout_s
        )
    except EmbeddingError as exc:
        logger.warning("query embedding failed: %s", type(exc).__name__)
        raise ServiceUnavailableError(
            f"Semantic search is temporarily unavailable: {exc.safe_message}"
        ) from None

    rows = repo.semantic_search(
        db,
        query_vector=query_vector,
        viewer_id=current_user.user_id,
        limit=limit,
        is_public=is_public,
        owner_only=owner_only,
    )
    results = [
        SemanticSearchResult(
            prompt_id=row.Prompt.prompt_id,
            version_id=row.Version.version_id,
            prompt_title=row.Prompt.title,
            version_number=row.Version.version_number,
            content_preview=row.Version.content[:_PREVIEW],
            similarity=float(row.similarity),
            is_public=row.Prompt.is_public,
            created_at=row.Version.created_at,
        )
        for row in rows
    ]
    return SemanticSearchResponse(query=q, count=len(results), results=results)
