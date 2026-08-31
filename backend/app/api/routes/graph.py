"""Graph traversal endpoints (Phase 7, ``/api/v1/graph``).

Thin: authorize + call the service. All Cypher is in ``app/graph/service.py``.
Neo4j answers "how are these prompts explicitly connected?" — distinct from
pgvector, which answers "what prompts have similar meaning?".
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.schemas.graph import GraphResponse
from app.services import graph as service

router = APIRouter(prefix="/graph", tags=["graph"])

DbDep = Annotated[Session, Depends(get_db)]
PromptId = Annotated[uuid.UUID, Path(description="Prompt UUID (PostgreSQL id).")]
Depth = Annotated[int, Query(ge=1, le=10, description="Max traversal depth.")]


@router.get(
    "/prompts/{prompt_id}/ancestors",
    response_model=GraphResponse,
    summary="Prompts this prompt was derived/forked from (transitive)",
)
def ancestors(
    prompt_id: PromptId, db: DbDep, current_user: CurrentUser, depth: Depth = 10
) -> GraphResponse:
    return service.ancestors(db, prompt_id, current_user=current_user, depth=depth)


@router.get(
    "/prompts/{prompt_id}/descendants",
    response_model=GraphResponse,
    summary="Prompts derived/forked from this prompt (transitive)",
)
def descendants(
    prompt_id: PromptId, db: DbDep, current_user: CurrentUser, depth: Depth = 10
) -> GraphResponse:
    return service.descendants(db, prompt_id, current_user=current_user, depth=depth)


@router.get(
    "/prompts/{prompt_id}/dependencies",
    response_model=GraphResponse,
    summary="Prompts this prompt explicitly DEPENDS_ON (transitive)",
)
def dependencies(
    prompt_id: PromptId, db: DbDep, current_user: CurrentUser, depth: Depth = 10
) -> GraphResponse:
    """Explicit dependency only — **not** semantic similarity (that is
    `/api/v1/search/semantic`, backed by pgvector)."""

    return service.dependencies(db, prompt_id, current_user=current_user, depth=depth)


@router.get(
    "/prompts/{prompt_id}/related",
    response_model=GraphResponse,
    summary="Prompts one hop away on any approved relationship (both directions)",
)
def related(
    prompt_id: PromptId, db: DbDep, current_user: CurrentUser
) -> GraphResponse:
    return service.related(db, prompt_id, current_user=current_user)
