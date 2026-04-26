"""
Veritext zero-width watermarking library.

Public API:
    Watermarker(...).apply(text)         -> watermarked text
    Watermarker(...).detect(text)        -> DetectResult
    Watermarker.strip(text)              -> text with all tags removed
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from . import payload as _pay
from .payload import Payload
from .streaming import TagInjector
from .zero_width import (
    InjectionMode,
    decode_tag,
    encode_bits,
    find_tags,
    strip_all,
)


__all__ = [
    "Watermarker",
    "DetectResult",
    "PayloadInfo",
    "InjectionMode",
    "Payload",
]


@dataclass
class PayloadInfo:
    schema_version: int
    issuer_id: int
    model_id: int
    model_version_id: int
    key_id: int
    code_valid: bool
    errors_corrected: int
    raw_payload_hex: str


@dataclass
class DetectResult:
    watermarked: bool
    tag_count: int
    valid_count: int
    invalid_count: int
    payloads: list[PayloadInfo] = field(default_factory=list)


class Watermarker:
    def __init__(
        self,
        *,
        schema_version: int = 1,
        issuer_id: int = 1,
        model_id: int = 0,
        model_version_id: int = 0,
        key_id: int = 1,
        repeat_interval_tokens: int = 160,
        injection_mode: InjectionMode | str = InjectionMode.WHITESPACE,
    ) -> None:
        self._payload = Payload(
            schema_version=schema_version,
            issuer_id=issuer_id,
            model_id=model_id,
            model_version_id=model_version_id,
            key_id=key_id,
        )
        self._payload.validate()
        self._repeat_interval = repeat_interval_tokens
        self._mode = (
            injection_mode
            if isinstance(injection_mode, InjectionMode)
            else InjectionMode(injection_mode)
        )

    def _packed_bits(self) -> str:
        return _pay.bytes_to_bits(_pay.pack(self._payload))

    def apply(self, text: str) -> str:
        if not text:
            return text
        injector = TagInjector(
            self._packed_bits(),
            repeat_interval=self._repeat_interval,
            mode=self._mode,
        )
        out_first = injector.inject_delta(text)
        out_final = injector.finalize()
        result = out_first + out_final
        # Force-tag fallback. The streaming injector cannot position tags at
        # "% of full output" (it sees one chunk at a time), so if no tags
        # landed naturally we insert here based on full result length:
        #   - 1 tag at 40% if text > 20 chars
        #   - 2 tags at 25% and 75% if text > 250 chars (so a half-cut leaves
        #     at least one tag intact)
        if injector._tags_inserted == 0 and len(text) > 20:
            tag = self._injector_tag()
            if len(result) > 250:
                # Insert in reverse order so positions don't shift.
                p2 = self._snap_to_ws(result, int(len(result) * 0.75))
                result = result[:p2] + tag + result[p2:]
                p1 = self._snap_to_ws(result, int(len(result) * 0.25))
                result = result[:p1] + tag + result[p1:]
            else:
                pos = self._snap_to_ws(result, int(len(result) * 0.4))
                result = result[:pos] + tag + result[pos:]
        return result

    @staticmethod
    def _snap_to_ws(s: str, pos: int) -> int:
        pos = max(1, pos)
        ws = s.find(" ", pos)
        if ws != -1 and ws - pos < 50:
            return ws + 1
        return pos

    def _injector_tag(self) -> str:
        from .zero_width import encode_bits
        return encode_bits(self._packed_bits())

    def detect(self, text: str) -> DetectResult:
        return _detect(text)

    @staticmethod
    def strip(text: str) -> str:
        return strip_all(text)


def _detect(text: str) -> DetectResult:
    tags = find_tags(text)
    payloads: list[PayloadInfo] = []
    valid = 0
    invalid = 0
    for _, _, raw in tags:
        bits = decode_tag(raw)
        if bits is None:
            invalid += 1
            continue
        try:
            buf = _pay.bits_to_bytes(bits)
        except ValueError:
            invalid += 1
            continue
        try:
            payload, code_valid, errors = _pay.unpack(buf)
        except ValueError:
            invalid += 1
            continue
        if code_valid:
            valid += 1
        else:
            invalid += 1
        payloads.append(
            PayloadInfo(
                schema_version=payload.schema_version,
                issuer_id=payload.issuer_id,
                model_id=payload.model_id,
                model_version_id=payload.model_version_id,
                key_id=payload.key_id,
                code_valid=code_valid,
                errors_corrected=errors,
                raw_payload_hex=buf.hex(),
            )
        )
    return DetectResult(
        watermarked=any(p.code_valid for p in payloads),
        tag_count=len(tags),
        valid_count=valid,
        invalid_count=invalid,
        payloads=payloads,
    )
