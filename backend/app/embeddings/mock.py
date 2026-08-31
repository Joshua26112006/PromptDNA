"""Deterministic, dependency-free embedding provider for dev + tests.

**Not** a fake of a production model — it is a *controlled test embedding*
(the spec explicitly allows one). It is a normalised bag-of-hashed-tokens:
text that shares words produces vectors with higher cosine similarity, which is
enough to test relevance *ordering* without any external API or paid model.
Deterministic: the same text always yields the same vector.
"""

from __future__ import annotations

import hashlib
import math
import re

from app.embeddings.base import EmbeddingProvider

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class MockEmbeddingProvider(EmbeddingProvider):
    key = "mock"
    label = "PromptDNA Mock Embeddings"

    def __init__(self, *, dimension: int, model_name: str = "mock-hash-v1") -> None:
        self.dimension = dimension
        self.model_name = model_name

    def is_configured(self) -> bool:
        return True

    def embed(self, text: str, *, timeout_s: float) -> list[float]:
        vec = [0.0] * self.dimension
        tokens = _TOKEN_RE.findall(text.lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode()).digest()
            # spread each token across a few buckets with signed weights
            for i in range(0, 16, 4):
                bucket = int.from_bytes(digest[i : i + 4], "big") % self.dimension
                sign = 1.0 if digest[i] & 1 else -1.0
                vec[bucket] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            # empty / punctuation-only text -> a fixed unit vector
            vec[0] = 1.0
            return self._check_dim(vec)
        return self._check_dim([v / norm for v in vec])
