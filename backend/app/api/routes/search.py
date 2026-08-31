"""Semantic search + version-embedding endpoints (Phase 6, ``/api/v1``).

Semantic search is a **separate mode** from lexical search
(``GET /api/v1/prompts?search=``). It finds prompts with similar *meaning* even
when the wording differs, by comparing embedding vectors in pgvector.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.schemas.search import SemanticSearchResponse, VersionEmbeddingStatus
from app.services import embedding as embedding_service
from app.services import search as search_service

router = APIRouter(tags=["search"])

DbDep = Annotated[Session, Depends(get_db)]
VersionId = Annotated[uuid.UUID, Path(description="Version UUID.")]


@router.get(
    "/search/semantic",
    response_model=SemanticSearchResponse,
    summary="Semantic (vector) search over versions the caller may view",
)
def semantic_search(
    db: DbDep,
    current_user: CurrentUser,
    query: Annotated[str, Query(min_length=1, max_length=2000)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    is_public: Annotated[bool | None, Query()] = None,
    owner: Annotated[bool, Query(description="Restrict to the caller's own prompts.")] = False,
) -> SemanticSearchResponse:
    """Embeds `query`, returns the nearest versions by **cosine similarity**.
    The searchable set is the caller's own prompts + public prompts — the
    visibility filter is part of the SQL query, so other users' private prompts
    are never scored. Never returns raw vectors."""

    return search_service.semantic_search(
        db,
        current_user=current_user,
        query=query,
        limit=limit,
        is_public=is_public,
        owner_only=owner,
    )


@router.post(
    "/versions/{version_id}/embedding",
    response_model=VersionEmbeddingStatus,
    summary="Generate / regenerate a version's embedding (owner only)",
)
def create_version_embedding(
    version_id: VersionId, db: DbDep, current_user: CurrentUser
) -> VersionEmbeddingStatus:
    """Only the prompt owner may trigger this (it can cost money). Never
    modifies `versions.content`; a provider failure leaves the version intact.
    `503` if the embedding provider is unconfigured."""

    return embedding_service.generate_for_version(
        db, version_id, current_user=current_user
    )


@router.get(
    "/versions/{version_id}/embedding",
    response_model=VersionEmbeddingStatus,
    summary="Embedding status for a version",
)
def get_version_embedding(
    version_id: VersionId, db: DbDep, current_user: CurrentUser
) -> VersionEmbeddingStatus:
    return embedding_service.get_status(db, version_id, current_user=current_user)
