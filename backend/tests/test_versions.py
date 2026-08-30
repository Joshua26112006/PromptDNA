"""Phase 4A — version creation, numbering, immutability, retrieval, concurrency.

Real PostgreSQL; savepoint-isolated (see conftest). Covers mandated cases
15–33.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa

from app.db.models import Version

BASE = "/api/v1/prompts"


def _new_prompt(client, auth, *, is_public=False, content="V1 content"):
    r = client.post(
        BASE,
        json={"title": "P", "content": content, "is_public": is_public},
        headers=auth.headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _add_version(client, auth, prompt_id, *, content="next", change_summary="s"):
    body = {"content": content}
    if change_summary is not None:
        body["change_summary"] = change_summary
    return client.post(
        f"{BASE}/{prompt_id}/versions", json=body, headers=auth.headers
    )


# --- 15 / 16 / 17  owner appends versions; numbers increment -------------- #
def test_owner_creates_v2_and_v3_incrementing(client, user_a):
    pid = _new_prompt(client, user_a)["prompt_id"]

    r2 = _add_version(client, user_a, pid, content="second")
    assert r2.status_code == 201
    assert r2.json()["version_number"] == 2

    r3 = _add_version(client, user_a, pid, content="third")
    assert r3.status_code == 201
    assert r3.json()["version_number"] == 3


# --- 18 / 19 / 20  content, change_summary, created_by ------------------ #
def test_new_version_stores_content_summary_and_creator(client, user_a):
    pid = _new_prompt(client, user_a)["prompt_id"]
    r = _add_version(
        client, user_a, pid, content="exact body text", change_summary="why"
    )
    v = r.json()
    assert v["content"] == "exact body text"
    assert v["change_summary"] == "why"
    assert v["created_by"] == user_a.user_id
    assert v["prompt_id"] == pid


def test_change_summary_is_optional(client, user_a):
    pid = _new_prompt(client, user_a)["prompt_id"]
    r = _add_version(client, user_a, pid, content="no summary", change_summary=None)
    assert r.status_code == 201
    assert r.json()["change_summary"] is None


def test_client_cannot_choose_version_number_or_creator(client, user_a, user_b):
    pid = _new_prompt(client, user_a)["prompt_id"]
    for extra in ({"version_number": 99}, {"created_by": user_b.user_id},
                  {"created_at": "2000-01-01T00:00:00Z"}):
        r = client.post(
            f"{BASE}/{pid}/versions",
            json={"content": "x", **extra},
            headers=user_a.headers,
        )
        assert r.status_code == 422, extra


def test_empty_version_content_is_rejected(client, user_a):
    pid = _new_prompt(client, user_a)["prompt_id"]
    for bad in ("", "   "):
        r = _add_version(client, user_a, pid, content=bad)
        assert r.status_code == 422


# --- 21 / 22  only the owner may create versions ---------------------- #
def test_other_user_cannot_create_version_on_public_prompt(client, user_a, user_b):
    pid = _new_prompt(client, user_a, is_public=True)["prompt_id"]
    r = _add_version(client, user_b, pid, content="hijack")
    assert r.status_code == 403


def test_other_user_cannot_create_version_on_private_prompt_404(client, user_a, user_b):
    pid = _new_prompt(client, user_a, is_public=False)["prompt_id"]
    r = _add_version(client, user_b, pid, content="hijack")
    assert r.status_code == 404  # existence not leaked


def test_create_version_requires_auth(client, user_a):
    pid = _new_prompt(client, user_a)["prompt_id"]
    r = client.post(f"{BASE}/{pid}/versions", json={"content": "x"})
    assert r.status_code == 401


def test_create_version_on_missing_prompt_404(client, user_a):
    r = _add_version(client, user_a, uuid.uuid4(), content="x")
    assert r.status_code == 404


# --- 23 / 24 / 25 / 26  immutability -------------------------------- #
def test_no_write_endpoints_for_a_version(client, user_a):
    pid = _new_prompt(client, user_a)["prompt_id"]
    vid = _add_version(client, user_a, pid, content="v2").json()["version_id"]
    assert client.put(f"{BASE}/{pid}/versions/{vid}", json={"content": "z"},
                      headers=user_a.headers).status_code == 405
    assert client.patch(f"{BASE}/{pid}/versions/{vid}", json={"content": "z"},
                        headers=user_a.headers).status_code == 405
    assert client.delete(f"{BASE}/{pid}/versions/{vid}",
                         headers=user_a.headers).status_code == 405
    # ...and none at the collection level either
    assert client.put(f"{BASE}/{pid}/versions", headers=user_a.headers).status_code == 405


def test_existing_versions_unchanged_after_appending(client, user_a):
    prompt = _new_prompt(client, user_a, content="ORIGINAL V1")
    pid = prompt["prompt_id"]
    v1_id = prompt["versions"][0]["version_id"]

    _add_version(client, user_a, pid, content="V2")
    _add_version(client, user_a, pid, content="V3")

    hist = client.get(f"{BASE}/{pid}/versions", headers=user_a.headers).json()
    assert [v["version_number"] for v in hist["items"]] == [1, 2, 3]
    v1 = next(v for v in hist["items"] if v["version_number"] == 1)
    assert v1["version_id"] == v1_id
    assert v1["content"] == "ORIGINAL V1"          # untouched
    assert v1["change_summary"] == "Initial version."


def test_version_row_is_not_updated_in_db(client, user_a, db_session):
    prompt = _new_prompt(client, user_a, content="frozen")
    pid = uuid.UUID(prompt["prompt_id"])
    v1_id = uuid.UUID(prompt["versions"][0]["version_id"])
    v1_before = db_session.get(Version, v1_id)
    created_at_before, content_before = v1_before.created_at, v1_before.content

    _add_version(client, user_a, str(pid), content="v2")
    db_session.expire_all()

    v1_after = db_session.get(Version, v1_id)
    assert v1_after.content == content_before == "frozen"
    assert v1_after.created_at == created_at_before


# --- 27 / 28  version history --------------------------------------- #
def test_history_returns_all_versions_ordered_asc(client, user_a):
    pid = _new_prompt(client, user_a)["prompt_id"]
    for i in range(2, 6):
        _add_version(client, user_a, pid, content=f"v{i}")
    body = client.get(f"{BASE}/{pid}/versions", headers=user_a.headers).json()
    assert body["total"] == 5
    assert [v["version_number"] for v in body["items"]] == [1, 2, 3, 4, 5]


# --- 29 / 30 / 31  specific version retrieval ---------------------- #
def test_specific_version_returns_correct_row(client, user_a):
    pid = _new_prompt(client, user_a)["prompt_id"]
    v2 = _add_version(client, user_a, pid, content="the second").json()
    got = client.get(f"{BASE}/{pid}/versions/{v2['version_id']}", headers=user_a.headers)
    assert got.status_code == 200
    assert got.json()["version_id"] == v2["version_id"]
    assert got.json()["content"] == "the second"


def test_version_from_another_prompt_returns_404(client, user_a):
    p1 = _new_prompt(client, user_a)["prompt_id"]
    p2 = _new_prompt(client, user_a)["prompt_id"]
    v_of_p1 = _add_version(client, user_a, p1, content="belongs to p1").json()["version_id"]
    # ask for p1's version *under p2's URL*
    r = client.get(f"{BASE}/{p2}/versions/{v_of_p1}", headers=user_a.headers)
    assert r.status_code == 404


def test_specific_version_of_missing_version_is_404(client, user_a):
    pid = _new_prompt(client, user_a)["prompt_id"]
    r = client.get(f"{BASE}/{pid}/versions/{uuid.uuid4()}", headers=user_a.headers)
    assert r.status_code == 404


def test_versions_of_inaccessible_private_prompt_are_404(client, user_a, user_b):
    prompt = _new_prompt(client, user_a, is_public=False)
    pid = prompt["prompt_id"]
    vid = prompt["versions"][0]["version_id"]
    assert client.get(f"{BASE}/{pid}/versions", headers=user_b.headers).status_code == 404
    assert client.get(f"{BASE}/{pid}/versions/{vid}", headers=user_b.headers).status_code == 404


def test_other_user_can_read_versions_of_public_prompt(client, user_a, user_b):
    prompt = _new_prompt(client, user_a, is_public=True)
    pid = prompt["prompt_id"]
    vid = prompt["versions"][0]["version_id"]
    assert client.get(f"{BASE}/{pid}/versions", headers=user_b.headers).status_code == 200
    assert client.get(f"{BASE}/{pid}/versions/{vid}", headers=user_b.headers).status_code == 200


def test_specific_version_requires_auth(client, user_a):
    prompt = _new_prompt(client, user_a)
    pid, vid = prompt["prompt_id"], prompt["versions"][0]["version_id"]
    assert client.get(f"{BASE}/{pid}/versions/{vid}").status_code == 401


# --- 32 / 33  version-number conflict handling -------------------- #
def test_persistent_version_number_conflict_returns_409(client, user_a, monkeypatch):
    """If the computed number keeps colliding (simulated), the API returns 409
    rather than a 500 or a silent overwrite."""

    from app.services import prompt as prompt_service

    pid = _new_prompt(client, user_a)["prompt_id"]  # V1 exists

    # Force every attempt to compute version_number = 1 -> always collides with V1.
    monkeypatch.setattr(
        prompt_service.repo, "get_max_version_number", lambda *a, **k: 0
    )
    r = _add_version(client, user_a, pid, content="doomed")
    assert r.status_code == 409
    assert "version number" in r.json()["detail"].lower()


def test_db_still_rejects_duplicate_version_numbers(client, user_a, db_session):
    """The UNIQUE(prompt_id, version_number) constraint is the final guard."""

    from sqlalchemy.exc import IntegrityError

    pid = uuid.UUID(_new_prompt(client, user_a)["prompt_id"])
    db_session.add(
        Version(prompt_id=pid, version_number=1, content="dupe",
                created_by=uuid.UUID(user_a.user_id), change_summary=None)
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_sequential_creation_never_reuses_a_number(client, user_a, db_session):
    pid = _new_prompt(client, user_a)["prompt_id"]
    seen = {1}
    for _ in range(6):
        n = _add_version(client, user_a, pid, content="x").json()["version_number"]
        assert n not in seen
        seen.add(n)
    assert seen == {1, 2, 3, 4, 5, 6, 7}
    rows = db_session.scalars(
        sa.select(Version.version_number).where(Version.prompt_id == uuid.UUID(pid))
    ).all()
    assert sorted(rows) == [1, 2, 3, 4, 5, 6, 7]
