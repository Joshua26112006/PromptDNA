"""Phase 2 API integration tests — real PostgreSQL, no SQLite.

Isolation: every test runs inside one connection-level transaction that is
rolled back at teardown (see conftest `txn_connection` / `client` / `db_session`).
Service-layer ``commit()`` calls are still exercised (via SAVEPOINT) but nothing
is written to the test database permanently.
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


def _create(client, dev_user, **over):
    return client.post(
        BASE, json=_payload(**over), headers={"X-Dev-User-ID": str(dev_user.user_id)}
    )


# --- 1 / 2  health ---------------------------------------------------------- #
def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_db_ok(client):
    r = client.get("/health/db")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "reachable"}


# --- 3 / 4 / 5  create + initial version + atomicity ---------------------- #
def test_create_prompt_returns_201_and_body(client, dev_user):
    r = _create(client, dev_user, title="My Prompt")
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "My Prompt"
    assert body["user_id"] == str(dev_user.user_id)
    assert body["owner"] == {"user_id": str(dev_user.user_id), "name": dev_user.name}
    assert "password_hash" not in r.text


def test_create_prompt_creates_version_1(client, dev_user):
    body = _create(client, dev_user, content="ABC123").json()
    assert len(body["versions"]) == 1
    v1 = body["versions"][0]
    assert v1["version_number"] == 1
    assert v1["content"] == "ABC123"
    assert v1["change_summary"] == "Initial version."
    assert body["latest_version"]["version_number"] == 1


def test_create_prompt_persists_prompt_and_version_together(client, dev_user, db_session):
    pid = uuid.UUID(_create(client, dev_user).json()["prompt_id"])
    prompt = db_session.get(Prompt, pid)
    assert prompt is not None
    vcount = db_session.scalar(
        sa.select(sa.func.count()).select_from(Version).where(Version.prompt_id == pid)
    )
    assert vcount == 1


# --- 6  missing / unknown dev user -------------------------------------- #
def test_unknown_dev_user_returns_404(client):
    r = client.post(
        BASE,
        json=_payload(),
        headers={"X-Dev-User-ID": "11111111-1111-1111-1111-111111111111"},
    )
    assert r.status_code == 404


def test_missing_dev_user_header_returns_400(client):
    r = client.post(BASE, json=_payload())
    assert r.status_code == 400
    assert "X-Dev-User-ID" in r.json()["detail"]


def test_malformed_dev_user_header_returns_400(client):
    r = client.post(BASE, json=_payload(), headers={"X-Dev-User-ID": "nope"})
    assert r.status_code == 400


# --- 7  validation ---------------------------------------------------- #
@pytest.mark.parametrize(
    "bad",
    [
        {"title": ""},
        {"content": ""},
        {"content": "   "},
        {"title": "x" * 201},
    ],
)
def test_invalid_body_returns_422(client, dev_user, bad):
    r = _create(client, dev_user, **bad)
    assert r.status_code == 422


def test_missing_required_fields_returns_422(client, dev_user):
    r = client.post(
        BASE, json={"title": "only title"},
        headers={"X-Dev-User-ID": str(dev_user.user_id)},
    )
    assert r.status_code == 422


def test_unexpected_field_is_rejected(client, dev_user):
    # user_id / prompt_id etc. must not be accepted from the client.
    r = _create(client, dev_user, user_id=str(uuid.uuid4()))
    assert r.status_code == 422


# --- 8 / 9  list + pagination ---------------------------------------- #
def test_list_returns_pagination_envelope(client, dev_user):
    for i in range(3):
        _create(client, dev_user, title=f"P{i}")
    r = client.get(BASE, params={"limit": 20, "offset": 0})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"items", "limit", "offset", "total"}
    assert body["total"] == 3
    assert body["limit"] == 20 and body["offset"] == 0
    assert body["items"][0]["latest_version_number"] == 1


def test_pagination_limit_and_offset(client, dev_user):
    for i in range(5):
        _create(client, dev_user, title=f"Page{i}")
    first = client.get(BASE, params={"limit": 2, "offset": 0}).json()
    second = client.get(BASE, params={"limit": 2, "offset": 2}).json()
    assert len(first["items"]) == 2
    assert len(second["items"]) == 2
    assert first["total"] == second["total"] == 5
    ids_first = {i["prompt_id"] for i in first["items"]}
    ids_second = {i["prompt_id"] for i in second["items"]}
    assert ids_first.isdisjoint(ids_second)


def test_list_search_is_lexical_substring(client, dev_user):
    _create(client, dev_user, title="Alpha Optimizer")
    _create(client, dev_user, title="Beta Helper")
    r = client.get(BASE, params={"search": "optimizer"})
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Alpha Optimizer"


def test_list_filter_is_public(client, dev_user):
    _create(client, dev_user, title="Public one", is_public=True)
    _create(client, dev_user, title="Private one", is_public=False)
    r = client.get(BASE, params={"is_public": "true"})
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["is_public"] is True


@pytest.mark.parametrize("bad", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_list_rejects_bad_pagination(client, bad):
    assert client.get(BASE, params=bad).status_code == 422


# --- 10 / 11  get single ------------------------------------------- #
def test_get_single_prompt(client, dev_user):
    pid = _create(client, dev_user, title="Fetch me").json()["prompt_id"]
    r = client.get(f"{BASE}/{pid}")
    assert r.status_code == 200
    assert r.json()["prompt_id"] == pid
    assert r.json()["title"] == "Fetch me"


def test_get_missing_prompt_returns_404(client):
    r = client.get(f"{BASE}/{uuid.uuid4()}")
    assert r.status_code == 404


# --- 15  invalid uuid ------------------------------------------- #
def test_get_prompt_invalid_uuid_returns_422(client):
    assert client.get(f"{BASE}/not-a-uuid").status_code == 422
    assert client.get(f"{BASE}/123/versions").status_code == 422


# --- 12 / 13  versions read-only, immutable -------------------- #
def test_list_versions_ordered_ascending(client, dev_user):
    pid = _create(client, dev_user).json()["prompt_id"]
    r = client.get(f"{BASE}/{pid}/versions")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert [v["version_number"] for v in body["items"]] == [1]


def test_list_versions_missing_prompt_returns_404(client):
    assert client.get(f"{BASE}/{uuid.uuid4()}/versions").status_code == 404


def test_versions_have_no_write_endpoints(client, dev_user):
    pid = _create(client, dev_user).json()["prompt_id"]
    vid = client.get(f"{BASE}/{pid}/versions").json()["items"][0]["version_id"]
    # No PUT/PATCH/DELETE routes exist for versions.
    assert client.put(f"{BASE}/{pid}/versions").status_code == 405
    assert client.patch(f"{BASE}/{pid}/versions/{vid}").status_code in (404, 405)
    assert client.delete(f"{BASE}/{pid}/versions/{vid}").status_code in (404, 405)


def test_existing_version_content_is_unchanged_after_rereads(client, dev_user):
    body = _create(client, dev_user, content="immutable text").json()
    pid = body["prompt_id"]
    v1_id = body["versions"][0]["version_id"]
    for _ in range(3):
        again = client.get(f"{BASE}/{pid}/versions").json()["items"][0]
        assert again["version_id"] == v1_id
        assert again["content"] == "immutable text"


# --- 14  transaction rollback ---------------------------------- #
def test_failed_initial_version_rolls_back_prompt(client, dev_user, db_session, monkeypatch):
    from app.services import prompt as prompt_service

    def _boom(*_a, **_kw):
        raise RuntimeError("simulated failure creating initial version")

    monkeypatch.setattr(prompt_service.repo, "add_version", _boom)

    before = db_session.scalar(sa.select(sa.func.count()).select_from(Prompt))
    r = _create(client, dev_user, title="Should Not Persist")
    assert r.status_code == 500
    assert r.json() == {"detail": "Internal server error"}

    db_session.expire_all()
    after = db_session.scalar(sa.select(sa.func.count()).select_from(Prompt))
    assert after == before
    assert db_session.scalar(
        sa.select(sa.func.count())
        .select_from(Prompt)
        .where(Prompt.title == "Should Not Persist")
    ) == 0


# --- OpenAPI ------------------------------------------------- #
def test_openapi_and_docs_available(client):
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert f"{BASE}" in schema["paths"]
    # development-only header is documented on the create operation
    params = schema["paths"][BASE]["post"].get("parameters", [])
    assert any(p["name"] == "x-dev-user-id" for p in params)


def test_cors_preflight_allows_configured_origin(client):
    r = client.options(
        BASE,
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
