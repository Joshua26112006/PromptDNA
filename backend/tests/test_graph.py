"""Phase 7 — Neo4j graph projection + traversal.

Uses the local docker-compose `promptdna-neo4j` container. Skips **with a
reason** when Neo4j is unreachable (never runs against a fake). PostgreSQL
stays authoritative throughout.
"""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import NEO4J_AVAILABLE

pytestmark = pytest.mark.skipif(
    not NEO4J_AVAILABLE,
    reason="Neo4j (docker-compose promptdna-neo4j) is not reachable",
)

GRAPH = "/api/v1/graph/prompts"


@pytest.fixture
def g(graph_clean):
    from app.graph import service as graph_service

    return graph_service


def nid() -> str:
    return str(uuid.uuid4())


# --- 1  connection ------------------------------------------------------- #
def test_1_neo4j_connection_works():
    from app.graph.client import verify_connectivity

    verify_connectivity()  # raises GraphUnavailable on failure


# --- 2 / 3 / 4  node upsert idempotency -------------------------------- #
def test_2_3_4_prompt_node_merge_is_idempotent(g):
    pid = nid()
    assert g.merge_prompt_node(pid, "Title A") == 1     # created
    assert g.merge_prompt_node(pid, "Title A") == 0     # merged, no new node
    assert g.merge_prompt_node(pid, "Title B") == 0     # still no new node (title updated)
    assert g.all_prompt_ids() == {pid}                  # exactly one node


# --- 5 / 6 / 7 / 8  relationship upsert ------------------------------ #
@pytest.mark.parametrize("rel", ["DERIVED_FROM", "FORKED_FROM", "DEPENDS_ON"])
def test_5_6_7_8_relationship_merge_is_idempotent(g, rel):
    child, parent = nid(), nid()
    assert g.merge_relationship(child, parent, rel) == 1   # created
    assert g.merge_relationship(child, parent, rel) == 0   # merged, no duplicate
    # both endpoints exist as :Prompt nodes
    assert {child, parent} <= g.all_prompt_ids()


def test_unknown_relationship_type_is_rejected(g):
    with pytest.raises(ValueError):
        g.merge_relationship(nid(), nid(), "OWNS")


def test_self_relationship_is_rejected(g):
    x = nid()
    with pytest.raises(ValueError):
        g.merge_relationship(x, x, "DERIVED_FROM")


# --- 9 / 10  ancestor + descendant traversal ------------------------ #
def test_9_10_ancestor_and_descendant_traversal(g):
    # A <- B <- C   (C DERIVED_FROM B, B FORKED_FROM A)
    a, b, c = nid(), nid(), nid()
    for x, t in ((a, "A"), (b, "B"), (c, "C")):
        g.merge_prompt_node(x, t)
    g.merge_relationship(b, a, "FORKED_FROM")
    g.merge_relationship(c, b, "DERIVED_FROM")

    anc = g.ancestors(c)
    by_depth = {r["depth"]: r["prompt_id"] for r in anc}
    assert by_depth == {1: b, 2: a}
    assert anc[0]["rel_types"] == ["DERIVED_FROM"]
    assert set(anc[1]["rel_types"]) == {"DERIVED_FROM", "FORKED_FROM"}

    desc = g.descendants(a)
    assert {r["prompt_id"]: r["depth"] for r in desc} == {b: 1, c: 2}


# --- 11  dependency traversal (explicit, NOT semantic) ------------- #
def test_11_dependency_traversal(g):
    p, d1, d2 = nid(), nid(), nid()
    for x in (p, d1, d2):
        g.merge_prompt_node(x, x[:8])
    g.merge_relationship(p, d1, "DEPENDS_ON")
    g.merge_relationship(d1, d2, "DEPENDS_ON")
    deps = g.dependencies(p)
    assert {r["prompt_id"]: r["depth"] for r in deps} == {d1: 1, d2: 2}
    # DEPENDS_ON is not a lineage relationship -> not in ancestors
    assert g.ancestors(p) == []


