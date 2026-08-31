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

    # -- Experiments / AI model execution (Phase 5) ----------------
    # API keys for real providers. Absent -> that provider reports
    # "not configured" and execution against its models is refused cleanly
    # (no experiment row is created). Keys are never logged or returned.
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    # Hard cap on a single provider call. Chosen for local development —
    # production should tune this and add rate/cost controls.
    experiment_provider_timeout_s: float = 30.0
    # The built-in deterministic provider (provider name "mock"/"echo").
    # Enabled by default for local dev and tests; set false to disable.
    enable_mock_provider: bool = True

    # -- Neo4j: supporting graph projection (not used in Phase 0) -------
    neo4j_uri: str | None = None
    neo4j_username: str | None = None
    neo4j_password: str | None = None

    # -- Embeddings / semantic search (Phase 6) --------------------
    # Whether this deployment's PostgreSQL has the `vector` extension +
    # migration 0002. When False, the versions.embedding columns are not mapped
    # and semantic-search endpoints return a clear "not available" error —
    # everything else is unaffected. Set False only where pgvector is absent.
    pgvector_enabled: bool = True
    # Active embedding provider: "mock" (deterministic, dev/tests) or "openai".
    embedding_provider: str = "mock"
    embedding_api_key: str | None = None  # kept for back-compat; openai uses OPENAI_API_KEY
    # Vector dimension. MUST match the provider's output AND the
    # versions.embedding column fixed by migration 0002. 1536 = OpenAI
    # text-embedding-3-small; the mock provider is configured to match, so
    # switching to real OpenAI needs no migration.
    embedding_dimension: int = 1536
    embedding_model_name: str = "text-embedding-3-small"
    embedding_provider_timeout_s: float = 30.0
    # Best-effort embed on version create. Off by default (requires pgvector +
    # migration 0002); enable on a pgvector-capable deployment.
    embedding_autogenerate: bool = False

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
