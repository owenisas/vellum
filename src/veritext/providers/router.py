"""Provider router — picks the right provider for a request."""

from __future__ import annotations

from .base import GenerateRequest, GenerateResult
from .fixture import FixtureProvider
from .google import GoogleProvider


class ProviderRouter:
    def __init__(self, *, google: GoogleProvider | None = None, fixture: FixtureProvider | None = None) -> None:
        self._google = google or GoogleProvider(api_key="")
        self._fixture = fixture or FixtureProvider()

    def _select(self, provider: str):
        if provider == "google":
            return self._google
        return self._fixture

    async def generate(self, *, provider: str, request: GenerateRequest) -> GenerateResult:
        return await self._select(provider).generate(request)

    async def list_all_models(self) -> list[dict]:
        models = []
        if await self._google.is_available():
            models.extend(await self._google.list_models())
        models.extend(await self._fixture.list_models())
        return models
