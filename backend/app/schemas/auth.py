"""Authentication request/response schemas.

Password policy (documented in docs/api.md): 8–128 characters, no other
composition rules. Email is validated with ``EmailStr`` and normalised
(trimmed + lower-cased) by the service before storage/lookup.
"""

from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

_NAME_MAX = 100
_PASSWORD_MIN = 8
_PASSWORD_MAX = 128


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=_NAME_MAX)
    email: EmailStr
    password: str = Field(min_length=_PASSWORD_MIN, max_length=_PASSWORD_MAX)


class UserRead(BaseModel):
    """Safe user profile. Never contains password / password_hash."""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    name: str
    email: EmailStr
    created_at: datetime.datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until the access token expires
