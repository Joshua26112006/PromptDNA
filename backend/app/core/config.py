"""Application configuration.

Settings are loaded from environment variables (and an optional `.env` file)
using ``pydantic-settings``. Nothing here is provider-specific: the embedding
provider and the databases are described only by connection strings / names so
they remain replaceable.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
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
    log_level: str = "INFO"

    # -- PostgreSQL: system of record (relational + pgvector) -----------
    # Required from Phase 2 onward for anything database-backed.
    database_url: str | None = None

    # SQLAlchemy engine pool sizing (kept modest for local development).
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_echo: bool = False

    # -- CORS ----------------------------------------------------------
    # Comma-separated list of allowed browser origins for local frontend dev.
    # NEVER set this to "*" while credentials are enabled.
    cors_origins: str = "http://localhost:3000"

    # -- Authentication (Phase 3) ------------------------------------
    # JWT_SECRET_KEY has NO default: auth operations fail clearly if it is
    # unset (no insecure fallback). Set it in the environment / .env.
    jwt_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # -- Neo4j: supporting graph projection (not used in Phase 0) -------
    neo4j_uri: str | None = None
    neo4j_username: str | None = None
    neo4j_password: str | None = None

    # -- Embedding provider abstraction --------------------------------
    # Provider name + credential only. The vector dimension is deliberately
    # NOT configured here; it is derived from the selected model later.
    embedding_provider: str | None = None
    embedding_api_key: str | None = None

    @field_validator("cors_origins")
    @classmethod
    def _reject_wildcard_cors(cls, value: str) -> str:
        if value.strip() == "*":
            raise ValueError(
                'cors_origins must be an explicit origin list, not "*" '
                "(credentials are enabled)."
            )
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""

    return Settings()
