"""Authentication business logic: registration and login.

Authentication ("who is this user?") lives here. Authorization ("what may they
access?") lives in ``app/services/prompt.py``. They are deliberately separate.
"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.errors import ConflictError, UnauthorizedError
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.models import User
from app.repositories import user as user_repo
from app.schemas.auth import RegisterRequest, TokenResponse, UserRead

logger = logging.getLogger("promptdna")

# Same generic message for every failure mode — never reveal which of email or
# password was wrong, or whether the account exists.
INVALID_CREDENTIALS = "Invalid email or password."


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def register_user(db: Session, data: RegisterRequest) -> UserRead:
    email = _normalize_email(data.email)

    if user_repo.get_by_email(db, email) is not None:
        raise ConflictError("An account with this email already exists.")

    try:
        user = user_repo.add_user(
            db,
            name=data.name,
            email=email,
            password_hash=hash_password(data.password),
        )
        db.commit()
    except IntegrityError:
        # Lost the race against a concurrent registration with the same email.
        db.rollback()
        raise ConflictError("An account with this email already exists.") from None
    except Exception:
        db.rollback()
        logger.exception("register_user failed; rolled back")
        raise

    db.refresh(user)
    return UserRead.model_validate(user)


def authenticate(db: Session, *, email: str, password: str) -> TokenResponse:
    user = user_repo.get_by_email(db, _normalize_email(email))

    if user is None:
        # Spend similar time as a real verification to blunt user enumeration.
        verify_password(password, DUMMY_PASSWORD_HASH)
        raise UnauthorizedError(INVALID_CREDENTIALS)

    if not verify_password(password, user.password_hash):
        raise UnauthorizedError(INVALID_CREDENTIALS)

    token, expires_in = create_access_token(str(user.user_id))
    return TokenResponse(access_token=token, expires_in=expires_in)


def to_user_read(user: User) -> UserRead:
    return UserRead.model_validate(user)
