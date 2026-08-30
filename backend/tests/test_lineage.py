"""Phase 4A — prompt lineage via ``parent_prompt_id`` on create.

Rule: a user may fork/derive from any prompt they can VIEW; the new prompt is
owned by the creator and ownership is never transferred. Covers mandated cases
34–38. Real PostgreSQL, savepoint-isolated.
"""

from __future__ import annotations

import uuid

from app.db.models import Prompt

BASE = "/api/v1/prompts"


def _create(client, auth, **over):
    body = {"title": "P", "content": "c", "is_public": False}
    body.update(over)
    return client.post(BASE, json=body, headers=auth.headers)


# --- 34  valid parent accepted ---------------------------------------- #
def test_fork_from_own_prompt_records_parent(client, user_a):
    parent = _create(client, user_a, title="Parent").json()["prompt_id"]
    child = _create(client, user_a, title="Child", parent_prompt_id=parent)
    assert child.status_code == 201
    assert child.json()["parent_prompt_id"] == parent


# --- 35  invalid parent rejected ------------------------------------ #
def test_nonexistent_parent_is_rejected_404(client, user_a):
    r = _create(client, user_a, parent_prompt_id=str(uuid.uuid4()))
    assert r.status_code == 404


def test_malformed_parent_uuid_is_422(client, user_a):
    r = _create(client, user_a, parent_prompt_id="not-a-uuid")
    assert r.status_code == 422


def test_private_prompt_of_another_user_cannot_be_a_parent_404(client, user_a, user_b):
    private_a = _create(client, user_a, is_public=False).json()["prompt_id"]
    r = _create(client, user_b, parent_prompt_id=private_a)
    assert r.status_code == 404  # not viewable -> indistinguishable from missing


# --- 36  self-parenting rejected ---------------------------------- #
def test_self_parenting_is_rejected(client, user_a, monkeypatch):
    """Structurally impossible through the API (the client cannot know the new
    prompt_id), but the service still guards against it. Simulate by forcing the
    freshly-created prompt's id to equal the requested parent id."""

    from app.services import prompt as prompt_service

    target = _create(client, user_a, title="Target").json()["prompt_id"]
    target_uuid = uuid.UUID(target)
    real_add_prompt = prompt_service.repo.add_prompt

    def _add_prompt_forcing_id(db, **kw):
        p = real_add_prompt(db, **kw)
        p.prompt_id = target_uuid
        return p

    monkeypatch.setattr(prompt_service.repo, "add_prompt", _add_prompt_forcing_id)
    r = _create(client, user_a, title="Loop", parent_prompt_id=target)
    assert r.status_code in (400, 403)  # rejected, not persisted


# --- 37  child belongs to creator, not the parent's owner --------- #
def test_forked_child_is_owned_by_creator_not_parent_owner(client, user_a, user_b):
    parent = _create(client, user_a, title="A's public", is_public=True).json()
    parent_id, a_id = parent["prompt_id"], parent["user_id"]

    child = _create(client, user_b, title="B's fork", parent_prompt_id=parent_id).json()
    assert child["user_id"] == user_b.user_id
    assert child["user_id"] != a_id
    assert child["parent_prompt_id"] == parent_id
    # parent is untouched
    reread = client.get(f"{BASE}/{parent_id}", headers=user_a.headers).json()
    assert reread["user_id"] == a_id
    assert reread["parent_prompt_id"] is None


# --- 38  a public parent can be used as a fork source ------------- #
def test_public_prompt_can_be_forked_by_another_user(client, user_a, user_b, db_session):
    public_a = _create(client, user_a, title="Shared", is_public=True).json()["prompt_id"]

    child = _create(client, user_b, title="Derived", parent_prompt_id=public_a)
    assert child.status_code == 201

    row = db_session.get(Prompt, uuid.UUID(child.json()["prompt_id"]))
    assert str(row.parent_prompt_id) == public_a
    assert str(row.user_id) == user_b.user_id
    # child has its own independent Version 1
    hist = client.get(
        f"{BASE}/{child.json()['prompt_id']}/versions", headers=user_b.headers
    ).json()
    assert hist["total"] == 1 and hist["items"][0]["version_number"] == 1
