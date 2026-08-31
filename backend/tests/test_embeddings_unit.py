"""Phase 6 — embedding provider abstraction (no database, no pgvector, no API).

Verifies the *controlled test embedding provider* and the similarity math that
semantic search relies on.
"""

from __future__ import annotations

import math

import pytest

from app.embeddings.base import EmbeddingDimensionMismatch
from app.embeddings.mock import MockEmbeddingProvider
from app.embeddings.registry import get_embedding_provider


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def test_mock_provider_is_deterministic_and_correct_dimension():
    p = MockEmbeddingProvider(dimension=1536)
    v1 = p.embed("summarize academic research papers", timeout_s=5)
    v2 = p.embed("summarize academic research papers", timeout_s=5)
    assert v1 == v2                    # deterministic
    assert len(v1) == 1536             # matches configured dimension
    assert abs(math.sqrt(sum(x * x for x in v1)) - 1.0) < 1e-6  # unit vector


def test_mock_provider_rejects_wrong_dimension_from_upstream():
    p = MockEmbeddingProvider(dimension=8)

    class Broken(MockEmbeddingProvider):
        def embed(self, text, *, timeout_s):
            return [0.0] * 999  # wrong length

    with pytest.raises(EmbeddingDimensionMismatch):
        Broken(dimension=8)._check_dim([0.0] * 999)
    assert len(p.embed("x", timeout_s=1)) == 8


def test_related_text_is_more_similar_than_unrelated():
    p = MockEmbeddingProvider(dimension=1536)
    a = p.embed("Summarize academic research papers and identify limitations.", timeout_s=5)
    b = p.embed("Create concise summaries of scholarly research articles.", timeout_s=5)
    c = p.embed("Write a Python function to sort a list of integers.", timeout_s=5)
    q = p.embed("Help me summarize scholarly research papers", timeout_s=5)

    # the query is closer to both summarization prompts than to the coding one
    assert _cos(q, a) > _cos(q, c)
    assert _cos(q, b) > _cos(q, c)


def test_registry_returns_mock_by_default(monkeypatch):
    from app.embeddings import registry

    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
    registry.reset_embedding_cache()
    from app.core.config import get_settings

    get_settings.cache_clear()
    p = get_embedding_provider()
    assert p.key == "mock"
    assert p.is_configured() is True
    get_settings.cache_clear()
    registry.reset_embedding_cache()
