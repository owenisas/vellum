"""Typed enums used across config and runtime."""

from __future__ import annotations

from enum import StrEnum


class DemoMode(StrEnum):
    LIVE = "live"
    FIXTURE = "fixture"


class ChainBackendType(StrEnum):
    SIMULATED = "simulated"
    SOLANA = "solana"


class LLMProvider(StrEnum):
    GOOGLE = "google"
    MINIMAX = "minimax"
    BEDROCK = "bedrock"
    FIXTURE = "fixture"


class LogFormat(StrEnum):
    PRETTY = "pretty"
    JSON = "json"
