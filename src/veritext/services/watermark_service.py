"""
Watermark service — combined detector that wraps the post-hoc Unicode tag
(`packages/watermark`) AND the optional generation-time SynthID layer
(`packages/genwatermark`).

Detection result: `present = unicode.detected OR statistical.watermarked`
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from genwatermark import StatisticalResult, detect_statistical
from watermark import DetectResult, Watermarker


@dataclass
class CombinedDetectResult:
    present: bool
    unicode: dict[str, Any]
    statistical: dict[str, Any] | None = None
    payloads: list[dict[str, Any]] = field(default_factory=list)


class WatermarkService:
    def __init__(self, *, genwatermark_enabled: bool = False) -> None:
        self._genwatermark_enabled = genwatermark_enabled

    def apply(
        self,
        text: str,
        *,
        issuer_id: int,
        model_id: int,
        model_version_id: int,
        key_id: int = 1,
        repeat_interval_tokens: int = 160,
        injection_mode: str = "whitespace",
    ) -> str:
        wm = Watermarker(
            issuer_id=issuer_id,
            model_id=model_id,
            model_version_id=model_version_id,
            key_id=key_id,
            repeat_interval_tokens=repeat_interval_tokens,
            injection_mode=injection_mode,
        )
        return wm.apply(text)

    def detect(self, text: str, *, model_id: str | None = None) -> CombinedDetectResult:
        wm_result = Watermarker().detect(text)
        unicode_dict = _result_to_dict(wm_result)
        payloads = [
            {
                "schema_version": p.schema_version,
                "issuer_id": p.issuer_id,
                "model_id": p.model_id,
                "model_version_id": p.model_version_id,
                "key_id": p.key_id,
                "code_valid": p.code_valid,
                "errors_corrected": p.errors_corrected,
                "raw_payload_hex": p.raw_payload_hex,
            }
            for p in wm_result.payloads
        ]
        statistical = None
        if self._genwatermark_enabled:
            stat: StatisticalResult = detect_statistical(text, model_id=model_id)
            statistical = {
                "type": stat.method,
                "present": stat.present,
                "detector_score": stat.score,
                "p_value": stat.p_value,
            }
        present = wm_result.watermarked or bool(statistical and statistical.get("present"))
        return CombinedDetectResult(
            present=present,
            unicode=unicode_dict,
            statistical=statistical,
            payloads=payloads,
        )

    @staticmethod
    def strip(text: str) -> str:
        return Watermarker.strip(text)


def _result_to_dict(r: DetectResult) -> dict[str, Any]:
    return {
        "detected": r.watermarked,
        "tag_count": r.tag_count,
        "valid_count": r.valid_count,
        "invalid_count": r.invalid_count,
    }
