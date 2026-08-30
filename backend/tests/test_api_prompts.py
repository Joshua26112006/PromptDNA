"""Prompt API tests (Phase 2 behavior, updated for Phase 3 auth).

Every prompt endpoint now requires ``Authorization: Bearer <token>``. Isolation
is unchanged: one rolled-back connection transaction per test; service commits
run via SAVEPOINT so nothing persists.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa

from app.db.models import Prompt, Version

BASE = "/api/v1/prompts"


def _payload(**over) -> dict:
    body = {
        "title": "Test Prompt",
        "content": "You are a helpful assistant.",
        "description": "A test prompt.",
        "purpose": "Testing.",
        "is_public": False,
    }
    body.update(over)
    return body


def _create(client, auth, **over):
    return client.post(BASE, json=_payload(**over), headers=auth.headers)


# --- health --------------------------------------------------------------- #
def test_health_ok(client):
    assert client.get("/health").json()["status"] == "ok"


def test_health_db_ok(client):
    r = client.get("/health/db")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "reachable"}


# --- create + initial version + atomicity ----------------------------- #
def test_create_prompt_returns_201_and_body(client, user_a):
    r = _create(client, user_a, title="My Prompt")
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "My Prompt"
    assert body["user_id"] == user_a.user_id           # owner = authenticated user
    assert body["owner"] == {"user_id": user_a.user_id, "name": user_a.name}
    assert "password_hash" not in r.text


def test_create_prompt_creates_version_1(client, user_a):
    body = _create(client, user_a, content="ABC123").json()
    assert [v["version_number"] for v in body["versions"]] == [1]
    assert body["versions"][0]["content"] == "ABC123"
    assert body["versions"][0]["change_summary"] == "Initial version."
    assert body["latest_version"]["version_number"] == 1


def test_create_prompt_persists_prompt_and_version_together(client, user_a, db_session):
    pid = uuid.UUID(_create(client, user_a).json()["prompt_id"])
    assert db_session.get(Prompt, pid) is not None
    assert db_session.scalar(
        sa.select(sa.func.count()).select_from(Version).where(Version.prompt_id == pid)
    ) == 1


# --- validation ---------------------------------------------------- #
@pytest.mark.parametrize(
    "bad", [{"title": ""}, {"content": ""}, {"content": "   "}, {"title": "x" * 201}]
)
def test_invalid_body_returns_422(client, user_a, bad):
    assert _create(client, user_a, **bad).status_code == 422


def test_missing_required_fields_returns_422(client, user_a):
    r = client.post(BASE, json={"title": "only title"}, headers=user_a.headers)
    assert r.status_code == 422


def test_ownership_fields_are_rejected(client, user_a):
    # user_id must never be accepted from the client.
    assert _create(client, user_a, user_id=str(uuid.uuid4())).status_code == 422
    assert _create(client, user_a, prompt_id=str(uuid.uuid4())).status_code == 422


# --- list + pagination ------------------------------------------- #
def test_list_returns_pagination_envelope(client, user_a):
    for i in range(3):
        _create(client, user_a, title=f"P{i}")
    body = client.get(BASE, params={"limit": 20, "offset": 0}, headers=user_a.headers).json()
    assert set(body) == {"items", "limit", "offset", "total"}
    assert body["total"] == 3 and body["limit"] == 20 and body["offset"] == 0
    assert body["items"][0]["latest_version_number"] == 1


def test_pagination_limit_and_offset(client, user_a):
    for i in range(5):
        _create(client, user_a, title=f"Page{i}")
    first = client.get(BASE, params={"limit": 2, "offset": 0}, headers=user_a.headers).json()
    second = client.get(BASE, params={"limit": 2, "offset": 2}, headers=user_a.headers).json()
    assert len(first["items"]) == 2 and len(second["items"]) == 2
    assert first["total"] == second["total"] == 5
    assert {i["prompt_id"] for i in first["items"]}.isdisjoint(
        {i["prompt_id"] for i in second["items"]}
    )


def test_list_search_is_lexical_substring(client, user_a):
    _create(client, user_a, title="Alpha Optimizer")
    _create(client, user_a, title="Beta Helper")
    body = client.get(BASE, params={"search": "optimizer"}, headers=user_a.headers).json()
    assert body["total"] == 1 and body["items"][0]["title"] == "Alpha Optimizer"


@pytest.mark.parametrize("bad", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_list_rejects_bad_pagination(client, user_a, bad):
    assert client.get(BASE, params=bad, headers=user_a.headers).status_code == 422


# --- get single ------------------------------------------------ #
def test_get_own_prompt(client, user_a):
    pid = _create(client, user_a, title="Fetch me").json()["prompt_id"]
    r = client.get(f"{BASE}/{pid}", headers=user_a.headers)
    assert r.status_code == 200 and r.json()["prompt_id"] == pid


def test_get_missing_prompt_returns_404(client, user_a):
    assert client.get(f"{BASE}/{uuid.uuid4()}", headers=user_a.headers).status_code == 404


def test_invalid_uuid_returns_422(client, user_a):
    assert client.get(f"{BASE}/not-a-uuid", headers=user_a.headers).status_code == 422
    assert client.get(f"{BASE}/123/versions", headers=user_a.headers).status_code == 422


# --- versions: read-only, immutable -------------------------- #
def test_list_versions_ordered_ascending(client, user_a):
    pid = _create(client, user_a).json()["prompt_id"]
    body = client.get(f"{BASE}/{pid}/versions", headers=user_a.headers).json()
    assert body["total"] == 1 and [v["version_number"] for v in body["items"]] == [1]


def test_list_versions_missing_prompt_returns_404(client, user_a):
    assert client.get(
        f"{BASE}/{uuid.uuid4()}/versions", headers=user_a.headers
    ).status_code == 404


def test_versions_have_no_write_endpoints(client, user_a):
    pid = _create(client, user_a).json()["prompt_id"]
    vid = client.get(f"{BASE}/{pid}/versions", headers=user_a.headers).json()["items"][0]["version_id"]
    assert client.put(f"{BASE}/{pid}/versions", headers=user_a.headers).status_code == 405
    assert client.patch(f"{BASE}/{pid}/versions/{vid}", headers=user_a.headers).status_code in (404, 405)
    assert client.delete(f"{BASE}/{pid}/versions/{vid}", headers=user_a.headers).status_code in (404, 405)


def test_existing_version_unchanged_after_rereads(client, user_a):
    body = _create(client, user_a, content="immutable text").json()
    pid, v1_id = body["prompt_id"], body["versions"][0]["version_id"]
    for _ in range(3):
        again = client.get(f"{BASE}/{pid}/versions", headers=user_a.headers).json()["items"][0]
        assert again["version_id"] == v1_id and again["content"] == "immutable text"


# --- transaction rollback (Phase 2 behavior preserved) ------ #
def test_failed_initial_version_rolls_back_prompt(client, user_a, db_session, monkeypatch):
    from app.services import prompt as prompt_service

    def _boom(*_a, **_kw):
        raise RuntimeError("simulated failure creating initial version")

    monkeypatch.setattr(prompt_service.repo, "add_version", _boom)

    before = db_session.scalar(sa.select(sa.func.count()).select_from(Prompt))
    r = _create(client, user_a, title="Should Not Persist")
    assert r.status_code == 500
    assert r.json() == {"detail": "Internal server error"}

    db_session.expire_all()
    assert db_session.scalar(sa.select(sa.func.count()).select_from(Prompt)) == before
    assert db_session.scalar(
        sa.select(sa.func.count()).select_from(Prompt).where(Prompt.title == "Should Not Persist")
    ) == 0


# --- OpenAPI / CORS ---------------------------------------- #
def test_openapi_and_docs_available(client):
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    for path in ("/api/v1/auth/register", "/api/v1/auth/login", "/api/v1/auth/me", BASE):
        assert path in schema["paths"]
    # No operation may still accept an X-Dev-User-ID parameter.
    for path_item in schema["paths"].values():
        for op in path_item.values():
            names = {p["name"].lower() for p in op.get("parameters", [])}
            assert "x-dev-user-id" not in names
    # The create-prompt body schema must document bearer-token ownership,
    # not the removed dev header.
    assert "x-dev-user-id" not in str(schema["components"]["schemas"]["PromptCreate"]).lower()


def test_cors_preflight_allows_configured_origin(client):
    r = client.options(
        BASE,
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"


# --- PATCH prompt metadata (Phase 4A) ---------------------------------- #
def test_patch_updates_metadata_only(client, user_a):
    body = _create(client, user_a, title="Before", is_public=False).json()
    pid = body["prompt_id"]
    v1_id = body["versions"][0]["version_id"]

    r = client.patch(
        f"{BASE}/{pid}",
        json={"title": "After", "purpose": "new purpose", "is_public": True},
        headers=user_a.headers,
    )
    assert r.status_code == 200
    patched = r.json()
    assert patched["title"] == "After"
    assert patched["purpose"] == "new purpose"
    assert patched["is_public"] is True
    # versions untouched
    assert len(patched["versions"]) == 1
    assert patched["versions"][0]["version_id"] == v1_id
    assert patched["versions"][0]["content"] == "You are a helpful assistant."


def test_patch_is_partial(client, user_a):
    pid = _create(client, user_a, title="Keep me", is_public=True).json()["prompt_id"]
    r = client.patch(f"{BASE}/{pid}", json={"is_public": False}, headers=user_a.headers)
    assert r.status_code == 200
    assert r.json()["title"] == "Keep me"        # unchanged
    assert r.json()["is_public"] is False


def test_patch_rejects_content_and_ownership_fields(client, user_a, user_b):
    pid = _create(client, user_a).json()["prompt_id"]
    for bad in ({"content": "x"}, {"user_id": user_b.user_id},
                {"version_number": 5}, {"parent_prompt_id": str(uuid.uuid4())},
                {"created_by": user_b.user_id}):
        r = client.patch(f"{BASE}/{pid}", json=bad, headers=user_a.headers)
        assert r.status_code == 422, bad


def test_patch_by_non_owner_public_is_403_private_is_404(client, user_a, user_b):
    pub = _create(client, user_a, is_public=True).json()["prompt_id"]
    priv = _create(client, user_a, is_public=False).json()["prompt_id"]
    assert client.patch(f"{BASE}/{pub}", json={"title": "x"},
                        headers=user_b.headers).status_code == 403
    assert client.patch(f"{BASE}/{priv}", json={"title": "x"},
                        headers=user_b.headers).status_code == 404


def test_patch_requires_auth(client, user_a):
    pid = _create(client, user_a).json()["prompt_id"]
    assert client.patch(f"{BASE}/{pid}", json={"title": "x"}).status_code == 401


def test_patch_missing_prompt_is_404(client, user_a):
    assert client.patch(
        f"{BASE}/{uuid.uuid4()}", json={"title": "x"}, headers=user_a.headers
    ).status_code == 404


def test_patch_empty_body_is_noop_200(client, user_a):
    pid = _create(client, user_a, title="Same").json()["prompt_id"]
    r = client.patch(f"{BASE}/{pid}", json={}, headers=user_a.headers)
    assert r.status_code == 200
    assert r.json()["title"] == "Same"


def test_patch_invalid_title_is_422(client, user_a):
    pid = _create(client, user_a).json()["prompt_id"]
    assert client.patch(f"{BASE}/{pid}", json={"title": ""},
                        headers=user_a.headers).status_code == 422
