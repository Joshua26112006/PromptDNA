"""Provider interface + typed failure modes.

A provider turns ``(model_name, prompt_text)`` into generated text, or raises a
:class:`ProviderError`. It does **not** touch the database and does **not**
measure its own timing — the experiment service times the call with
``time.perf_counter()`` and records the result.
"""

from __future__ import annotations

import abc


class ProviderError(Exception):
    """Base class for all provider execution failures.

    ``safe_message`` is what may be stored in ``experiments.error_message`` and
    shown to clients — it must never contain API keys, auth headers, or full
    raw provider payloads.
    """

    def __init__(self, safe_message: str) -> None:
        super().__init__(safe_message)
        self.safe_message = safe_message


class ProviderNotConfigured(ProviderError):
    """The provider exists but has no usable credentials/config on this server."""


class ProviderTimeout(ProviderError):
    """The provider call exceeded the configured timeout."""


class ProviderRequestError(ProviderError):
    """The provider returned an HTTP error or a malformed/empty response."""


class LLMProvider(abc.ABC):
    """One executable model provider (maps to a ``models.provider`` value)."""

    #: canonical lower-case key, e.g. "openai", "mock"
    key: str
    #: human label, e.g. "OpenAI"
    label: str

    @abc.abstractmethod
    def is_configured(self) -> bool:
        """True if a real call could be attempted (e.g. an API key is set)."""

    @abc.abstractmethod
    def generate(self, *, model_name: str, prompt_text: str, timeout_s: float) -> str:
        """Run ``prompt_text`` against ``model_name`` and return the output text.

        Raises a :class:`ProviderError` subclass on any failure. Must not return
        a fabricated success if the underlying call failed.
        """
