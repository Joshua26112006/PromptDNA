"""Deterministic in-process provider for local development and tests.

This is **not** a fake of any real vendor — it is its own provider whose
``models.provider`` value is ``"mock"``. It never pretends a failed call
succeeded. It exists so the experiment pipeline can be exercised end-to-end
without paid API access. Disable with ``ENABLE_MOCK_PROVIDER=false``.
"""

from __future__ import annotations

from app.providers.base import LLMProvider

_MAX_ECHO = 4000


class MockProvider(LLMProvider):
    key = "mock"
    label = "PromptDNA Mock"

    def is_configured(self) -> bool:
        return True

    def generate(self, *, model_name: str, prompt_text: str, timeout_s: float) -> str:
        # A deterministic, obviously-synthetic transformation of the input so
        # tests can assert the exact version content reached the provider.
        body = prompt_text.strip()[:_MAX_ECHO]
        return (
            f"[mock:{model_name}] echo of {len(prompt_text)} chars\n"
            f"---\n{body}"
        )
