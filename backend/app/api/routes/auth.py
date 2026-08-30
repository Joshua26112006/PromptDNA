"""Authentication endpoints: register, login, me.

Login uses the OAuth2 "password" flow: an
``application/x-www-form-urlencoded`` body with ``username`` (the email) and
``password``. This makes the Swagger "Authorize" button work out of the box.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.schemas.auth import RegisterRequest, TokenResponse, UserRead
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

DbDep = Annotated[Session, Depends(get_db)]


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={409: {"description": "Email already registered"}},
)
def register(payload: RegisterRequest, db: DbDep) -> UserRead:
    """Create an account. Password policy: 8–128 characters.

    The password is Argon2-hashed; only the hash is stored. Returns the safe
    profile (never the password or its hash). `409` if the email is taken.
    """

    return auth_service.register_user(db, payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and receive a JWT access token",
    responses={401: {"description": "Invalid email or password"}},
)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbDep
) -> TokenResponse:
    """Exchange credentials for a bearer access token.

    Send form fields `username` (your email) and `password`. On success returns
    `{access_token, token_type: "bearer", expires_in}`. Invalid credentials
    return `401` with a generic message.
    """

    return auth_service.authenticate(
        db, email=form_data.username, password=form_data.password
    )


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get the authenticated user's profile",
)
def me(current_user: CurrentUser) -> UserRead:
    return auth_service.to_user_read(current_user)
