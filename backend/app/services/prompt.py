"""Prompt & version business logic + authorization.

Prompt vs. version
------------------
A ``prompts`` row is the logical container (title/description/purpose/lineage/
visibility). The prompt text lives in ``versions.content``. Versions are
**immutable**: "editing a prompt's content" means inserting a new version, never
updating an existing one. There is no update/delete path for versions.

Authorization (all enforced here, never in routes)
--------------------------------------------------
* ``_can_view``   : owner OR ``is_public``.
* Read / list / version-history / single-version: not viewable → **404**
  (same body as a missing prompt, so existence cannot be probed).
* Create version / PATCH metadata: **owner only**. A non-owner who *can* view a
  public prompt gets **403** (existence is already public); otherwise **404**.

Transactions (service owns the boundary; repositories never commit)
------------------------------------------------------------------
* create prompt        : INSERT prompt + INSERT version 1  → one commit
* create version       : SELECT max(version_number) → INSERT version → commit,
                         with a bounded retry on the UNIQUE(prompt_id,
                         version_number) race, then 409.
* PATCH metadata        : UPDATE prompts (metadata columns only) → commit
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.errors import ConflictError, ForbiddenError, NotFoundError
from app.db.models import Prompt, User
from app.repositories import prompt as repo
from app.schemas.prompt import (
    OwnerRead,
    PromptCreate,
    PromptListItem,
    PromptListResponse,
    PromptRead,
    PromptUpdate,
    VersionCreate,
    VersionListResponse,
    VersionRead,
)

logger = logging.getLogger("promptdna")

INITIAL_VERSION_NUMBER = 1
INITIAL_CHANGE_SUMMARY = "Initial version."
VERSION_NUMBER_MAX_RETRIES = 5


def _try_autoembed_version(db: Session, version_id: uuid.UUID) -> None:
    """Best-effort embed after a version is committed. No-op unless
    EMBEDDING_AUTOGENERATE is on; never raises (see services/embedding.py)."""

    from app.services.embedding import try_autogenerate

    try_autogenerate(db, version_id)


def _project_to_graph(prompt: Prompt) -> None:
    """Best-effort Neo4j projection AFTER the PostgreSQL commit. No-op unless
    NEO4J_ENABLED; never raises — PostgreSQL is authoritative and is never
    rolled back for Neo4j (eventual consistency; reconcile via
    scripts/sync_neo4j.py)."""

    from app.services.graph import project_prompt_after_commit

    project_prompt_after_commit(
        prompt.prompt_id, prompt.title, prompt.parent_prompt_id
    )


def _try_autoembed(db: Session, prompt_id: uuid.UUID) -> None:
    v = repo.list_versions_for_prompt(db, prompt_id)
    if v:
        _try_autoembed_version(db, v[0].version_id)


# --------------------------------------------------------------------------- #
# Authorization helpers                                                      #
# --------------------------------------------------------------------------- #
def _can_view(prompt: Prompt, user: User) -> bool:
    return prompt.user_id == user.user_id or prompt.is_public


def _load_viewable_prompt(db: Session, prompt_id: uuid.UUID, user: User) -> Prompt:
    prompt = repo.get_prompt_by_id(db, prompt_id)
    if prompt is None or not _can_view(prompt, user):
        raise NotFoundError("Prompt not found.")
    return prompt


def _load_owned_prompt(db: Session, prompt_id: uuid.UUID, user: User) -> Prompt:
    """Return the prompt only if ``user`` owns it.

    Public prompt owned by someone else → 403 (its existence is already public).
    Private prompt owned by someone else, or missing → 404 (no existence leak).
    """

    prompt = repo.get_prompt_by_id(db, prompt_id)
    if prompt is None:
        raise NotFoundError("Prompt not found.")
    if prompt.user_id == user.user_id:
        return prompt
    if prompt.is_public:
        raise ForbiddenError("Only the prompt owner can perform this action.")
    raise NotFoundError("Prompt not found.")


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
    """Create a prompt owned by ``current_user`` and its Version 1, atomically.

    If ``data.parent_prompt_id`` is set it must reference a prompt the caller
    can VIEW (lineage / fork). Ownership is not transferred — the new prompt is
    owned by ``current_user``.
    """

    if data.parent_prompt_id is not None:
        parent = repo.get_prompt_by_id(db, data.parent_prompt_id)
        if parent is None or not _can_view(parent, current_user):
            raise NotFoundError("Parent prompt not found or not accessible.")

    try:
        prompt = repo.add_prompt(
            db,
            user_id=current_user.user_id,
            title=data.title,
            description=data.description,
            purpose=data.purpose,
            is_public=data.is_public,
            parent_prompt_id=data.parent_prompt_id,
        )
        # Defensive: a prompt can never be its own lineage parent. Unreachable
        # via the API (the client cannot know the new prompt_id) but cheap.
        if prompt.prompt_id == data.parent_prompt_id:
            raise ForbiddenError("A prompt cannot be its own parent.")
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

    _try_autoembed(db, prompt.prompt_id)

    created = repo.get_prompt_by_id(db, prompt.prompt_id)
    assert created is not None  # just committed
    _project_to_graph(created)
    return _to_prompt_read(created)


def create_version(
    db: Session,
    prompt_id: uuid.UUID,
    *,
    current_user: User,
    data: VersionCreate,
) -> VersionRead:
    """Append a new immutable version to a prompt the caller **owns**.

    ``version_number`` = current max + 1, read fresh from the database. On the
    ``UNIQUE(prompt_id, version_number)`` race the insert is retried a bounded
    number of times with a recomputed number; if it still cannot be placed a
    ``409`` is returned. Existing versions are never touched.
    """

    _load_owned_prompt(db, prompt_id, current_user)  # 403 / 404 as appropriate

    for attempt in range(1, VERSION_NUMBER_MAX_RETRIES + 1):
        next_number = (repo.get_max_version_number(db, prompt_id) or 0) + 1
        try:
            version = repo.add_version(
                db,
                prompt_id=prompt_id,
                version_number=next_number,
                content=data.content,
                created_by=current_user.user_id,
                change_summary=data.change_summary,
            )
            db.commit()
        except IntegrityError:
            db.rollback()
            if attempt == VERSION_NUMBER_MAX_RETRIES:
                logger.warning(
                    "version-number contention on prompt %s: gave up after %d tries",
                    prompt_id, attempt,
                )
                raise ConflictError(
                    "Could not allocate a version number due to concurrent "
                    "writes. Please retry."
                ) from None
            continue
        except Exception:
            db.rollback()
            logger.exception("create_version failed; rolled back")
            raise
        db.refresh(version)
        _try_autoembed_version(db, version.version_id)
        return VersionRead.model_validate(version)

    raise AssertionError("unreachable")  # pragma: no cover


def update_prompt_metadata(
    db: Session,
    prompt_id: uuid.UUID,
    *,
    current_user: User,
    data: PromptUpdate,
) -> PromptRead:
    """Update prompt **metadata only** (title/description/purpose/is_public).

    Owner only. Never touches versions, ``version_number``, ``created_by``,
    ownership, or ``parent_prompt_id``.
    """

    prompt = _load_owned_prompt(db, prompt_id, current_user)
    changes = data.model_dump(exclude_unset=True)

    if changes:
        try:
            repo.update_prompt(db, prompt, **changes)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("update_prompt_metadata failed; rolled back")
            raise

    refreshed = repo.get_prompt_by_id(db, prompt_id)
    assert refreshed is not None
    _project_to_graph(refreshed)  # e.g. title change -> update the node
    return _to_prompt_read(refreshed)


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


def get_version(
    db: Session,
    prompt_id: uuid.UUID,
    version_id: uuid.UUID,
    *,
    current_user: User,
) -> VersionRead:
    """Return one version, verifying it belongs to ``prompt_id`` and the caller
    can view that prompt. Any mismatch → 404 (no existence leak)."""

    _load_viewable_prompt(db, prompt_id, current_user)  # 404 if not viewable

    version = repo.get_version_by_id(db, version_id)
    if version is None or version.prompt_id != prompt_id:
        raise NotFoundError("Version not found.")
    return VersionRead.model_validate(version)
