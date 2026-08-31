"""AI model execution behind a provider abstraction.

The experiment service depends only on :class:`LLMProvider` — it never knows a
provider's HTTP details. Look providers up by their name (which matches
``models.provider``) via :func:`app.providers.registry.get_provider`.
"""
