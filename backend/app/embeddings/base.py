"""Embedding provider interface + typed failures."""

from __future__ import annotations

import abc


class EmbeddingError(Exception):
    """Base for embedding failures. ``safe_message`` is all that is surfaced."""

    def __init__(self, safe_message: str) -> None:
        super().__init__(safe_message)
        self.safe_message = safe_message


class EmbeddingNotConfigured(EmbeddingError):
    """No usable credentials/config for the active provider."""


class EmbeddingTimeout(EmbeddingError):
    """The embedding call exceeded the configured timeout."""


class EmbeddingRequestError(EmbeddingError):
    """HTTP error or malformed/empty response from the provider."""


class EmbeddingDimensionMismatch(EmbeddingError):
    """The provider returned a vector of the wrong length."""


class EmbeddingProvider(abc.ABC):
    """Turns text into a fixed-length float vector."""

    key: str
    label: str
    model_name: str
    dimension: int

    @abc.abstractmethod
    def is_configured(self) -> bool: ...

    @abc.abstractmethod
    def embed(self, text: str, *, timeout_s: float) -> list[float]:
        """Return one embedding for ``text``. Raises :class:`EmbeddingError`."""

    def _check_dim(self, vector: list[float]) -> list[float]:
        if len(vector) != self.dimension:
            raise EmbeddingDimensionMismatch(
                f"Embedding provider returned {len(vector)} dimensions, "
                f"expected {self.dimension}."
            )
        return vector
