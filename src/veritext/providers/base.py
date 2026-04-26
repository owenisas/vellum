"""LLM provider Protocol + shared dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class GenerateRequest:
    prompt: str
    model: str
    max_tokens: int = 1024
    temperature: float = 0.7


@dataclass
class GenerateResult:
    text: str
    model: str
    provider: str
    usage: dict = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})
    thinking: str = ""


class LLMProvider(Protocol):
    name: str

    async def is_available(self) -> bool: ...

    async def generate(self, request: GenerateRequest) -> GenerateResult: ...

    async def list_models(self) -> list[dict]: ...
