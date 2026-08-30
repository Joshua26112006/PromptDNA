"""Prompt business logic + authorization.

Authorization rules (Phase 3) — all enforced here, never in routes:

* **Create**: any authenticated user; the caller becomes ``prompts.user_id``.
* **Read / list / versions**: a prompt is *visible* to a user iff the user
  owns it **or** ``is_public is True``.
* An inaccessible private prompt is reported as **404** (same message as a
  genuinely missing prompt) so a caller cannot probe for its existence.

Transaction boundary — :func:`create_prompt_with_initial_version`:

    BEGIN
        INSERT prompts
        INSERT versions (version_number = 1)
    COMMIT            -- both, or neither
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.api.errors import NotFoundError
from app.db.models import Prompt, User
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
# Authorization helpers                                                      #
# --------------------------------------------------------------------------- #
def _can_view(prompt: Prompt, user: User) -> bool:
    return prompt.user_id == user.user_id or prompt.is_public


def _load_viewable_prompt(
    db: Session, prompt_id: uuid.UUID, user: User
) -> Prompt:
    """Return the prompt if the user may view it, else raise 404.

    Missing prompt and access-denied private prompt return the SAME error so
    existence cannot be probed.
    """

    prompt = repo.get_prompt_by_id(db, prompt_id)
    if prompt is None or not _can_view(prompt, user):
        # Constant message: a denied private prompt is indistinguishable from a
        # missing one, so callers cannot probe for existence.
        raise NotFoundError("Prompt not found.")
    return prompt


# --------------------------------------------------------------------------- #
# Serialization                                                              #
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
    db: Session, *, current_user: User, data: PromptCreate
) -> PromptRead:
    """Create a prompt owned by ``current_user`` and its Version 1, atomically."""

    try:
        prompt = repo.add_prompt(
            db,
            user_id=current_user.user_id,
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
            created_by=current_user.user_id,
            change_summary=INITIAL_CHANGE_SUMMARY,
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("create_prompt_with_initial_version failed; rolled back")
        raise

    created = repo.get_prompt_by_id(db, prompt.prompt_id)
    assert created is not None  # just committed
    return _to_prompt_read(created)


# --------------------------------------------------------------------------- #
# Queries                                                                    #
# --------------------------------------------------------------------------- #
def get_prompt(
    db: Session, prompt_id: uuid.UUID, *, current_user: User
) -> PromptRead:
    return _to_prompt_read(_load_viewable_prompt(db, prompt_id, current_user))


def list_prompts(
    db: Session,
    *,
    current_user: User,
    limit: int,
    offset: int,
    search: str | None = None,
    is_public: bool | None = None,
) -> PromptListResponse:
    rows, total = repo.list_prompts(
        db,
        viewer_id=current_user.user_id,
        limit=limit,
        offset=offset,
        search=search,
        is_public=is_public,
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


def list_versions(
    db: Session, prompt_id: uuid.UUID, *, current_user: User
) -> VersionListResponse:
    _load_viewable_prompt(db, prompt_id, current_user)  # 404 if not viewable
    versions = repo.list_versions_for_prompt(db, prompt_id)
    items = [VersionRead.model_validate(v) for v in versions]
    return VersionListResponse(items=items, total=len(items))
