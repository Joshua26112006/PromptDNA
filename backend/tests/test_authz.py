"""Authorization & ownership tests (Phase 3) — real PostgreSQL.

Covers mandated cases 14–25 including the explicit security-attack scenario
(User B must not reach User A's private prompt or bypass it via query params).
"""

from __future__ import annotations

import uuid

from app.db.models import Prompt

BASE = "/api/v1/prompts"


def _create(client, auth, *, title="P", is_public=False, content="c"):
    r = client.post(
        BASE,
        json={"title": title, "content": content, "is_public": is_public},
        headers=auth.headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


# --- 14 / 15  create + automatic ownership ---------------------------- #
def test_user_can_create_prompt_and_becomes_owner(client, user_a):
    body = _create(client, user_a, title="Mine")
    assert body["user_id"] == user_a.user_id
    assert body["owner"]["user_id"] == user_a.user_id


def test_client_cannot_set_a_different_owner(client, user_a, user_b):
    # Even if user_id is smuggled in the body it is rejected (extra=forbid);
    # ownership always comes from the token.
    r = client.post(
        BASE,
        json={"title": "x", "content": "y", "user_id": user_b.user_id},
        headers=user_a.headers,
    )
    assert r.status_code == 422


# --- 16 / 17  own prompts ---------------------------------------- #
def test_user_can_list_and_get_their_own_private_prompt(client, user_a):
    pid = _create(client, user_a, title="Private A", is_public=False)["prompt_id"]

    lst = client.get(BASE, headers=user_a.headers).json()
    assert pid in {i["prompt_id"] for i in lst["items"]}

    got = client.get(f"{BASE}/{pid}", headers=user_a.headers)
    assert got.status_code == 200 and got.json()["prompt_id"] == pid


# --- 18  another user's PUBLIC prompt is visible ---------------- #
def test_user_can_get_another_users_public_prompt(client, user_a, user_b):
    pid = _create(client, user_a, title="Public A", is_public=True)["prompt_id"]

    got = client.get(f"{BASE}/{pid}", headers=user_b.headers)
    assert got.status_code == 200

    lst = client.get(BASE, headers=user_b.headers).json()
    assert pid in {i["prompt_id"] for i in lst["items"]}


# --- 19 / 20  another user's PRIVATE prompt is 404 ------------- #
def test_user_cannot_get_another_users_private_prompt(client, user_a, user_b):
    pid = _create(client, user_a, title="Secret A", is_public=False)["prompt_id"]
    assert client.get(f"{BASE}/{pid}", headers=user_b.headers).status_code == 404


def test_user_cannot_list_another_users_private_prompt(client, user_a, user_b):
    pid = _create(client, user_a, title="Secret A", is_public=False)["prompt_id"]
    lst = client.get(BASE, headers=user_b.headers).json()
    assert pid not in {i["prompt_id"] for i in lst["items"]}
    assert lst["total"] == 0


def test_user_cannot_get_versions_of_another_users_private_prompt(client, user_a, user_b):
    pid = _create(client, user_a, title="Secret A", is_public=False)["prompt_id"]
    r = client.get(f"{BASE}/{pid}/versions", headers=user_b.headers)
    assert r.status_code == 404


def test_user_can_get_versions_of_another_users_public_prompt(client, user_a, user_b):
    pid = _create(client, user_a, title="Public A", is_public=True)["prompt_id"]
    r = client.get(f"{BASE}/{pid}/versions", headers=user_b.headers)
    assert r.status_code == 200 and r.json()["total"] == 1


# --- 21  query params cannot widen visibility ----------------- #
def test_is_public_false_filter_does_not_expose_others_private(client, user_a, user_b):
    priv_a = _create(client, user_a, title="Priv A", is_public=False)["prompt_id"]
    priv_b = _create(client, user_b, title="Priv B", is_public=False)["prompt_id"]

    # B asks for "private" prompts — must see only their own.
    body = client.get(f"{BASE}?is_public=false", headers=user_b.headers).json()
    ids = {i["prompt_id"] for i in body["items"]}
    assert priv_a not in ids
    assert ids == {priv_b}


def test_search_cannot_surface_others_private_prompt(client, user_a, user_b):
    _create(client, user_a, title="UniqueNeedle Private", is_public=False)
    body = client.get(f"{BASE}?search=UniqueNeedle", headers=user_b.headers).json()
    assert body["total"] == 0


# --- SECURITY: explicit attack scenario --------------------- #
def test_security_user_b_cannot_probe_user_a_private_prompt_by_uuid(client, user_a, user_b):
    """User A makes a private prompt; User B has its UUID and tries every route."""

    pid = _create(client, user_a, title="Confidential", is_public=False)["prompt_id"]

    assert client.get(f"{BASE}/{pid}", headers=user_b.headers).status_code == 404
    assert client.get(f"{BASE}/{pid}/versions", headers=user_b.headers).status_code == 404
    # query-parameter manipulation must not help
    assert client.get(f"{BASE}/{pid}?is_public=true", headers=user_b.headers).status_code == 404
    assert client.get(f"{BASE}?is_public=false&limit=100", headers=user_b.headers).json()["total"] == 0

    # ...and a genuinely missing id looks identical (no existence oracle).
    missing = client.get(f"{BASE}/{uuid.uuid4()}", headers=user_b.headers)
    real = client.get(f"{BASE}/{pid}", headers=user_b.headers)
    assert missing.status_code == real.status_code == 404
    assert missing.json() == real.json()


# --- 24 / 25  X-Dev-User-ID removed; token required -------- #
def test_x_dev_user_id_is_not_accepted_as_auth(client, db_session, user_a):
    import sqlalchemy as sa

    before = db_session.scalar(sa.select(sa.func.count()).select_from(Prompt))
    r = client.post(
        BASE,
        json={"title": "via dev header", "content": "x"},
        headers={"X-Dev-User-ID": user_a.user_id},   # no Bearer token
    )
    assert r.status_code == 401
    db_session.expire_all()
    assert db_session.scalar(sa.select(sa.func.count()).select_from(Prompt)) == before


def test_all_prompt_endpoints_require_bearer_token(client):
    assert client.get(BASE).status_code == 401
    assert client.post(BASE, json={"title": "t", "content": "c"}).status_code == 401
    assert client.get(f"{BASE}/{uuid.uuid4()}").status_code == 401
    assert client.get(f"{BASE}/{uuid.uuid4()}/versions").status_code == 401


# --- 22 / 23  transaction still atomic under auth --------- #
def test_create_still_makes_version_1_atomically(client, user_a, db_session):
    import sqlalchemy as sa

    from app.db.models import Version

    pid = uuid.UUID(_create(client, user_a, title="Atomic")["prompt_id"])
    assert db_session.get(Prompt, pid) is not None
    assert db_session.scalar(
        sa.select(sa.func.count()).select_from(Version).where(Version.prompt_id == pid)
    ) == 1


def test_rollback_still_works_under_auth(client, user_a, db_session, monkeypatch):
    import sqlalchemy as sa

    from app.services import prompt as prompt_service

    monkeypatch.setattr(
        prompt_service.repo, "add_version",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    before = db_session.scalar(sa.select(sa.func.count()).select_from(Prompt))
    r = client.post(BASE, json={"title": "nope", "content": "x"}, headers=user_a.headers)
    assert r.status_code == 500
    db_session.expire_all()
    assert db_session.scalar(sa.select(sa.func.count()).select_from(Prompt)) == before
