"""Smoke tests for the Phase 0 application shell."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"]
    assert "running" in body["message"].lower()


def test_root_returns_metadata() -> None:
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["health"] == "/health"
