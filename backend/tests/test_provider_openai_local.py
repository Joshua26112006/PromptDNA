"""OpenAIProvider configuration: real OpenAI vs. a local Ollama-compatible server.

No network and no running Ollama: ``httpx.Client`` is replaced by a fake.
"""

from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.providers import openai as openai_module
from app.providers.base import ProviderNotConfigured, ProviderRequestError
from app.providers.openai import OpenAIProvider, _is_local_endpoint


@pytest.fixture
def configure(monkeypatch):
    def _set(*, base_url: str, api_key: str | None) -> None:
        monkeypatch.setenv("OPENAI_BASE_URL", base_url)
        if api_key is None:
            monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        else:
            monkeypatch.setenv("OPENAI_API_KEY", api_key)
        get_settings.cache_clear()

    yield _set
    get_settings.cache_clear()


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def _fake_client(calls: list, response: _FakeResponse):
    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, json=None, headers=None):
            calls.append({"url": url, "json": json, "headers": headers})
            return response

    return _Client


OK = _FakeResponse(200, {"choices": [{"message": {"content": "hello from the model"}}]})


@pytest.mark.parametrize(
    "url,expected",
    [
        ("http://localhost:11434/v1", True),
        ("http://127.0.0.1:11434/v1", True),
        ("http://[::1]:11434/v1", True),
        ("https://api.openai.com/v1", False),
        ("https://localhost.evil.example/v1", False),
        ("not a url", False),
    ],
)
def test_local_endpoint_detection(url, expected):
    assert _is_local_endpoint(url) is expected


def test_real_openai_still_requires_a_key(configure):
    configure(base_url="https://api.openai.com/v1", api_key=None)
    p = OpenAIProvider()
    assert p.is_configured() is False
    with pytest.raises(ProviderNotConfigured):
        p.generate(model_name="gpt-x", prompt_text="hi", timeout_s=5)


def test_real_openai_with_key_is_configured_and_sends_bearer(configure, monkeypatch):
    configure(base_url="https://api.openai.com/v1", api_key="sk-test-not-real")
    calls: list = []
    monkeypatch.setattr(openai_module.httpx, "Client", _fake_client(calls, OK))
    p = OpenAIProvider()
    assert p.is_configured() is True
    assert p.generate(model_name="gpt-x", prompt_text="hi", timeout_s=5) == "hello from the model"
    assert calls[0]["headers"] == {"Authorization": "Bearer sk-test-not-real"}
    assert calls[0]["url"] == "https://api.openai.com/v1/chat/completions"


def test_local_ollama_needs_no_key_and_sends_no_auth_header(configure, monkeypatch):
    configure(base_url="http://localhost:11434/v1", api_key=None)
    calls: list = []
    monkeypatch.setattr(openai_module.httpx, "Client", _fake_client(calls, OK))
    p = OpenAIProvider()
    assert p.is_configured() is True
    out = p.generate(model_name="gemma3:4b", prompt_text="hi", timeout_s=5)
    assert out == "hello from the model"
    assert calls[0]["url"] == "http://localhost:11434/v1/chat/completions"
    assert calls[0]["json"]["model"] == "gemma3:4b"
    assert calls[0]["headers"] == {}


def test_local_endpoint_http_error_is_not_reported_as_success(configure, monkeypatch):
    configure(base_url="http://localhost:11434/v1", api_key=None)
    monkeypatch.setattr(
        openai_module.httpx, "Client", _fake_client([], _FakeResponse(404, {"error": "x"}))
    )
    with pytest.raises(ProviderRequestError):
        OpenAIProvider().generate(model_name="nope", prompt_text="hi", timeout_s=5)