# --- 12  related traversal (1 hop, both directions, all types) ---- #
def test_12_related_traversal(g):
    p, parent, child, dep = nid(), nid(), nid(), nid()
    for x in (p, parent, child, dep):
        g.merge_prompt_node(x, x[:8])
    g.merge_relationship(p, parent, "DERIVED_FROM")   # p -> parent (outgoing)
    g.merge_relationship(child, p, "FORKED_FROM")     # child -> p (incoming)
    g.merge_relationship(p, dep, "DEPENDS_ON")        # p -> dep (outgoing)

    rel = {r["prompt_id"]: (r["type"], r["direction"]) for r in g.related(p)}
    assert rel == {
        parent: ("DERIVED_FROM", "outgoing"),
        child: ("FORKED_FROM", "incoming"),
        dep: ("DEPENDS_ON", "outgoing"),
    }


# --- 13 / 14  PostgreSQL is authoritative; projection is correct -- #
def test_13_14_postgres_is_authoritative_and_projects(client, user_a, db_session, g):
    from app.db.models import Prompt

    # Create a prompt (PostgreSQL) + a child that DERIVED_FROM it.
    parent = client.post(
        "/api/v1/prompts",
        json={"title": "Parent P", "content": "c", "is_public": True},
        headers=user_a.headers,
    ).json()
    child = client.post(
        "/api/v1/prompts",
        json={"title": "Child P", "content": "c", "is_public": True,
              "parent_prompt_id": parent["prompt_id"]},
        headers=user_a.headers,
    ).json()

    # projection hook ran after commit -> nodes + DERIVED_FROM edge exist
    ids = g.all_prompt_ids()
    assert {parent["prompt_id"], child["prompt_id"]} <= ids
    anc = g.ancestors(child["prompt_id"])
    assert anc and anc[0]["prompt_id"] == parent["prompt_id"]

    # Authoritative title: change it only in Neo4j, then verify the graph API
    # returns the PostgreSQL title (system of record wins).
    g.merge_prompt_node(parent["prompt_id"], "STALE NEO4J TITLE")
    body = client.get(
        f"{GRAPH}/{child['prompt_id']}/ancestors", headers=user_a.headers
    ).json()
    assert body["relationships"][0]["title"] == "Parent P"  # from PostgreSQL


# --- 15 / 16  re-running sync creates no duplicates -------------- #
def test_15_16_resync_is_idempotent(client, user_a, db_session, g):
    from app.db.models import Prompt
    from sqlalchemy import select

    p1 = client.post("/api/v1/prompts", json={"title": "S1", "content": "c", "is_public": True}, headers=user_a.headers).json()
    p2 = client.post("/api/v1/prompts", json={"title": "S2", "content": "c", "is_public": True, "parent_prompt_id": p1["prompt_id"]}, headers=user_a.headers).json()

    rows = db_session.execute(
        select(Prompt.prompt_id, Prompt.title, Prompt.parent_prompt_id)
    ).all()

    def project_all():
        created_n = created_r = 0
        for pid, title, parent in rows:
            created_n += g.merge_prompt_node(str(pid), title)
            if parent is not None:
                created_r += g.merge_relationship(str(pid), str(parent), "DERIVED_FROM")
        return created_n, created_r

    # Start from an empty graph so the first projection actually creates nodes.
    from app.graph.client import get_database, get_driver

    with get_driver().session(database=get_database()) as s:
        s.run("MATCH (p:Prompt) DETACH DELETE p")

    first = project_all()
    second = project_all()
    third = project_all()
    assert first == (2, 1)          # fresh projection creates 2 nodes + 1 edge
    assert second == (0, 0)         # re-run: nothing new
    assert third == (0, 0)         # still nothing new

    # graph now holds exactly those two nodes + exactly one DERIVED_FROM edge
    assert g.all_prompt_ids() == {p1["prompt_id"], p2["prompt_id"]}
    with get_driver().session(database=get_database()) as s:
        n_edges = s.run(
            "MATCH (:Prompt)-[r:DERIVED_FROM]->(:Prompt) RETURN count(r) AS n"
        ).single()["n"]
    assert n_edges == 1


