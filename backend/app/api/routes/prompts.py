"""Prompt endpoints (versioned under ``/api/v1``).

Routers are thin: parse/validate input, call a service, return a response
schema. No database access here.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_dev_user_id
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
    payload: PromptCreate,
    db: DbDep,
    dev_user_id: Annotated[uuid.UUID, Depends(get_dev_user_id)],
) -> PromptRead:
    """Create a prompt owned by the `X-Dev-User-ID` user.

    The prompt row and its first `versions` row (``version_number = 1``,
    containing ``content``) are written in a single transaction: if either
    insert fails, neither is persisted.
    """

    return service.create_prompt_with_initial_version(
        db, dev_user_id=dev_user_id, data=payload
    )


@router.get(
    "",
    response_model=PromptListResponse,
    summary="List prompts (paginated)",
)
def list_prompts(
    db: DbDep,
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
    return service.list_prompts(
        db, limit=limit, offset=offset, search=search, is_public=is_public
    )


@router.get(
    "/{prompt_id}",
    response_model=PromptRead,
    summary="Get one prompt with its owner and all versions",
)
def get_prompt(prompt_id: PromptIdPath, db: DbDep) -> PromptRead:
    return service.get_prompt(db, prompt_id)


@router.get(
    "/{prompt_id}/versions",
    response_model=VersionListResponse,
    summary="List a prompt's versions (immutable, ordered by version_number ASC)",
)
def list_prompt_versions(
    prompt_id: PromptIdPath, db: DbDep
) -> VersionListResponse:
    """Read-only. Versions are immutable — there is no create/update/delete
    endpoint for versions in this phase (see docs/api.md)."""

    return service.list_versions(db, prompt_id)
