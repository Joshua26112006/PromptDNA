"""OpenAI Chat Completions provider.

Real integration. Runs when ``OPENAI_API_KEY`` is set — otherwise
:meth:`is_configured` returns False and the experiment service refuses the run
with a clean configuration error (no experiment row created, no key logged).

**Local Ollama / OpenAI-compatible servers:** if ``OPENAI_BASE_URL`` points at
this machine (localhost / 127.0.0.1 / ::1) no API key is required, and no
``Authorization`` header is sent unless a key is set. A non-local base URL
(including the OpenAI default) still requires ``OPENAI_API_KEY`` exactly as
before.

Adding Anthropic / Google providers is the same shape: a subclass with its own
``is_configured`` + ``generate``, registered in ``registry.py``.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.providers.base import (
    LLMProvider,
    ProviderNotConfigured,
    ProviderRequestError,
    ProviderTimeout,
)

logger = logging.getLogger("promptdna")

_MAX_ERROR_LEN = 300
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _is_local_endpoint(base_url: str) -> bool:
    """True if ``base_url`` targets this machine (e.g. a local Ollama server)."""

    try:
        return (urlparse(base_url).hostname or "").lower() in _LOCAL_HOSTS
    except ValueError:
        return False


class OpenAIProvider(LLMProvider):
    key = "openai"
    label = "OpenAI"

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(settings.openai_api_key) or _is_local_endpoint(
            settings.openai_base_url
        )

    def generate(self, *, model_name: str, prompt_text: str, timeout_s: float) -> str:
        settings = get_settings()
        api_key = settings.openai_api_key
        if not api_key and not _is_local_endpoint(settings.openai_base_url):
            raise ProviderNotConfigured(
                "OpenAI execution is not configured on this server."
            )

        url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt_text}],
        }
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        try:
            with httpx.Client(timeout=timeout_s) as client:
                resp = client.post(
                    url,
                    json=payload,
                    headers=headers,
                )
        except httpx.TimeoutException as exc:
            raise ProviderTimeout(
                f"OpenAI request timed out after {timeout_s:g}s."
            ) from exc
        except httpx.HTTPError as exc:
            # Never include the exception repr (could echo the request URL/headers).
            logger.warning("OpenAI transport error: %s", type(exc).__name__)
            raise ProviderRequestError("Could not reach the OpenAI API.") from exc

        if resp.status_code >= 400:
            # Log status only; do not store/return the raw error body.
            logger.warning("OpenAI HTTP %s", resp.status_code)
            raise ProviderRequestError(
                f"OpenAI API returned HTTP {resp.status_code}."
            )

        try:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderRequestError(
                "OpenAI API returned a malformed response."
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise ProviderRequestError("OpenAI API returned an empty response.")
        return content[: 100_000]
