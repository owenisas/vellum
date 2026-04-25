"""ProviderRouter — registers providers and dispatches generate requests."""

from __future__ import annotations

import logging

from vellum.config import LLMSettings

from .base import GenerateRequest, GenerateResponse, LLMProvider
from .bedrock import BedrockProvider
from .fixture import FixtureProvider
from .google import GoogleProvider
from .minimax import MiniMaxProvider

logger = logging.getLogger(__name__)


class ProviderRouter:
    """Registers all available providers based on config and dispatches calls."""

    def __init__(self, settings: LLMSettings, fixture_only: bool = False) -> None:
        self.settings = settings
        self._providers: dict[str, LLMProvider] = {}
        self._fixture_only = fixture_only
        self._register_defaults(settings, fixture_only=fixture_only)

    def _register_defaults(self, settings: LLMSettings, *, fixture_only: bool) -> None:
        # Always register fixture
        self._providers["fixture"] = FixtureProvider()

        if fixture_only:
            return

        if settings.google_api_key:
            self._providers["google"] = GoogleProvider(settings.google_api_key)
        if settings.minimax_api_key:
            self._providers["minimax"] = MiniMaxProvider(
                settings.minimax_api_key, settings.minimax_base_url
            )
        # Bedrock — let it lazy-fail on credential issues, but expose models
        self._providers["bedrock"] = BedrockProvider()

    def register(self, name: str, provider: LLMProvider) -> None:
        self._providers[name] = provider

    def has(self, name: str) -> bool:
        return name in self._providers

    def list_providers(self) -> list[str]:
        return [p for p in self._providers.keys() if p != "fixture"]

    def list_models(self) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        for name, provider in self._providers.items():
            if name == "fixture":
                continue
            out[name] = list(provider.available_models)
        return out

    def resolve(self, provider: str | None) -> str:
        """Pick a default provider when caller omits one."""
        if self._fixture_only:
            return "fixture"
        if provider and provider in self._providers:
            return provider
        return self.settings.default_provider.value

    async def generate(
        self, provider: str | None, request: GenerateRequest
    ) -> GenerateResponse:
        chosen = self.resolve(provider)
        if chosen not in self._providers:
            return GenerateResponse(
                provider=chosen,
                model=request.model,
                error=f"Unknown provider: {chosen}",
            )
        if not request.model:
            request.model = self.settings.default_model
        return await self._providers[chosen].generate(request)
