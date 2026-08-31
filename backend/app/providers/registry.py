"""Maps a ``models.provider`` string to an :class:`LLMProvider` instance.

A ``models`` row only *describes* a model. Execution needs a provider that is
both **registered** here and **configured** (``is_configured()``). GPT-5 /
Claude / Gemini seed rows have registered providers but are unconfigured
without API keys, so runs against them fail cleanly with a config error.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.providers.base import LLMProvider
from app.providers.mock import MockProvider
from app.providers.openai import OpenAIProvider


@lru_cache
def _registry() -> dict[str, LLMProvider]:
    providers: list[LLMProvider] = [OpenAIProvider()]
    if get_settings().enable_mock_provider:
        providers.append(MockProvider())

    table: dict[str, LLMProvider] = {}
    for provider in providers:
        table[provider.key] = provider
    # convenience aliases
    if "mock" in table:
        table.setdefault("echo", table["mock"])
        table.setdefault("promptdna mock", table["mock"])
    return table


def get_provider(provider_name: str) -> LLMProvider | None:
    """Return the provider for a ``models.provider`` value, or ``None``."""

    return _registry().get(provider_name.strip().lower())


def reset_registry_cache() -> None:
    """Test hook: rebuild the registry after changing settings."""

    _registry.cache_clear()
