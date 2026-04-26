"""Pydantic Settings — typed, grouped, and validated config."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .enums import ChainBackendType, DemoMode, LLMProvider, LogFormat


class AuthSettings(BaseSettings):
    """Auth0 configuration. All optional — empty domain disables Auth0."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    auth0_domain: str = Field(default="", alias="AUTH0_DOMAIN")
    auth0_audience: str = Field(default="https://api.vellum.io", alias="AUTH0_AUDIENCE")
    auth0_algorithms: str = Field(default="RS256", alias="AUTH0_ALGORITHMS")
    auth0_spa_client_id: str = Field(default="", alias="AUTH0_SPA_CLIENT_ID")

    @property
    def enabled(self) -> bool:
        return bool(self.auth0_domain)

    @property
    def issuer(self) -> str:
        return f"https://{self.auth0_domain}/" if self.auth0_domain else ""

    @property
    def algorithms_list(self) -> list[str]:
        return [a.strip() for a in self.auth0_algorithms.split(",") if a.strip()]


class SolanaSettings(BaseSettings):
    """Solana configuration. Only active when chain_backend=solana."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    solana_rpc_url: str = Field(default="https://api.devnet.solana.com", alias="SOLANA_RPC_URL")
    solana_keypair_path: str = Field(default="", alias="SOLANA_KEYPAIR_PATH")
    solana_cluster: str = Field(default="devnet", alias="SOLANA_CLUSTER")


class LLMSettings(BaseSettings):
    """LLM provider API keys and endpoints."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    minimax_api_key: str = Field(default="", alias="MINIMAX_API_KEY")
    minimax_base_url: str = Field(
        default="https://api.minimax.io/anthropic", alias="MINIMAX_BASE_URL"
    )
    default_provider: LLMProvider = Field(default=LLMProvider.GOOGLE, alias="DEFAULT_PROVIDER")
    default_model: str = Field(default="gemma-4-27b-it", alias="DEFAULT_MODEL")


class AppSettings(BaseSettings):
    """Top-level application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core
    demo_mode: DemoMode = Field(default=DemoMode.LIVE, alias="DEMO_MODE")
    chain_backend: ChainBackendType = Field(
        default=ChainBackendType.SIMULATED, alias="CHAIN_BACKEND"
    )
    registry_admin_secret: str = Field(default="dev-admin-secret", alias="REGISTRY_ADMIN_SECRET")

    # Server
    host: str = Field(default="127.0.0.1", alias="APP_HOST")
    port: int = Field(default=5050, alias="APP_PORT")
    cors_origins_raw: str = Field(
        default="http://localhost:5173,http://localhost:5050",
        alias="CORS_ORIGINS",
    )
    log_level: str = Field(default="info", alias="LOG_LEVEL")
    log_format: LogFormat = Field(default=LogFormat.PRETTY, alias="LOG_FORMAT")

    # Database
    db_path: str = Field(default="data/vellum.db", alias="DB_PATH")

    # Sub-configs
    auth: AuthSettings = Field(default_factory=AuthSettings)
    solana: SolanaSettings = Field(default_factory=SolanaSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, v: str) -> str:
        return str(v).lower()

    @model_validator(mode="after")
    def _validate_solana_keypair(self) -> "AppSettings":
        if (
            self.chain_backend == ChainBackendType.SOLANA
            and not self.solana.solana_keypair_path
        ):
            raise ValueError("SOLANA_KEYPAIR_PATH required when CHAIN_BACKEND=solana")
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]

    @property
    def is_fixture_mode(self) -> bool:
        return self.demo_mode == DemoMode.FIXTURE


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Cached settings accessor — used by FastAPI dependencies."""
    return AppSettings()


def reload_settings() -> AppSettings:
    """Clear cache and reload (used by tests that change env vars)."""
    get_settings.cache_clear()
    return get_settings()
