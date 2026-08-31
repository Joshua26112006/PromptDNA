"""Phase 6 — semantic search + version embeddings (real PostgreSQL + pgvector).

Tests that need the ``vector`` extension are skipped **with a reason** when it
is not installed in the test database (the migration then stops before 0002).
The embedding provider is always the deterministic MockEmbeddingProvider — no
external API is called.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa

from app.db.models import Version
from tests.conftest import PGVECTOR_AVAILABLE

needs_pgvector = pytest.mark.skipif(
    not PGVECTOR_AVAILABLE,
    reason="pgvector 'vector' extension is not installed in the test database",
)

PROMPTS = "/api/v1/prompts"
SEMANTIC = "/api/v1/search/semantic"


def mk_prompt(client, auth, *, title, content, is_public=False):
    r = client.post(
        PROMPTS,
        json={"title": title, "content": content, "is_public": is_public},
        headers=auth.headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def embed_all(client, auth, prompt):
    vid = prompt["versions"][0]["version_id"]
    r = client.post(f"/api/v1/versions/{vid}/embedding", headers=auth.headers)
    assert r.status_code == 200, r.text
    return r.json()


# --------------------------------------------------------------------------- #
# Always run — no pgvector needed                                            #
# --------------------------------------------------------------------------- #
def test_semantic_search_requires_auth(client):
    assert client.get(f"{SEMANTIC}?query=hello").status_code == 401


def test_empty_query_is_rejected(client, user_a):
    # FastAPI Query(min_length=1)
    assert client.get(f"{SEMANTIC}?query=", headers=user_a.headers).status_code == 422
    # whitespace-only -> service rejects before any vector work
    assert client.get(f"{SEMANTIC}?query=%20%20", headers=user_a.headers).status_code == 400


def test_lexical_search_still_works(client, user_a):
    uniq = "Zetaprompt Optimizer"
    mk_prompt(client, user_a, title=uniq, content="x")
    mk_prompt(client, user_a, title="Beta Helper", content="y")
    titles = {
        i["title"]
        for i in client.get(
            f"{PROMPTS}?search=zetaprompt", headers=user_a.headers
        ).json()["items"]
    }
    assert titles == {uniq}  # lexical ILIKE on title, unaffected by Phase 6


# --------------------------------------------------------------------------- #
# Need pgvector                                                              #
# --------------------------------------------------------------------------- #
@needs_pgvector
def test_pgvector_extension_is_available(db_session):
    row = db_session.execute(
        sa.text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
    ).first()
    assert row is not None


@needs_pgvector
def test_version_stores_embedding_of_correct_dimension_without_changing_content(
    client, user_a, db_session
):
    p = mk_prompt(client, user_a, title="Sum", content="ORIGINAL CONTENT")
    vid = uuid.UUID(p["versions"][0]["version_id"])
    status = embed_all(client, user_a, p)
    assert status["has_embedding"] is True
    assert status["dimension"] == 1536

    row = db_session.get(Version, vid)
    db_session.refresh(row, ["embedding", "embedding_model", "content"])
    assert row.content == "ORIGINAL CONTENT"          # unchanged
    assert len(list(row.embedding)) == 1536
    assert row.embedding_model


@needs_pgvector
def test_embedding_failure_does_not_delete_or_change_the_version(
    client, user_a, db_session, monkeypatch
):
    from app.embeddings.mock import MockEmbeddingProvider

    def boom(self, text, *, timeout_s):
        from app.embeddings.base import EmbeddingRequestError

        raise EmbeddingRequestError("provider exploded")

    monkeypatch.setattr(MockEmbeddingProvider, "embed", boom)
    p = mk_prompt(client, user_a, title="Keep", content="STILL HERE")
    vid = p["versions"][0]["version_id"]
    r = client.post(f"/api/v1/versions/{vid}/embedding", headers=user_a.headers)
    assert r.status_code == 503
    # the version is untouched and still retrievable
    got = client.get(f"{PROMPTS}/{p['prompt_id']}/versions/{vid}", headers=user_a.headers)
    assert got.status_code == 200
    assert got.json()["content"] == "STILL HERE"


@needs_pgvector
def test_only_owner_can_generate_embedding(client, user_a, user_b):
    pub = mk_prompt(client, user_a, title="Pub", content="c", is_public=True)
    priv = mk_prompt(client, user_a, title="Priv", content="c", is_public=False)
    assert client.post(
        f"/api/v1/versions/{pub['versions'][0]['version_id']}/embedding",
        headers=user_b.headers,
    ).status_code == 403
    assert client.post(
        f"/api/v1/versions/{priv['versions'][0]['version_id']}/embedding",
        headers=user_b.headers,
    ).status_code == 404


@needs_pgvector
def test_semantic_search_ranks_related_above_unrelated_and_returns_similarity(
    client, user_a
):
    a = mk_prompt(client, user_a, title="A", content="Summarize academic research papers.", is_public=True)
    b = mk_prompt(client, user_a, title="B", content="Create concise summaries of scholarly articles.", is_public=True)
    c = mk_prompt(client, user_a, title="C", content="Write a Python function to sort a list.", is_public=True)
    for p in (a, b, c):
        embed_all(client, user_a, p)

    body = client.get(
        f"{SEMANTIC}?query=Help me summarize scholarly papers&limit=3",
        headers=user_a.headers,
    ).json()
    titles = [r["prompt_title"] for r in body["results"]]
    assert set(titles[:2]) == {"A", "B"}          # A/B rank above C
    assert titles[-1] == "C"
    assert all("similarity" in r for r in body["results"])
    assert body["results"][0]["similarity"] >= body["results"][-1]["similarity"]
    # never leak the raw vector
    assert "embedding" not in body["results"][0]
    assert "vector" not in str(body).lower()


@needs_pgvector
def test_semantic_search_excludes_other_users_private_prompts(client, user_a, user_b):
    secret = mk_prompt(
        client, user_a, title="Secret A",
        content="Summarize academic research papers thoroughly.", is_public=False,
    )
    embed_all(client, user_a, secret)

    body = client.get(
        f"{SEMANTIC}?query=summarize academic research", headers=user_b.headers
    ).json()
    ids = {r["prompt_id"] for r in body["results"]}
    assert secret["prompt_id"] not in ids


@needs_pgvector
def test_semantic_search_includes_own_private_and_public(client, user_a, user_b):
    mine = mk_prompt(client, user_a, title="Mine", content="summarize research papers", is_public=False)
    theirs_public = mk_prompt(client, user_b, title="Theirs", content="summarize research articles", is_public=True)
    embed_all(client, user_a, mine)
    embed_all(client, user_b, theirs_public)

    ids = {
        r["prompt_id"]
        for r in client.get(
            f"{SEMANTIC}?query=summarize research", headers=user_a.headers
        ).json()["results"]
    }
    assert mine["prompt_id"] in ids
    assert theirs_public["prompt_id"] in ids


@needs_pgvector
def test_semantic_search_owner_filter(client, user_a, user_b):
    mine = mk_prompt(client, user_a, title="Mine", content="summarize research", is_public=True)
    theirs = mk_prompt(client, user_b, title="Theirs", content="summarize research too", is_public=True)
    embed_all(client, user_a, mine)
    embed_all(client, user_b, theirs)
    ids = {
        r["prompt_id"]
        for r in client.get(
            f"{SEMANTIC}?query=summarize research&owner=true", headers=user_a.headers
        ).json()["results"]
    }
    assert ids == {mine["prompt_id"]}


@needs_pgvector
def test_hnsw_index_exists(db_session):
    row = db_session.execute(
        sa.text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE tablename = 'versions' AND indexname = 'ix_versions_embedding_hnsw'"
        )
    ).first()
    assert row is not None
    assert "hnsw" in row[0].lower()
    assert "vector_cosine_ops" in row[0].lower()


@needs_pgvector
def test_versions_without_embedding_are_not_returned(client, user_a):
    # a prompt whose version was never embedded must not appear in results
    p = mk_prompt(client, user_a, title="NoEmbed", content="summarize research papers", is_public=True)
    body = client.get(
        f"{SEMANTIC}?query=summarize research papers", headers=user_a.headers
    ).json()
    assert p["prompt_id"] not in {r["prompt_id"] for r in body["results"]}
