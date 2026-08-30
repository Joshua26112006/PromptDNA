"""Authentication tests (Phase 3) — real PostgreSQL.

Covers the 13 mandated AUTHENTICATION cases + the password-hash-storage check.
"""

from __future__ import annotations

import datetime as dt
import uuid

import jwt
import pytest
import sqlalchemy as sa

from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.models import User
from tests.conftest import DEFAULT_PASSWORD, register_and_login

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"


def _reg_body(**over) -> dict:
    body = {"name": "Alice", "email": f"a-{uuid.uuid4().hex[:10]}@example.com",
            "password": DEFAULT_PASSWORD}
    body.update(over)
    return body


# --- 1 / 2 / 3  registration + hashing + no plaintext ------------------- #
def test_registration_succeeds_and_returns_safe_profile(client):
    body = _reg_body(name="Alice")
    r = client.post(REGISTER, json=body)
    assert r.status_code == 201
    data = r.json()
    assert set(data) == {"user_id", "name", "email", "created_at"}
    assert data["email"] == body["email"]
    assert "password" not in r.text and "password_hash" not in r.text


def test_registration_hashes_password_and_never_stores_plaintext(client, db_session):
    body = _reg_body(password="s3cretpassword")
    client.post(REGISTER, json=body)

    row = db_session.execute(
        sa.select(User.password_hash).where(User.email == body["email"].lower())
    ).scalar_one()

    assert row != "s3cretpassword"          # not the plaintext
    assert "s3cretpassword" not in row      # plaintext not embedded
    assert row.startswith("$argon2")        # a real Argon2 hash
    # verify the hash actually validates the original password
    from app.core.security import verify_password

    assert verify_password("s3cretpassword", row) is True
    assert verify_password("wrong", row) is False


def test_email_is_normalized_lowercase(client, db_session):
    body = _reg_body(email=f"MixedCase-{uuid.uuid4().hex[:6]}@Example.COM")
    client.post(REGISTER, json=body)
    stored = db_session.execute(sa.select(User.email)).scalars().all()
    assert body["email"].lower() in stored


# --- 4  duplicate email -> 409 -------------------------------------- #
def test_duplicate_email_returns_409(client):
    body = _reg_body()
    assert client.post(REGISTER, json=body).status_code == 201
    dup = client.post(REGISTER, json={**body, "name": "Someone Else"})
    assert dup.status_code == 409
    assert "exists" in dup.json()["detail"].lower()


def test_duplicate_email_is_case_insensitive(client):
    body = _reg_body(email=f"Dup-{uuid.uuid4().hex[:6]}@Example.com")
    assert client.post(REGISTER, json=body).status_code == 201
    dup = client.post(REGISTER, json={**body, "email": body["email"].upper()})
    assert dup.status_code == 409


# --- 5  invalid registration -> 422 ------------------------------ #
@pytest.mark.parametrize(
    "bad",
    [
        {"password": "short"},          # < 8 chars
        {"email": "not-an-email"},
        {"name": ""},
        {"email": ""},
    ],
)
def test_invalid_registration_returns_422(client, bad):
    assert client.post(REGISTER, json=_reg_body(**bad)).status_code == 422


def test_registration_rejects_unexpected_fields(client):
    assert client.post(
        REGISTER, json={**_reg_body(), "user_id": str(uuid.uuid4())}
    ).status_code == 422


# --- 6 / 7 / 8  login outcomes ------------------------------- #
def test_login_succeeds_with_correct_credentials(client):
    body = _reg_body()
    client.post(REGISTER, json=body)
    r = client.post(LOGIN, data={"username": body["email"], "password": body["password"]})
    assert r.status_code == 200
    tok = r.json()
    assert tok["token_type"] == "bearer"
    assert tok["access_token"] and tok["expires_in"] > 0


def test_login_fails_with_wrong_password(client):
    body = _reg_body()
    client.post(REGISTER, json=body)
    r = client.post(LOGIN, data={"username": body["email"], "password": "wrongpassword"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid email or password."


def test_login_fails_with_unknown_email(client):
    r = client.post(LOGIN, data={"username": "nobody@example.com", "password": DEFAULT_PASSWORD})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid email or password."


# --- 9  JWT identity + expiration --------------------------- #
def test_jwt_contains_expected_identity_and_expiration(client):
    au = register_and_login(client)
    settings = get_settings()
    claims = jwt.decode(au.token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

    assert claims["sub"] == au.user_id
    assert set(claims) <= {"sub", "iat", "exp"}          # minimal claims only
    assert "email" not in claims and "password" not in claims and "password_hash" not in claims
    ttl = claims["exp"] - claims["iat"]
    assert ttl == settings.access_token_expire_minutes * 60


# --- 10 / 11 / 12 / 13  /auth/me + token validation ------ #
def test_valid_token_authenticates_me(client):
    au = register_and_login(client, name="Meep")
    r = client.get(ME, headers=au.headers)
    assert r.status_code == 200
    assert r.json()["user_id"] == au.user_id
    assert r.json()["name"] == "Meep"
    assert "password_hash" not in r.text


def test_me_without_token_returns_401(client):
    r = client.get(ME)
    assert r.status_code == 401
    assert r.headers.get("www-authenticate") == "Bearer"


@pytest.mark.parametrize(
    "header",
    ["Bearer not.a.jwt", "Bearer ", "Token abc", "garbage"],
)
def test_me_with_malformed_token_returns_401(client, header):
    assert client.get(ME, headers={"Authorization": header}).status_code == 401


def test_me_with_token_signed_by_wrong_secret_returns_401(client):
    au = register_and_login(client)
    forged = jwt.encode(
        {"sub": au.user_id, "iat": 0, "exp": 9999999999},
        "a-different-secret-of-adequate-length-0123456789",
        algorithm="HS256",
    )
    assert client.get(ME, headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_me_with_expired_token_returns_401(client):
    au = register_and_login(client)
    token, _ = create_access_token(au.user_id, expires_delta=dt.timedelta(seconds=-5))
    r = client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_me_with_token_for_deleted_user_returns_401(client, db_session):
    au = register_and_login(client)
    db_session.execute(sa.delete(User).where(User.user_id == uuid.UUID(au.user_id)))
    db_session.commit()
    assert client.get(ME, headers=au.headers).status_code == 401
