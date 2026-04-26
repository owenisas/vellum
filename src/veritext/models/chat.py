from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WatermarkParams(BaseModel):
    issuer_id: int = 1
    model_id: int = 0
    model_version_id: int = 0
    key_id: int = 1
    repeat_interval_tokens: int = 160


class ChatRequest(BaseModel):
    prompt: str
    model: str = "fixture"
    provider: str = "fixture"
    watermark: bool = True
    watermark_params: WatermarkParams | None = None


class ChatResponse(BaseModel):
    text: str
    raw_text: str
    thinking: str = ""
    watermarked: bool
    model: str
    provider: str
    usage: dict[str, int] = Field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})
    error: str | None = None


class ApplyRequest(BaseModel):
    text: str
    watermark_params: WatermarkParams | None = None


class ApplyResponse(BaseModel):
    text: str
    watermarked_text: str


class DetectRequest(BaseModel):
    text: str


class DetectResponse(BaseModel):
    watermarked: bool
    tag_count: int
    valid_count: int
    invalid_count: int
    payloads: list[dict[str, Any]]
    statistical: dict[str, Any] | None = None  # genwatermark result


class StripRequest(BaseModel):
    text: str


class StripResponse(BaseModel):
    text: str
    stripped_count: int


class ModelEntry(BaseModel):
    id: str
    name: str
    provider: str


class ModelsResponse(BaseModel):
    models: list[ModelEntry]
