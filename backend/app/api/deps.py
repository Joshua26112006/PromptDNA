"""Shared FastAPI dependencies for the API layer.

Phase 3: the Phase 2 ``X-Dev-User-ID`` mechanism is **removed**. Authenticated
endpoints require ``Authorization: Bearer <token>`` and resolve the caller via
:func:`get_current_user`.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.api.errors import UnauthorizedError
from app.core.config import get_settings
from app.core.security import TokenError, decode_access_token
from app.db.models import User
from app.db.session import get_db
from app.repositories import user as user_repo

# tokenUrl powers the Swagger "Authorize" dialog; it points at the login route.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{get_settings().api_v1_prefix}/auth/login", auto_error=False
)


def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Resolve the authenticated user from a Bearer access token.

    401 for a missing / malformed / invalid / expired token, or a token whose
    ``sub`` does not resolve to an existing user.
    """

    if not token:
        raise UnauthorizedError("Not authenticated.")

    try:
        claims = decode_access_token(token)
    except TokenError:
        raise UnauthorizedError("Could not validate credentials.") from None

    subject = claims.get("sub")
    try:
        user_id = uuid.UUID(str(subject))
    except (ValueError, TypeError):
        raise UnauthorizedError("Could not validate credentials.") from None

    user = user_repo.get_by_id(db, user_id)
    if user is None:
        raise UnauthorizedError("Could not validate credentials.") from None
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
