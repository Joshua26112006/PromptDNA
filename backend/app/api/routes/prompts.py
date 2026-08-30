"""Prompt & version endpoints (versioned under ``/api/v1``).

All endpoints require ``Authorization: Bearer <token>``. Ownership / visibility
is decided in the service layer, not here.

Prompt content lives in **versions**; existing versions are **immutable** — there
is deliberately no PUT/PATCH/DELETE for a version.
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
    PromptUpdate,
    VersionCreate,
    VersionListResponse,
    VersionRead,
)
from app.services import prompt as service

router = APIRouter(prefix="/prompts", tags=["prompts"])

DbDep = Annotated[Session, Depends(get_db)]
PromptIdPath = Annotated[uuid.UUID, Path(description="Prompt UUID.")]
VersionIdPath = Annotated[uuid.UUID, Path(description="Version UUID.")]


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
    neither is persisted. The client cannot set the owner. Optionally pass
    ``parent_prompt_id`` (a prompt the caller can view) to record lineage."""

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


@router.patch(
    "/{prompt_id}",
    response_model=PromptRead,
    summary="Update prompt metadata only (owner only)",
)
def update_prompt(
    prompt_id: PromptIdPath,
    payload: PromptUpdate,
    db: DbDep,
    current_user: CurrentUser,
) -> PromptRead:
    """Update `title` / `description` / `purpose` / `is_public` only. Never
    touches version content, `version_number`, `created_by`, ownership, or
    `parent_prompt_id`. Only the owner may call this (`403` for a public prompt
    owned by someone else, `404` otherwise)."""

    return service.update_prompt_metadata(
        db, prompt_id, current_user=current_user, data=payload
    )


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
    create/update/delete endpoint exists for an individual version."""

    return service.list_versions(db, prompt_id, current_user=current_user)


@router.post(
    "/{prompt_id}/versions",
    response_model=VersionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Append a new version to a prompt (owner only)",
)
def create_prompt_version(
    prompt_id: PromptIdPath,
    payload: VersionCreate,
    db: DbDep,
    current_user: CurrentUser,
) -> VersionRead:
    """Create the next version (`version_number` = current max + 1). Only the
    **prompt owner** may do this — a public prompt does NOT let other users add
    versions (`403`); a private prompt owned by someone else is `404`. Existing
    versions are never modified. On a concurrent version-number collision the
    insert is retried; if it still cannot be placed, `409` is returned."""

    return service.create_version(
        db, prompt_id, current_user=current_user, data=payload
    )


@router.get(
    "/{prompt_id}/versions/{version_id}",
    response_model=VersionRead,
    summary="Get one version of a prompt",
)
def get_prompt_version(
    prompt_id: PromptIdPath,
    version_id: VersionIdPath,
    db: DbDep,
    current_user: CurrentUser,
) -> VersionRead:
    """Returns the version only if it belongs to `prompt_id` **and** the caller
    can view that prompt. Any mismatch (wrong prompt, missing version,
    inaccessible private prompt) → `404`."""

    return service.get_version(
        db, prompt_id, version_id, current_user=current_user
    )
