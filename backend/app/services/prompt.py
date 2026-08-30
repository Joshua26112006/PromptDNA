"""Prompt business logic.

Transaction boundary of note — :func:`create_prompt_with_initial_version`:

    BEGIN
        INSERT prompts
        INSERT versions (version_number = 1)
    COMMIT            -- both, or neither

If the version insert fails for any reason the whole thing is rolled back, so a
prompt can never exist without its Version 1.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.api.errors import NotFoundError
from app.db.models import Prompt, Version
from app.repositories import prompt as repo
from app.schemas.prompt import (
    OwnerRead,
    PromptCreate,
    PromptListItem,
    PromptListResponse,
    PromptRead,
    VersionListResponse,
    VersionRead,
)

logger = logging.getLogger("promptdna")

INITIAL_VERSION_NUMBER = 1
INITIAL_CHANGE_SUMMARY = "Initial version."


# --------------------------------------------------------------------------- #
# Serialization helpers (ORM -> response schema)                             #
# --------------------------------------------------------------------------- #
def _to_prompt_read(prompt: Prompt) -> PromptRead:
    versions = sorted(prompt.versions, key=lambda v: v.version_number)
    version_reads = [VersionRead.model_validate(v) for v in versions]
    return PromptRead(
        prompt_id=prompt.prompt_id,
        user_id=prompt.user_id,
        title=prompt.title,
        description=prompt.description,
        purpose=prompt.purpose,
        is_public=prompt.is_public,
        parent_prompt_id=prompt.parent_prompt_id,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
        owner=OwnerRead.model_validate(prompt.owner),
        versions=version_reads,
        latest_version=version_reads[-1] if version_reads else None,
        tags=sorted(tag.name for tag in prompt.tags),
    )


# --------------------------------------------------------------------------- #
# Commands                                                                   #
# --------------------------------------------------------------------------- #
def create_prompt_with_initial_version(
    db: Session, *, dev_user_id: uuid.UUID, data: PromptCreate
) -> PromptRead:
    """Create a prompt and its Version 1 atomically. Returns the full prompt.

    Raises :class:`NotFoundError` if the development user does not exist.
    """

    if repo.get_user_by_id(db, dev_user_id) is None:
        raise NotFoundError(
            f"No user exists for X-Dev-User-ID {dev_user_id}. "
            "(X-Dev-User-ID is a development-only mechanism; see docs/api.md.)"
        )

    try:
        prompt = repo.add_prompt(
            db,
            user_id=dev_user_id,
            title=data.title,
            description=data.description,
            purpose=data.purpose,
            is_public=data.is_public,
        )
        repo.add_version(
            db,
            prompt_id=prompt.prompt_id,
            version_number=INITIAL_VERSION_NUMBER,
            content=data.content,
            created_by=dev_user_id,
            change_summary=INITIAL_CHANGE_SUMMARY,
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("create_prompt_with_initial_version failed; rolled back")
        raise

    # Reload with relationships for the response.
    created = repo.get_prompt_by_id(db, prompt.prompt_id)
    assert created is not None  # just committed
    return _to_prompt_read(created)


# --------------------------------------------------------------------------- #
# Queries                                                                    #
# --------------------------------------------------------------------------- #
def get_prompt(db: Session, prompt_id: uuid.UUID) -> PromptRead:
    prompt = repo.get_prompt_by_id(db, prompt_id)
    if prompt is None:
        raise NotFoundError(f"Prompt {prompt_id} not found.")
    return _to_prompt_read(prompt)


def list_prompts(
    db: Session,
    *,
    limit: int,
    offset: int,
    search: str | None = None,
    is_public: bool | None = None,
) -> PromptListResponse:
    rows, total = repo.list_prompts(
        db, limit=limit, offset=offset, search=search, is_public=is_public
    )
    items = [
        PromptListItem(
            prompt_id=row.Prompt.prompt_id,
            user_id=row.Prompt.user_id,
            title=row.Prompt.title,
            description=row.Prompt.description,
            purpose=row.Prompt.purpose,
            is_public=row.Prompt.is_public,
            created_at=row.Prompt.created_at,
            updated_at=row.Prompt.updated_at,
            latest_version_number=row.latest_version_number,
        )
        for row in rows
    ]
    return PromptListResponse(items=items, limit=limit, offset=offset, total=total)


def list_versions(db: Session, prompt_id: uuid.UUID) -> VersionListResponse:
    if not repo.prompt_exists(db, prompt_id):
        raise NotFoundError(f"Prompt {prompt_id} not found.")
    versions: Sequence[Version] = repo.list_versions_for_prompt(db, prompt_id)
    items = [VersionRead.model_validate(v) for v in versions]
    return VersionListResponse(items=items, total=len(items))
