"""Provider Protocol + request/response dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class GenerateRequest:
    model: str
    messages: list[dict[str, Any]]
    system: str = "You are a helpful assistant."
    max_tokens: int = 2048
    temperature: float = 0.7


@dataclass
class GenerateResponse:
    text: str = ""
    thinking: str = ""
    model: str = ""
    provider: str = ""
    usage: dict[str, int] = field(
        default_factory=lambda: {"input_tokens": 0, "output_tokens": 0}
    )
    error: str | None = None


@runtime_checkable
class LLMProvider(Protocol):
    """Every LLM provider implements this protocol."""

    @property
    def provider_name(self) -> str: ...

    @property
    def available_models(self) -> list[dict[str, str]]: ...

    async def generate(self, request: GenerateRequest) -> GenerateResponse: ...
