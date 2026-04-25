"""Thin wrapper around `packages/watermark` so services can swap impls easily."""

from __future__ import annotations

from watermark import DetectResult, Watermarker

from vellum.models.chat import WmParams


def _build_watermarker(params: WmParams | None) -> Watermarker:
    p = params.model_dump(exclude_none=True) if params else {}
    return Watermarker(
        schema_version=p.get("schema_version", 1),
        issuer_id=p.get("issuer_id", 1),
        model_id=p.get("model_id", 0),
        model_version_id=p.get("model_version_id", 0),
        key_id=p.get("key_id", 1),
        repeat_interval_tokens=p.get("repeat_interval_tokens", 160),
    )


class WatermarkService:
    """Apply / detect / strip with optional per-call overrides."""

    def apply(self, text: str, params: WmParams | None = None) -> str:
        return _build_watermarker(params).apply(text)

    def detect(self, text: str) -> DetectResult:
        return Watermarker.detect_text(text)

    def strip(self, text: str) -> str:
        return Watermarker.strip(text)

    def watermarker_for(self, params: WmParams | None) -> Watermarker:
        return _build_watermarker(params)
