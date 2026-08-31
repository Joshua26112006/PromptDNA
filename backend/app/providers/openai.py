"""OpenAI Chat Completions provider.

Real integration. Only ever runs when ``OPENAI_API_KEY`` is set — otherwise
:meth:`is_configured` returns False and the experiment service refuses the run
with a clean configuration error (no experiment row created, no key logged).

Adding Anthropic / Google providers is the same shape: a subclass with its own
``is_configured`` + ``generate``, registered in ``registry.py``.
"""

from __future__ import annotations

import logging

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


class OpenAIProvider(LLMProvider):
    key = "openai"
    label = "OpenAI"

    def is_configured(self) -> bool:
        return bool(get_settings().openai_api_key)

    def generate(self, *, model_name: str, prompt_text: str, timeout_s: float) -> str:
        settings = get_settings()
        api_key = settings.openai_api_key
        if not api_key:
            raise ProviderNotConfigured(
                "OpenAI execution is not configured on this server."
            )

        url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt_text}],
        }
        try:
            with httpx.Client(timeout=timeout_s) as client:
                resp = client.post(
                    url,
                    json=payload,
                    headers={"Authorization": f"Bearer {api_key}"},
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
