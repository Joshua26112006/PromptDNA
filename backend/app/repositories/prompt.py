"""Data access for prompts, versions, and the user-existence check.

Functions take the :class:`~sqlalchemy.orm.Session` as their first argument,
mutate it (``add`` / ``flush``) or query it, and return ORM objects or rows.
They never ``commit`` or ``rollback``.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import Row, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Prompt, User, Version


def _escape_like(term: str) -> str:
    """Escape LIKE/ILIKE wildcards so a search term is treated literally."""

    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# --------------------------------------------------------------------------- #
# Users                                                                      #
# --------------------------------------------------------------------------- #
def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


# --------------------------------------------------------------------------- #
# Prompts                                                                    #
# --------------------------------------------------------------------------- #
def add_prompt(
    db: Session,
    *,
    user_id: uuid.UUID,
    title: str,
    description: str | None,
    purpose: str | None,
    is_public: bool,
) -> Prompt:
    prompt = Prompt(
        user_id=user_id,
        title=title,
        description=description,
        purpose=purpose,
        is_public=is_public,
    )
    db.add(prompt)
    db.flush()  # assign prompt_id without committing
    return prompt


def get_prompt_by_id(db: Session, prompt_id: uuid.UUID) -> Prompt | None:
    stmt = (
        select(Prompt)
        .where(Prompt.prompt_id == prompt_id)
        .options(
            selectinload(Prompt.owner),
            selectinload(Prompt.versions),
            selectinload(Prompt.tags),
        )
    )
    return db.scalars(stmt).one_or_none()


def prompt_exists(db: Session, prompt_id: uuid.UUID) -> bool:
    stmt = select(Prompt.prompt_id).where(Prompt.prompt_id == prompt_id).limit(1)
    return db.scalar(stmt) is not None


def list_prompts(
    db: Session,
    *,
    limit: int,
    offset: int,
    search: str | None = None,
    is_public: bool | None = None,
) -> tuple[Sequence[Row], int]:
    """Return ``(rows, total)``.

    Each row exposes ``.Prompt`` and ``.latest_version_number`` (may be ``None``
    for a prompt that somehow has no version). ``total`` is the count under the
    same filters, for pagination metadata.
    """

    filters = []
    if search:
        filters.append(Prompt.title.ilike(f"%{_escape_like(search)}%", escape="\\"))
    if is_public is not None:
        filters.append(Prompt.is_public.is_(is_public))

    latest = func.max(Version.version_number).label("latest_version_number")
    stmt = (
        select(Prompt, latest)
        .outerjoin(Version, Version.prompt_id == Prompt.prompt_id)
        .group_by(Prompt.prompt_id)
        .order_by(Prompt.created_at.desc(), Prompt.prompt_id)
        .limit(limit)
        .offset(offset)
    )
    count_stmt = select(func.count()).select_from(Prompt)
    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    rows = db.execute(stmt).all()
    total = db.scalar(count_stmt) or 0
    return rows, total


# --------------------------------------------------------------------------- #
# Versions                                                                   #
# --------------------------------------------------------------------------- #
def add_version(
    db: Session,
    *,
    prompt_id: uuid.UUID,
    version_number: int,
    content: str,
    created_by: uuid.UUID,
    change_summary: str | None,
) -> Version:
    version = Version(
        prompt_id=prompt_id,
        version_number=version_number,
        content=content,
        created_by=created_by,
        change_summary=change_summary,
    )
    db.add(version)
    db.flush()
    return version


def list_versions_for_prompt(
    db: Session, prompt_id: uuid.UUID
) -> Sequence[Version]:
    stmt = (
        select(Version)
        .where(Version.prompt_id == prompt_id)
        .order_by(Version.version_number.asc())
    )
    return db.scalars(stmt).all()
