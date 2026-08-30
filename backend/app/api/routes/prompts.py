"""Prompt endpoints (versioned under ``/api/v1``).

All endpoints require ``Authorization: Bearer <token>`` (Phase 3). Ownership /
visibility is decided in the service layer, not here.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.schemas.prompt import (
    PromptCreate,
    PromptListResponse,
    PromptRead,
    VersionListResponse,
)
from app.services import prompt as service

router = APIRouter(prefix="/prompts", tags=["prompts"])

DbDep = Annotated[Session, Depends(get_db)]
PromptIdPath = Annotated[uuid.UUID, Path(description="Prompt UUID.")]


@router.post(
    "",
    response_model=PromptRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a prompt (and its Version 1) atomically",
)
def create_prompt(
    payload: PromptCreate, db: DbDep, current_user: CurrentUser
) -> PromptRead:
    """Create a prompt owned by the **authenticated user** and its Version 1
    (containing ``content``) in a single transaction — if either insert fails,
    neither is persisted. The client cannot set the owner."""

    return service.create_prompt_with_initial_version(
        db, current_user=current_user, data=payload
    )


@router.get(
    "",
    response_model=PromptListResponse,
    summary="List prompts visible to the authenticated user (paginated)",
)
def list_prompts(
    db: DbDep,
    current_user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[
        str | None,
        Query(
            max_length=200,
            description="Case-insensitive substring match on title "
            "(lexical only — not semantic search).",
        ),
    ] = None,
    is_public: Annotated[bool | None, Query()] = None,
) -> PromptListResponse:
    """Returns the caller's own prompts plus public prompts. Query parameters
    can only narrow this set — they cannot expose other users' private
    prompts."""

    return service.list_prompts(
        db,
        current_user=current_user,
        limit=limit,
        offset=offset,
        search=search,
        is_public=is_public,
    )


@router.get(
    "/{prompt_id}",
    response_model=PromptRead,
    summary="Get one prompt (owner or public only; 404 otherwise)",
)
def get_prompt(
    prompt_id: PromptIdPath, db: DbDep, current_user: CurrentUser
) -> PromptRead:
    return service.get_prompt(db, prompt_id, current_user=current_user)


@router.get(
    "/{prompt_id}/versions",
    response_model=VersionListResponse,
    summary="List a prompt's versions (immutable, version_number ASC)",
)
def list_prompt_versions(
    prompt_id: PromptIdPath, db: DbDep, current_user: CurrentUser
) -> VersionListResponse:
    """Read-only. Access follows the parent prompt's visibility (404 if the
    caller may not view the prompt). Versions are immutable — no
    create/update/delete endpoint exists."""

    return service.list_versions(db, prompt_id, current_user=current_user)
