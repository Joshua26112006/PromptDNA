"""OpenAI embeddings provider (real; needs OPENAI_API_KEY).

Default model ``text-embedding-3-small`` -> 1536 dimensions. Only ever runs when
a key is set; otherwise :meth:`is_configured` is False and the semantic-search
endpoints report a clear configuration error. The key is never logged/returned.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import get_settings
from app.embeddings.base import (
    EmbeddingNotConfigured,
    EmbeddingProvider,
    EmbeddingRequestError,
    EmbeddingTimeout,
)

logger = logging.getLogger("promptdna")


class OpenAIEmbeddingProvider(EmbeddingProvider):
    key = "openai"
    label = "OpenAI Embeddings"

    def __init__(self, *, dimension: int, model_name: str) -> None:
        self.dimension = dimension
        self.model_name = model_name

    def is_configured(self) -> bool:
        return bool(get_settings().openai_api_key)

    def embed(self, text: str, *, timeout_s: float) -> list[float]:
        settings = get_settings()
        api_key = settings.openai_api_key
        if not api_key:
            raise EmbeddingNotConfigured(
                "OpenAI embeddings are not configured on this server."
            )
        url = f"{settings.openai_base_url.rstrip('/')}/embeddings"
        try:
            with httpx.Client(timeout=timeout_s) as client:
                resp = client.post(
                    url,
                    json={"model": self.model_name, "input": text},
                    headers={"Authorization": f"Bearer {api_key}"},
                )
        except httpx.TimeoutException as exc:
            raise EmbeddingTimeout(
                f"OpenAI embeddings timed out after {timeout_s:g}s."
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning("OpenAI embeddings transport error: %s", type(exc).__name__)
            raise EmbeddingRequestError("Could not reach the OpenAI API.") from exc

        if resp.status_code >= 400:
            logger.warning("OpenAI embeddings HTTP %s", resp.status_code)
            raise EmbeddingRequestError(
                f"OpenAI API returned HTTP {resp.status_code}."
            )
        try:
            vector = resp.json()["data"][0]["embedding"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise EmbeddingRequestError(
                "OpenAI API returned a malformed embedding response."
            ) from exc
        return self._check_dim([float(x) for x in vector])
