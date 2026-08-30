"""Shared FastAPI dependencies for the API layer."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Header

from app.api.errors import BadRequestError

# NOTE: development-only. `X-Dev-User-ID` is NOT authentication. It simply names
# which existing user owns a created prompt while there is no auth. It will be
# removed when real authentication lands. See docs/api.md.
DEV_USER_HEADER_DESCRIPTION = (
    "**Development only.** UUID of an existing `users.user_id` that will own "
    "the created prompt. This is NOT authentication and will be replaced by a "
    "real auth mechanism in a later phase."
)


def get_dev_user_id(
    x_dev_user_id: Annotated[
        str | None, Header(description=DEV_USER_HEADER_DESCRIPTION)
    ] = None,
) -> uuid.UUID:
    if x_dev_user_id is None:
        raise BadRequestError(
            "Missing 'X-Dev-User-ID' header. This development-only header must "
            "carry the UUID of an existing user (auth is not implemented yet)."
        )
    try:
        return uuid.UUID(x_dev_user_id)
    except ValueError as exc:
        raise BadRequestError("'X-Dev-User-ID' must be a valid UUID.") from exc
