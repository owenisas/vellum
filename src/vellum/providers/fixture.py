"""Deterministic fixture provider — used in DEMO_MODE=fixture and tests."""

from __future__ import annotations

from .base import GenerateRequest, GenerateResponse


FIXTURE_TEXT = (
    "Vellum fixture response: this output is deterministic for demo reliability. "
    "It can be watermarked, signed, anchored, and verified without calling external "
    "model APIs. The pipeline runs end-to-end exactly the same way it does with a "
    "real provider. Use this mode when you want a reproducible artifact."
)


def _extract_prompt(messages: list[dict]) -> str:
    parts: list[str] = []
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    parts.append(item.get("text", ""))
                else:
                    parts.append(str(item))
        elif content is not None:
            parts.append(str(content))
    return "\n".join(parts).strip()


class FixtureProvider:
    @property
    def provider_name(self) -> str:
        return "fixture"

    @property
    def available_models(self) -> list[dict[str, str]]:
        return [{"id": "fixture-default", "name": "Fixture (deterministic)", "provider": "fixture"}]

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        prompt = _extract_prompt(request.messages)
        text = (
            f"{FIXTURE_TEXT}\n\n"
            f"Requested model: {request.model or 'fixture-default'}.\n"
            f"Prompt digest: {prompt[:180]}"
        )
        return GenerateResponse(
            text=text,
            thinking="fixture-mode",
            model=request.model or "fixture-default",
            provider="fixture",
            usage={
                "input_tokens": max(1, len(prompt.split())),
                "output_tokens": max(1, len(text.split())),
            },
        )
