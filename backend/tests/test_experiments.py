"""Phase 5 — experiment execution against AI models (provider mocked).

Real PostgreSQL, savepoint-isolated. The external provider is always a fake
injected via ``monkeypatch`` — the normal test suite never calls a real AI API.
Covers mandated cases 1–21.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa

from app.db.models import Experiment, Model, Version
from app.providers.base import ProviderRequestError, ProviderTimeout

PROMPTS = "/api/v1/prompts"


# --------------------------------------------------------------------------- #
# Fake provider                                                             #
# --------------------------------------------------------------------------- #
class FakeProvider:
    key = "fake"
    label = "Fake"

    def __init__(self, *, output="FAKE MODEL OUTPUT", exc=None, configured=True,
                 hook=None):
        self.output = output
        self.exc = exc
        self._configured = configured
        self.hook = hook
        self.calls: list[dict] = []

    def is_configured(self) -> bool:
        return self._configured

    def generate(self, *, model_name, prompt_text, timeout_s):
        self.calls.append(
            {"model_name": model_name, "prompt_text": prompt_text, "timeout_s": timeout_s}
        )
        if self.hook:
            self.hook()
        if self.exc:
            raise self.exc
        return self.output


@pytest.fixture
def use_provider(monkeypatch):
    """Install a FakeProvider for every provider lookup in the experiment service."""

    def _install(provider: FakeProvider):
        monkeypatch.setattr(
            "app.services.experiment.get_provider", lambda _name: provider
        )
        return provider

    return _install


# --------------------------------------------------------------------------- #
# Helpers                                                                   #
# --------------------------------------------------------------------------- #
def make_model(db_session, provider="mock", name=None) -> Model:
    model = Model(name=name or f"Model-{uuid.uuid4().hex[:8]}", provider=provider)
    db_session.add(model)
    db_session.commit()
    return model


def make_prompt(client, auth, *, content="Summarize this document.", is_public=False):
    r = client.post(
        PROMPTS,
        json={"title": "P", "content": content, "is_public": is_public},
        headers=auth.headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def run(client, auth, prompt_id, version_id, model_id, notes=None):
    body = {"model_id": model_id}
    if notes is not None:
        body["notes"] = notes
    return client.post(
        f"{PROMPTS}/{prompt_id}/versions/{version_id}/experiments",
        json=body,
        headers=auth.headers,
    )


# --------------------------------------------------------------------------- #
# 1–4  authorization to execute                                             #
# --------------------------------------------------------------------------- #
def test_1_execution_requires_authentication(client, user_a, db_session, use_provider):
    use_provider(FakeProvider())
    m = make_model(db_session)
    p = make_prompt(client, user_a)
    r = client.post(
        f"{PROMPTS}/{p['prompt_id']}/versions/{p['versions'][0]['version_id']}/experiments",
        json={"model_id": str(m.model_id)},
    )
    assert r.status_code == 401


def test_2_non_owner_cannot_execute_on_private_prompt(client, user_a, user_b, db_session, use_provider):
    use_provider(FakeProvider())
    m = make_model(db_session)
    p = make_prompt(client, user_a, is_public=False)
    r = run(client, user_b, p["prompt_id"], p["versions"][0]["version_id"], str(m.model_id))
    assert r.status_code == 404  # existence not leaked


def test_3_owner_can_execute(client, user_a, db_session, use_provider):
    use_provider(FakeProvider())
    m = make_model(db_session)
    p = make_prompt(client, user_a)
    r = run(client, user_a, p["prompt_id"], p["versions"][0]["version_id"], str(m.model_id))
    assert r.status_code == 201
    assert r.json()["status"] == "SUCCESS"


def test_4_public_prompt_does_not_grant_execution(client, user_a, user_b, db_session, use_provider):
    use_provider(FakeProvider())
    m = make_model(db_session)
    p = make_prompt(client, user_a, is_public=True)
    r = run(client, user_b, p["prompt_id"], p["versions"][0]["version_id"], str(m.model_id))
    assert r.status_code == 403


# --------------------------------------------------------------------------- #
# 5 / 6  correct version content + model reach the provider                 #
# --------------------------------------------------------------------------- #
def test_5_exact_version_content_is_passed_to_provider(client, user_a, db_session, use_provider):
    fake = use_provider(FakeProvider())
    m = make_model(db_session, name="ModelX", provider="mock")
    p = make_prompt(client, user_a, content="ORIGINAL V1 CONTENT")
    # add V2 with different content and run against V2
    v2 = client.post(
        f"{PROMPTS}/{p['prompt_id']}/versions",
        json={"content": "SECOND VERSION CONTENT"},
        headers=user_a.headers,
    ).json()
    run(client, user_a, p["prompt_id"], v2["version_id"], str(m.model_id))
    assert fake.calls[0]["prompt_text"] == "SECOND VERSION CONTENT"
    assert fake.calls[0]["model_name"] == "ModelX"


def test_6_provider_selected_from_model_provider_field(client, user_a, db_session, monkeypatch):
    seen = {}
    monkeypatch.setattr(
        "app.services.experiment.get_provider",
        lambda name: seen.setdefault("name", name) or FakeProvider(),
    )
    m = make_model(db_session, provider="some-provider")
    p = make_prompt(client, user_a)
    run(client, user_a, p["prompt_id"], p["versions"][0]["version_id"], str(m.model_id))
    assert seen["name"] == "some-provider"


# --------------------------------------------------------------------------- #
# 7 / 8 / 9 / 10  lifecycle + result storage                                #
# --------------------------------------------------------------------------- #
def test_7_pending_experiment_is_committed_before_the_provider_call(
    client, user_a, db_session, use_provider
):
    pending_at_call = []

    def hook():
        pending_at_call.append(
            db_session.scalar(
                sa.select(sa.func.count())
                .select_from(Experiment)
                .where(Experiment.status == "PENDING")
            )
        )

    use_provider(FakeProvider(hook=hook))
    m = make_model(db_session)
    p = make_prompt(client, user_a)
    run(client, user_a, p["prompt_id"], p["versions"][0]["version_id"], str(m.model_id))
    assert pending_at_call == [1]  # the row existed & was committed during the call


def test_8_successful_execution_becomes_SUCCESS(client, user_a, db_session, use_provider):
    use_provider(FakeProvider(output="the answer"))
    m = make_model(db_session)
    p = make_prompt(client, user_a)
    body = run(client, user_a, p["prompt_id"], p["versions"][0]["version_id"], str(m.model_id)).json()
    assert body["status"] == "SUCCESS"
    assert body["error_message"] is None


def test_9_output_is_stored(client, user_a, db_session, use_provider):
    use_provider(FakeProvider(output="STORED OUTPUT 123"))
    m = make_model(db_session)
    p = make_prompt(client, user_a)
    body = run(client, user_a, p["prompt_id"], p["versions"][0]["version_id"], str(m.model_id)).json()
    assert body["output"] == "STORED OUTPUT 123"
    row = db_session.get(Experiment, uuid.UUID(body["experiment_id"]))
    db_session.refresh(row)
    assert row.output == "STORED OUTPUT 123"


def test_10_response_time_is_recorded_as_int_ms(client, user_a, db_session, use_provider):
    use_provider(FakeProvider())
    m = make_model(db_session)
    p = make_prompt(client, user_a)
    body = run(client, user_a, p["prompt_id"], p["versions"][0]["version_id"], str(m.model_id)).json()
    assert isinstance(body["response_time_ms"], int)
    assert body["response_time_ms"] >= 0
    assert body["executed_at"] is not None


# --------------------------------------------------------------------------- #
# 11 / 12  failure recorded as FAILED with a safe message                   #
# --------------------------------------------------------------------------- #
def test_11_failed_provider_call_becomes_FAILED(client, user_a, db_session, use_provider):
    use_provider(FakeProvider(exc=ProviderRequestError("provider returned HTTP 500")))
    m = make_model(db_session)
    p = make_prompt(client, user_a)
    r = run(client, user_a, p["prompt_id"], p["versions"][0]["version_id"], str(m.model_id))
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "FAILED"
    assert body["output"] is None
    assert body["response_time_ms"] is not None


def test_12_error_message_is_stored_and_safe(client, user_a, db_session, use_provider):
    use_provider(FakeProvider(exc=ProviderRequestError("could not reach the API")))
    m = make_model(db_session)
    p = make_prompt(client, user_a)
    body = run(client, user_a, p["prompt_id"], p["versions"][0]["version_id"], str(m.model_id)).json()
    assert body["error_message"] == "could not reach the API"
    assert "key" not in body["error_message"].lower()


# --------------------------------------------------------------------------- #
# 13 / 14 / 15  version untouched; references correct                       #
# --------------------------------------------------------------------------- #
def test_13_version_content_unchanged_after_experiment(client, user_a, db_session, use_provider):
    use_provider(FakeProvider())
    m = make_model(db_session)
    p = make_prompt(client, user_a, content="IMMUTABLE CONTENT")
    vid = p["versions"][0]["version_id"]
    run(client, user_a, p["prompt_id"], vid, str(m.model_id))
    got = client.get(f"{PROMPTS}/{p['prompt_id']}/versions/{vid}", headers=user_a.headers).json()
    assert got["content"] == "IMMUTABLE CONTENT"
    row = db_session.get(Version, uuid.UUID(vid))
    db_session.refresh(row)
    assert row.content == "IMMUTABLE CONTENT"


def test_14_15_experiment_references_correct_version_and_model(client, user_a, db_session, use_provider):
    use_provider(FakeProvider())
    m = make_model(db_session)
    p = make_prompt(client, user_a)
    vid = p["versions"][0]["version_id"]
    body = run(client, user_a, p["prompt_id"], vid, str(m.model_id)).json()
    assert body["version_id"] == vid
    assert body["model_id"] == str(m.model_id)
    assert body["prompt_id"] == p["prompt_id"]
    assert body["model_name"] == m.name
    assert body["provider"] == m.provider


# --------------------------------------------------------------------------- #
# 16 / 17  invalid model / missing provider config                         #
# --------------------------------------------------------------------------- #
def test_16_invalid_model_returns_404_and_creates_nothing(client, user_a, db_session, use_provider):
    use_provider(FakeProvider())
    p = make_prompt(client, user_a)
    before = db_session.scalar(sa.select(sa.func.count()).select_from(Experiment))
    r = run(client, user_a, p["prompt_id"], p["versions"][0]["version_id"], str(uuid.uuid4()))
    assert r.status_code == 404
    db_session.expire_all()
    assert db_session.scalar(sa.select(sa.func.count()).select_from(Experiment)) == before


def test_17_missing_provider_configuration_fails_cleanly(client, user_a, db_session, use_provider):
    use_provider(FakeProvider(configured=False))
    m = make_model(db_session, provider="OpenAI")
    p = make_prompt(client, user_a)
    before = db_session.scalar(sa.select(sa.func.count()).select_from(Experiment))
    r = run(client, user_a, p["prompt_id"], p["versions"][0]["version_id"], str(m.model_id))
    assert r.status_code == 503
    assert "not configured" in r.json()["detail"].lower()
    db_session.expire_all()
    assert db_session.scalar(sa.select(sa.func.count()).select_from(Experiment)) == before


def test_no_registered_provider_is_503(client, user_a, db_session, monkeypatch):
    monkeypatch.setattr("app.services.experiment.get_provider", lambda _n: None)
    m = make_model(db_session, provider="unknown-vendor")
    p = make_prompt(client, user_a)
    r = run(client, user_a, p["prompt_id"], p["versions"][0]["version_id"], str(m.model_id))
    assert r.status_code == 503


# --------------------------------------------------------------------------- #
# 18  timeout                                                               #
# --------------------------------------------------------------------------- #
def test_18_provider_timeout_is_recorded_as_FAILED(client, user_a, db_session, use_provider):
    use_provider(FakeProvider(exc=ProviderTimeout("request timed out after 30s")))
    m = make_model(db_session)
    p = make_prompt(client, user_a)
    body = run(client, user_a, p["prompt_id"], p["versions"][0]["version_id"], str(m.model_id)).json()
    assert body["status"] == "FAILED"
    assert "timed out" in body["error_message"].lower()


# --------------------------------------------------------------------------- #
# 19  score validation                                                      #
# --------------------------------------------------------------------------- #
@pytest.fixture
def experiment_id(client, user_a, db_session, use_provider):
    use_provider(FakeProvider())
    m = make_model(db_session)
    p = make_prompt(client, user_a)
    body = run(client, user_a, p["prompt_id"], p["versions"][0]["version_id"], str(m.model_id)).json()
    return body["experiment_id"], p


@pytest.mark.parametrize("bad", [11, -1, 10.5, -0.01])
def test_19_score_out_of_range_rejected(client, user_a, experiment_id, bad):
    eid, _ = experiment_id
    r = client.patch(f"/api/v1/experiments/{eid}", json={"score": bad}, headers=user_a.headers)
    assert r.status_code == 422


@pytest.mark.parametrize("ok", [0, 5, 10, 8.5])
def test_19_score_in_range_accepted(client, user_a, experiment_id, ok):
    eid, _ = experiment_id
    r = client.patch(f"/api/v1/experiments/{eid}", json={"score": ok}, headers=user_a.headers)
    assert r.status_code == 200
    assert float(r.json()["score"]) == float(ok)


def test_19_only_owner_can_score(client, user_a, user_b, experiment_id):
    eid, prompt = experiment_id
    # make it public so B can *see* it but still cannot score it
    client.patch(f"/api/v1/prompts/{prompt['prompt_id']}", json={"is_public": True}, headers=user_a.headers)
    r = client.patch(f"/api/v1/experiments/{eid}", json={"score": 5}, headers=user_b.headers)
    assert r.status_code == 403


# --------------------------------------------------------------------------- #
# 20 / 21  retrieval authorization                                          #
# --------------------------------------------------------------------------- #
def test_20_non_owner_cannot_retrieve_experiments_of_private_prompt(
    client, user_a, user_b, db_session, use_provider
):
    use_provider(FakeProvider())
    m = make_model(db_session)
    p = make_prompt(client, user_a, is_public=False)
    vid = p["versions"][0]["version_id"]
    eid = run(client, user_a, p["prompt_id"], vid, str(m.model_id)).json()["experiment_id"]

    assert client.get(f"{PROMPTS}/{p['prompt_id']}/experiments", headers=user_b.headers).status_code == 404
    assert client.get(f"{PROMPTS}/{p['prompt_id']}/versions/{vid}/experiments", headers=user_b.headers).status_code == 404
    assert client.get(f"/api/v1/experiments/{eid}", headers=user_b.headers).status_code == 404


def test_21_public_prompt_experiments_are_readable_by_others(
    client, user_a, user_b, db_session, use_provider
):
    use_provider(FakeProvider())
    m = make_model(db_session)
    p = make_prompt(client, user_a, is_public=True)
    vid = p["versions"][0]["version_id"]
    eid = run(client, user_a, p["prompt_id"], vid, str(m.model_id)).json()["experiment_id"]

    assert client.get(f"{PROMPTS}/{p['prompt_id']}/experiments", headers=user_b.headers).json()["total"] == 1
    assert client.get(f"{PROMPTS}/{p['prompt_id']}/versions/{vid}/experiments", headers=user_b.headers).status_code == 200
    assert client.get(f"/api/v1/experiments/{eid}", headers=user_b.headers).status_code == 200
    # ...but B still cannot run or score
    assert run(client, user_b, p["prompt_id"], vid, str(m.model_id)).status_code == 403


def test_experiment_requires_auth_for_retrieval(client, user_a, db_session, use_provider):
    use_provider(FakeProvider())
    m = make_model(db_session)
    p = make_prompt(client, user_a)
    eid = run(client, user_a, p["prompt_id"], p["versions"][0]["version_id"], str(m.model_id)).json()["experiment_id"]
    assert client.get(f"/api/v1/experiments/{eid}").status_code == 401
    assert client.get(f"{PROMPTS}/{p['prompt_id']}/experiments").status_code == 401


# --------------------------------------------------------------------------- #
# GET /models                                                               #
# --------------------------------------------------------------------------- #
def test_models_endpoint_reports_execution_configured(client, user_a, db_session):
    make_model(db_session, name="Echo", provider="mock")
    make_model(db_session, name="GPT-5", provider="OpenAI")
    rows = client.get("/api/v1/models", headers=user_a.headers).json()
    by_name = {r["name"]: r for r in rows}
    assert by_name["Echo"]["execution_configured"] is True     # mock provider on
    assert by_name["GPT-5"]["execution_configured"] is False    # no OPENAI_API_KEY
    assert "api_key" not in str(rows).lower()


def test_models_endpoint_requires_auth(client):
    assert client.get("/api/v1/models").status_code == 401


# --------------------------------------------------------------------------- #
# version content passed verbatim (not reconstructed from metadata)         #
# --------------------------------------------------------------------------- #
def test_provider_receives_only_version_content_not_title_or_description(
    client, user_a, db_session, use_provider
):
    fake = use_provider(FakeProvider())
    m = make_model(db_session)
    r = client.post(
        PROMPTS,
        json={
            "title": "TITLE SHOULD NOT APPEAR",
            "description": "DESC SHOULD NOT APPEAR",
            "content": "only this content",
            "is_public": False,
        },
        headers=user_a.headers,
    ).json()
    run(client, user_a, r["prompt_id"], r["versions"][0]["version_id"], str(m.model_id))
    assert fake.calls[0]["prompt_text"] == "only this content"
