"""Application configuration.

Settings are loaded from environment variables (and an optional `.env` file)
using ``pydantic-settings``. Nothing here is provider-specific: the embedding
provider and the databases are described only by connection strings / names so
they remain replaceable.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> repo root is three parents up.
_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Typed application settings."""

    model_config = SettingsConfigDict(
        # Look for a repo-root `.env` first, then a backend-local one.
        env_file=(str(_REPO_ROOT / ".env"), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -- Application ------------------------------------------------------
    app_name: str = "PromptDNA API"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # -- PostgreSQL: system of record (relational + pgvector) -----------
    # Optional in Phase 0 — there is no schema yet.
    database_url: str | None = None

    # -- Neo4j: supporting graph projection (not used in Phase 0) -------
    neo4j_uri: str | None = None
    neo4j_username: str | None = None
    neo4j_password: str | None = None

    # -- Embedding provider abstraction --------------------------------
    # Provider name + credential only. The vector dimension is deliberately
    # NOT configured here; it is derived from the selected model later.
    embedding_provider: str | None = None
    embedding_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""

    return Settings()
