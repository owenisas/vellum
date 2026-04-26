"""Unit tests for the deterministic FixtureProvider and ProviderRouter."""

from __future__ import annotations

from vellum.config import LLMSettings
from vellum.providers.base import GenerateRequest
from vellum.providers.fixture import FixtureProvider
from vellum.providers.router import ProviderRouter


def _request(prompt: str = "hi") -> GenerateRequest:
    return GenerateRequest(
        model="fixture-default",
        messages=[{"role": "user", "content": prompt}],
    )


async def test_fixture_provider_deterministic():
    provider = FixtureProvider()
    a = await provider.generate(_request("identical prompt"))
    b = await provider.generate(_request("identical prompt"))

    assert a.text == b.text
    assert a.thinking == b.thinking
    assert "Placeholder response for the demo" in a.text
    assert "Placeholder reasoning summary" in a.thinking
    assert a.usage == b.usage
    assert a.provider == "fixture"
    assert a.model == "fixture-default"


async def test_router_fixture_only():
    settings = LLMSettings()
    router = ProviderRouter(settings, fixture_only=True)

    # No real providers should be exposed via list_models()
    assert router.list_models() == {}

    # Resolve always falls back to fixture in fixture_only mode
    assert router.resolve("google") == "fixture"
    assert router.resolve(None) == "fixture"
    assert router.resolve("nonexistent") == "fixture"

    response = await router.generate("google", _request())
    assert response.provider == "fixture"
    assert response.error is None
    assert response.text  # non-empty


async def test_router_unknown_provider_returns_error():
    settings = LLMSettings()  # no api keys configured
    router = ProviderRouter(settings, fixture_only=False)

    # router.resolve() falls back to settings.default_provider when the requested
    # name isn't registered, so to truly hit "unknown provider" we strip the
    # fallback registrations first.
    router._providers.pop(settings.default_provider.value, None)
    router._providers.pop("bedrock", None)
    router._providers.pop("google", None)
    router._providers.pop("minimax", None)

    response = await router.generate("does-not-exist-provider", _request())
    assert response.error is not None
    assert "Unknown provider" in response.error


async def test_fixture_provider_includes_prompt_digest():
    provider = FixtureProvider()
    response = await provider.generate(_request("alpha-beta-gamma"))
    assert "alpha-beta-gamma" in response.text
