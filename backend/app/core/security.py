"""Password hashing and JWT access tokens.

* Passwords: Argon2 via ``pwdlib`` (``PasswordHash.recommended()``). No
  plaintext is ever stored; only the ``$argon2id$…`` hash goes in
  ``users.password_hash``.
* Tokens: signed JWTs (``HS256`` by default) with the minimum claims
  ``sub`` (= ``user_id``), ``exp``, ``iat``.

The JWT secret comes only from configuration (``JWT_SECRET_KEY``). There is no
hard-coded fallback: :func:`_secret` raises a clear error if it is missing, so
the secret is never logged or embedded in code.
"""

from __future__ import annotations

import datetime as dt
import uuid

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

_password_hash = PasswordHash.recommended()

# Used to keep login timing similar whether or not the email exists (a minor
# anti-enumeration measure). It is a real Argon2 hash of a random value.
DUMMY_PASSWORD_HASH = _password_hash.hash(uuid.uuid4().hex)


class TokenError(Exception):
    """Raised when a token cannot be decoded/validated (expired, bad signature…)."""


def hash_password(plain_password: str) -> str:
    return _password_hash.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return _password_hash.verify(plain_password, password_hash)
    except Exception:
        # Malformed stored hash, etc. — treat as a failed verification.
        return False


def _secret() -> str:
    secret = get_settings().jwt_secret_key
    if not secret:
        raise RuntimeError(
            "JWT_SECRET_KEY is not configured. Set it in the environment "
            "(see .env.example). No insecure fallback secret is used."
        )
    return secret


def create_access_token(
    subject: str, *, expires_delta: dt.timedelta | None = None
) -> tuple[str, int]:
    """Return ``(token, expires_in_seconds)`` for ``sub = subject``."""

    settings = get_settings()
    delta = expires_delta or dt.timedelta(
        minutes=settings.access_token_expire_minutes
    )
    now = dt.datetime.now(dt.timezone.utc)
    expire = now + delta
    payload = {"sub": subject, "iat": now, "exp": expire}
    token = jwt.encode(payload, _secret(), algorithm=settings.jwt_algorithm)
    return token, int(delta.total_seconds())


def decode_access_token(token: str) -> dict:
    """Return the token's claims, or raise :class:`TokenError`."""

    settings = get_settings()
    try:
        return jwt.decode(
            token,
            _secret(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as exc:  # expired, bad signature, malformed, …
        raise TokenError(str(exc)) from exc
