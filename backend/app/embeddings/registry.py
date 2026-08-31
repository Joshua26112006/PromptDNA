"""Selects the single active :class:`EmbeddingProvider` from configuration.

Unlike LLM providers (one per model row), there is exactly one embedding
provider per deployment — every embedding in ``versions.embedding`` must come
from the same model / dimension to be comparable.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.embeddings.base import EmbeddingProvider
from app.embeddings.mock import MockEmbeddingProvider
from app.embeddings.openai import OpenAIEmbeddingProvider


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    dim = settings.embedding_dimension
    name = settings.embedding_provider.strip().lower()
    if name == "openai":
        return OpenAIEmbeddingProvider(
            dimension=dim, model_name=settings.embedding_model_name
        )
    return MockEmbeddingProvider(dimension=dim)


def get_embedding_dimension() -> int:
    return get_settings().embedding_dimension


def reset_embedding_cache() -> None:
    get_embedding_provider.cache_clear()
