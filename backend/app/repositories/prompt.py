"""Data access for prompts and versions.

Functions take the :class:`~sqlalchemy.orm.Session` as their first argument,
mutate it (``add`` / ``flush``) or query it, and return ORM objects or rows.
They never ``commit`` or ``rollback``.

Authorization note: :func:`list_prompts` applies the visibility predicate
(``owner OR public``) itself and combines it with user filters using ``AND``,
so no query parameter can widen what a viewer sees.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import Row, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Prompt, Version


def _escape_like(term: str) -> str:
    """Escape LIKE/ILIKE wildcards so a search term is treated literally."""

    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


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
    parent_prompt_id: uuid.UUID | None = None,
) -> Prompt:
    prompt = Prompt(
        user_id=user_id,
        title=title,
        description=description,
        purpose=purpose,
        is_public=is_public,
        parent_prompt_id=parent_prompt_id,
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


def update_prompt(db: Session, prompt: Prompt, **fields: object) -> Prompt:
    """Apply metadata changes to an already-loaded prompt (no commit)."""

    for key, value in fields.items():
        setattr(prompt, key, value)
    db.flush()
    return prompt


def list_prompts(
    db: Session,
    *,
    viewer_id: uuid.UUID,
    limit: int,
    offset: int,
    search: str | None = None,
    is_public: bool | None = None,
) -> tuple[Sequence[Row], int]:
    """Return ``(rows, total)`` for prompts **visible to ``viewer_id``**.

    Visible = owned by the viewer OR ``is_public = true``. Optional ``search``
    (title substring) and ``is_public`` filters are ANDed on top and can only
    narrow the result. Each row exposes ``.Prompt`` and
    ``.latest_version_number``.
    """

    visibility = or_(Prompt.user_id == viewer_id, Prompt.is_public.is_(True))

    filters = [visibility]
    if search:
        filters.append(
            Prompt.title.ilike(f"%{_escape_like(search)}%", escape="\\")
        )
    if is_public is not None:
        filters.append(Prompt.is_public.is_(is_public))

    latest = func.max(Version.version_number).label("latest_version_number")
    stmt = (
        select(Prompt, latest)
        .outerjoin(Version, Version.prompt_id == Prompt.prompt_id)
        .where(*filters)
        .group_by(Prompt.prompt_id)
        .order_by(Prompt.created_at.desc(), Prompt.prompt_id)
        .limit(limit)
        .offset(offset)
    )
    count_stmt = select(func.count()).select_from(Prompt).where(*filters)

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


def get_version_by_id(db: Session, version_id: uuid.UUID) -> Version | None:
    return db.get(Version, version_id)


def get_max_version_number(db: Session, prompt_id: uuid.UUID) -> int | None:
    """Highest ``version_number`` for the prompt, or ``None`` if it has none.

    Read fresh from the database on every call — the caller must not cache it,
    because a concurrent writer may have advanced it. The
    ``UNIQUE (prompt_id, version_number)`` constraint is the final guard.
    """

    return db.scalar(
        select(func.max(Version.version_number)).where(
            Version.prompt_id == prompt_id
        )
    )