# --- 17  Neo4j unavailability does not corrupt PostgreSQL -------- #
def test_17_neo4j_outage_does_not_break_postgres(client, user_a, db_session, monkeypatch):
    from app.db.models import Prompt
    from app.graph.client import GraphUnavailable
    from app.services import graph as graph_service

    monkeypatch.setattr(
        graph_service.graph, "merge_prompt_node",
        lambda *a, **k: (_ for _ in ()).throw(GraphUnavailable("down")),
    )
    r = client.post(
        "/api/v1/prompts",
        json={"title": "Survives Neo4j Outage", "content": "authoritative", "is_public": False},
        headers=user_a.headers,
    )
    assert r.status_code == 201  # PostgreSQL write succeeded despite Neo4j failing
    pid = uuid.UUID(r.json()["prompt_id"])
    row = db_session.get(Prompt, pid)
    assert row is not None and row.title == "Survives Neo4j Outage"


# --- 18 / 19 / 20  graph API authorization --------------------- #
def _mk(client, auth, *, title, public, parent=None):
    body = {"title": title, "content": "c", "is_public": public}
    if parent:
        body["parent_prompt_id"] = parent
    return client.post("/api/v1/prompts", json=body, headers=auth.headers).json()


def test_18_owner_can_access_own_private_graph(client, user_a, g):
    p = _mk(client, user_a, title="A private", public=False)
    r = client.get(f"{GRAPH}/{p['prompt_id']}/related", headers=user_a.headers)
    assert r.status_code == 200
    assert r.json()["prompt_id"] == p["prompt_id"]


def test_19_public_prompt_graph_is_visible_to_others(client, user_a, user_b, g):
    pub = _mk(client, user_a, title="A public", public=True)
    child = _mk(client, user_a, title="A public child", public=True, parent=pub["prompt_id"])
    r = client.get(f"{GRAPH}/{pub['prompt_id']}/descendants", headers=user_b.headers)
    assert r.status_code == 200
    assert child["prompt_id"] in {rel["prompt_id"] for rel in r.json()["relationships"]}


def test_20_graph_endpoints_do_not_leak_private_prompts(client, user_a, user_b, g):
    # A's private prompt with a private child.
    priv = _mk(client, user_a, title="A secret", public=False)
    _mk(client, user_a, title="A secret child", public=False, parent=priv["prompt_id"])

    # B cannot even address it
    assert client.get(f"{GRAPH}/{priv['prompt_id']}/ancestors", headers=user_b.headers).status_code == 404
    assert client.get(f"{GRAPH}/{priv['prompt_id']}/descendants", headers=user_b.headers).status_code == 404
    assert client.get(f"{GRAPH}/{priv['prompt_id']}/related", headers=user_b.headers).status_code == 404

    # And a public prompt of A that links to A's private prompt must not expose it.
    pub = _mk(client, user_a, title="A bridge public", public=True, parent=priv["prompt_id"])
    body = client.get(f"{GRAPH}/{pub['prompt_id']}/ancestors", headers=user_b.headers).json()
    assert priv["prompt_id"] not in {r["prompt_id"] for r in body["relationships"]}
    # A (the owner) does see it
    body_a = client.get(f"{GRAPH}/{pub['prompt_id']}/ancestors", headers=user_a.headers).json()
    assert priv["prompt_id"] in {r["prompt_id"] for r in body_a["relationships"]}


def test_graph_endpoint_requires_auth(client, user_a, g):
    p = _mk(client, user_a, title="x", public=True)
    assert client.get(f"{GRAPH}/{p['prompt_id']}/related").status_code == 401


def test_graph_endpoint_unknown_prompt_is_404(client, user_a, g):
    assert client.get(f"{GRAPH}/{uuid.uuid4()}/related", headers=user_a.headers).status_code == 404


# --- 21  reconciliation removes orphaned nodes ---------------- #
def test_21_prune_removes_nodes_not_in_postgres(g):
    alive, orphan = nid(), nid()
    g.merge_prompt_node(alive, "alive")
    g.merge_prompt_node(orphan, "orphan (deleted in PG)")
    assert {alive, orphan} <= g.all_prompt_ids()

    # reconciliation: delete nodes whose id is not in the authoritative set
    valid = {alive}
    pruned = sum(g.delete_prompt_node(x) for x in g.all_prompt_ids() - valid)
    assert pruned == 1
    assert g.all_prompt_ids() == {alive}
