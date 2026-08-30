"""Prompt / Version request and response schemas.

Kept deliberately small and single-purpose. Field constraints here are input
*shape* validation only (lengths, ranges, non-empty); anything that needs a
database lookup or a rule lives in the service layer.

String length caps: ``title`` mirrors the DB column (``VARCHAR(200)``).
``description`` / ``purpose`` / ``content`` are ``TEXT`` in the database (no DB
limit); the caps below are sanity limits for an unauthenticated dev API.
"""

from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field

_TITLE_MAX = 200
_TEXT_MAX = 20_000
_CONTENT_MAX = 100_000


# --------------------------------------------------------------------------- #
# Requests                                                                   #
# --------------------------------------------------------------------------- #
class PromptCreate(BaseModel):
    """Body for ``POST /api/v1/prompts``.

    ``prompt_id`` / ``user_id`` / ``created_at`` / ``updated_at`` are NOT
    accepted from the client (``extra`` is forbidden). The owner is always the
    authenticated user from the ``Authorization: Bearer`` token.

    ``parent_prompt_id`` (optional) records lineage: the new prompt is a
    derivation / fork of an existing prompt the caller is allowed to VIEW. It
    does not transfer ownership — the new prompt is owned by the caller.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=_TITLE_MAX)
    content: str = Field(
        min_length=1,
        max_length=_CONTENT_MAX,
        description="Text of the prompt. Stored as this prompt's Version 1.",
    )
    description: str | None = Field(default=None, max_length=_TEXT_MAX)
    purpose: str | None = Field(default=None, max_length=_TEXT_MAX)
    is_public: bool = False
    parent_prompt_id: uuid.UUID | None = Field(
        default=None,
        description="Optional: UUID of a prompt the caller can view, recorded "
        "as this prompt's lineage parent. Ownership is not transferred.",
    )


class PromptUpdate(BaseModel):
    """Body for ``PATCH /api/v1/prompts/{id}`` — **metadata only**.

    Every field is optional; only the fields present in the request are
    changed. Version content, ``version_number``, ``created_by``, ownership and
    ``parent_prompt_id`` can never be modified here.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=_TITLE_MAX)
    description: str | None = Field(default=None, max_length=_TEXT_MAX)
    purpose: str | None = Field(default=None, max_length=_TEXT_MAX)
    is_public: bool | None = None


class VersionCreate(BaseModel):
    """Body for ``POST /api/v1/prompts/{id}/versions``.

    ``version_number``, ``created_by``, ``created_at`` are NOT accepted — the
    number is assigned by the server (current max + 1) and the creator is the
    authenticated user.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    content: str = Field(min_length=1, max_length=_CONTENT_MAX)
    change_summary: str | None = Field(default=None, max_length=_TEXT_MAX)


# --------------------------------------------------------------------------- #
# Responses                                                                  #
# --------------------------------------------------------------------------- #
class OwnerRead(BaseModel):
    """Minimal owner info for the UI. Never includes email or password_hash."""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    name: str


class VersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version_id: uuid.UUID
    prompt_id: uuid.UUID
    version_number: int
    content: str
    change_summary: str | None
    created_by: uuid.UUID
    created_at: datetime.datetime


class PromptRead(BaseModel):
    """Full prompt detail: the prompt, its owner, and all its versions."""

    model_config = ConfigDict(from_attributes=True)

    prompt_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None
    purpose: str | None
    is_public: bool
    parent_prompt_id: uuid.UUID | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    owner: OwnerRead
    versions: list[VersionRead]
    latest_version: VersionRead | None
    tags: list[str]


class PromptListItem(BaseModel):
    """One row in the paginated list. No nested version bodies."""

    model_config = ConfigDict(from_attributes=True)

    prompt_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None
    purpose: str | None
    is_public: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
    latest_version_number: int | None


class PromptListResponse(BaseModel):
    items: list[PromptListItem]
    limit: int
    offset: int
    total: int


class VersionListResponse(BaseModel):
    items: list[VersionRead]
    total: int
