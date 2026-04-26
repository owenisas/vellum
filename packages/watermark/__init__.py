"""vellum-watermark — invisible Unicode watermarks for AI-generated text."""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import TagConfig, WatermarkConfig
from .payload import Payload, crc8, from_bits, from_hex, pack, to_bits, to_hex, unpack
from .zero_width import (
    TagInjector,
    TagMatch,
    build_tag,
    decode_bits,
    encode_bits,
    find_tags,
    strip_tags,
)


@dataclass
class PayloadInfo:
    """Public-facing payload description (matches REWRITE_SPEC.md)."""

    schema_version: int
    issuer_id: int
    model_id: int
    model_version_id: int
    key_id: int
    crc_valid: bool
    raw_payload_hex: str

    @classmethod
    def from_match(cls, match: TagMatch) -> "PayloadInfo":
        p = match.payload
        return cls(
            schema_version=p.schema_version,
            issuer_id=p.issuer_id,
            model_id=p.model_id,
            model_version_id=p.model_version_id,
            key_id=p.key_id,
            crc_valid=p.crc_valid,
            raw_payload_hex=to_hex(match.payload64),
        )

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "issuer_id": self.issuer_id,
            "model_id": self.model_id,
            "model_version_id": self.model_version_id,
            "key_id": self.key_id,
            "crc_valid": self.crc_valid,
            "raw_payload_hex": self.raw_payload_hex,
        }


@dataclass
class DetectResult:
    """Structured result of `Watermarker.detect`."""

    watermarked: bool
    tag_count: int
    valid_count: int
    invalid_count: int
    payloads: list[PayloadInfo] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "watermarked": self.watermarked,
            "tag_count": self.tag_count,
            "valid_count": self.valid_count,
            "invalid_count": self.invalid_count,
            "payloads": [p.to_dict() for p in self.payloads],
        }


class Watermarker:
    """High-level interface for applying and detecting watermarks."""

    def __init__(
        self,
        *,
        schema_version: int = 1,
        issuer_id: int = 1,
        model_id: int = 0,
        model_version_id: int = 0,
        key_id: int = 1,
        repeat_interval_tokens: int = 160,
        tag: TagConfig | None = None,
    ) -> None:
        self.config = WatermarkConfig(
            schema_version=schema_version,
            issuer_id=issuer_id,
            model_id=model_id,
            model_version_id=model_version_id,
            key_id=key_id,
            repeat_interval_tokens=repeat_interval_tokens,
            tag=tag or TagConfig(),
        )

    @property
    def payload64(self) -> int:
        c = self.config
        return pack(
            schema_version=c.schema_version,
            issuer_id=c.issuer_id,
            model_id=c.model_id,
            model_version_id=c.model_version_id,
            key_id=c.key_id,
        )

    def apply(self, text: str) -> str:
        """Inject invisible watermark tags into `text`."""
        if not text:
            return text
        injector = TagInjector(
            payload64=self.payload64,
            tag=self.config.tag,
            repeat_interval_tokens=self.config.repeat_interval_tokens,
        )
        out = injector.inject_delta(text, finalize=True)
        return out

    def detect(self, text: str) -> DetectResult:
        """Scan `text` for watermark tags and return a structured report."""
        if not text:
            return DetectResult(False, 0, 0, 0, [])
        matches = find_tags(text, self.config.tag)
        infos = [PayloadInfo.from_match(m) for m in matches]
        valid = sum(1 for i in infos if i.crc_valid)
        return DetectResult(
            watermarked=valid > 0,
            tag_count=len(matches),
            valid_count=valid,
            invalid_count=len(matches) - valid,
            payloads=infos,
        )

    @staticmethod
    def strip(text: str, tag: TagConfig | None = None) -> str:
        """Remove all watermark tags from text."""
        return strip_tags(text, tag or TagConfig())

    @classmethod
    def detect_text(cls, text: str, tag: TagConfig | None = None) -> DetectResult:
        """Convenience: detect with a default config."""
        wm = cls(tag=tag)
        return wm.detect(text)


def apply(text: str, **kwargs: object) -> str:
    """Module-level convenience wrapper."""
    return Watermarker(**kwargs).apply(text)  # type: ignore[arg-type]


def detect(text: str) -> DetectResult:
    """Module-level convenience wrapper."""
    return Watermarker.detect_text(text)


def strip(text: str) -> str:
    """Module-level convenience wrapper."""
    return Watermarker.strip(text)


__all__ = [
    "DetectResult",
    "Payload",
    "PayloadInfo",
    "TagConfig",
    "TagInjector",
    "TagMatch",
    "Watermarker",
    "WatermarkConfig",
    "apply",
    "build_tag",
    "crc8",
    "decode_bits",
    "detect",
    "encode_bits",
    "find_tags",
    "from_bits",
    "from_hex",
    "pack",
    "strip",
    "strip_tags",
    "to_bits",
    "to_hex",
    "unpack",
]
