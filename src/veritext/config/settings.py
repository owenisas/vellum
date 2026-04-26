"""Pydantic Settings for Veritext, env-driven."""

from __future__ import annotations

from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env into os.environ once at import time so sub-model BaseSettings
# instances can read env vars without each one re-reading the file.
load_dotenv(override=False)

from .enums import (
    AnchorStrategy,
    ChainBackendType,
    DemoMode,
    PayloadVisibility,
    WatermarkInjectionMode,
)


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    auth0_domain: str = ""
    auth0_audience: str = "https://api.veritext.io"
    auth0_spa_client_id: str = ""
    jwks_cache_ttl_seconds: int = 300


class SolanaSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    solana_rpc_url: str = "https://api.devnet.solana.com"
    solana_keypair_path: str = ""
    solana_cluster: str = "devnet"
    merkle_batch_window_seconds: int = 10
    merkle_batch_max_leaves: int = 64


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    google_api_key: str = ""


class WatermarkSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    payload_visibility: PayloadVisibility = PayloadVisibility.PLAINTEXT
    watermark_injection_mode: WatermarkInjectionMode = WatermarkInjectionMode.WHITESPACE
    watermark_encryption_key: str = ""  # 32 hex chars / 16 bytes when encrypted
    genwatermark_enabled: bool = False


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="",
    )

    # Core
    demo_mode: DemoMode = DemoMode.LIVE
    registry_admin_secret: str = "dev-admin-secret-change-me"

    # Server
    app_host: str = "127.0.0.1"
    app_port: int = 5050
    cors_origins: str = "http://localhost:5173,http://localhost:5050"
    log_level: str = "info"
    log_format: str = "pretty"  # pretty | json

    # Database
    db_path: str = "data/veritext.db"

    # Chain
    chain_backend: ChainBackendType = ChainBackendType.SIMULATED
    anchor_strategy: AnchorStrategy = AnchorStrategy.PER_RESPONSE

    # Sub-models
    auth: AuthSettings = Field(default_factory=AuthSettings)
    solana: SolanaSettings = Field(default_factory=SolanaSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    watermark: WatermarkSettings = Field(default_factory=WatermarkSettings)

    @field_validator("cors_origins")
    @classmethod
    def _split_origins(cls, v: str) -> str:  # kept as raw string; consumer splits
        return v

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validate_solana_keypair(self) -> None:
        if self.chain_backend == ChainBackendType.SOLANA and not self.solana.solana_keypair_path:
            raise ValueError("SOLANA_KEYPAIR_PATH required when CHAIN_BACKEND=solana")

    def auth0_enabled(self) -> bool:
        return bool(self.auth.auth0_domain)


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()
