"""Deterministic fixture provider — used in demo mode and tests."""

from __future__ import annotations

from .base import GenerateRequest, GenerateResult


FIXTURE_TEXT = (
    "Veritext fixture response: this output is deterministic and used for "
    "demos and tests. The Veritext system signs this text with a per-issuer "
    "ECDSA key and anchors a SHA-256 hash to a chain of choice. The "
    "watermark library inserts invisible Unicode tags so this text can be "
    "verified for tampering after distribution."
)


class FixtureProvider:
    name = "fixture"

    async def is_available(self) -> bool:
        return True

    async def generate(self, request: GenerateRequest) -> GenerateResult:
        return GenerateResult(
            text=FIXTURE_TEXT,
            model=request.model or "fixture",
            provider="fixture",
            usage={"input_tokens": len(request.prompt.split()), "output_tokens": len(FIXTURE_TEXT.split())},
        )

    async def list_models(self) -> list[dict]:
        return [{"id": "fixture", "name": "Fixture (deterministic)", "provider": "fixture"}]
