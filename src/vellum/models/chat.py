"""Chat / watermark request and response shapes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WmParams(BaseModel):
    """Optional override for watermark payload fields."""

    schema_version: int | None = None
    issuer_id: int | None = None
    model_id: int | None = None
    model_version_id: int | None = None
    key_id: int | None = None
    repeat_interval_tokens: int | None = None


class ChatMessage(BaseModel):
    role: str
    content: str | list[dict[str, Any]]


class ChatRequest(BaseModel):
    """Request body for POST /api/chat."""

    messages: list[ChatMessage] = Field(default_factory=list)
    provider: str | None = None
    model: str | None = None
    system: str = "You are a helpful assistant."
    max_tokens: int = 2048
    temperature: float = 0.7
    watermark: bool = True
    wm_params: WmParams | None = None


class ChatResponse(BaseModel):
    text: str = ""
    raw_text: str = ""
    thinking: str = ""
    watermarked: bool = False
    model: str = ""
    provider: str = ""
    usage: dict[str, int] = Field(
        default_factory=lambda: {"input_tokens": 0, "output_tokens": 0}
    )
    error: str | None = None


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str


class ModelsResponse(BaseModel):
    google: list[ModelInfo] = Field(default_factory=list)
    minimax: list[ModelInfo] = Field(default_factory=list)
    bedrock: list[ModelInfo] = Field(default_factory=list)


class TextRequest(BaseModel):
    text: str
    wm_params: WmParams | None = None


class StripRequest(BaseModel):
    text: str


class WatermarkInfo(BaseModel):
    watermarked: bool = False
    tag_count: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    payloads: list[dict[str, Any]] = Field(default_factory=list)


class DetectResponse(BaseModel):
    text: str
    watermark: WatermarkInfo


class StripResponse(BaseModel):
    text: str
    stripped: str
    removed: int


class ApplyResponse(BaseModel):
    text: str
    watermarked: str
    payload_hex: str
