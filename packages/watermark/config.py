"""Configuration dataclasses for the watermark library."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TagConfig:
    """Unicode codepoints used to encode a watermark tag."""

    bit_zero: str = "​"  # ZERO WIDTH SPACE
    bit_one: str = "‌"  # ZERO WIDTH NON-JOINER
    tag_start: str = "⁣"  # INVISIBLE SEPARATOR
    tag_end: str = "⁤"  # INVISIBLE PLUS
    payload_bits: int = 64

    @property
    def all_chars(self) -> set[str]:
        return {self.bit_zero, self.bit_one, self.tag_start, self.tag_end}


@dataclass(frozen=True)
class WatermarkConfig:
    """Top-level watermark configuration."""

    schema_version: int = 1
    issuer_id: int = 1
    model_id: int = 0
    model_version_id: int = 0
    key_id: int = 1
    repeat_interval_tokens: int = 160
    tag: TagConfig = TagConfig()

    def __post_init__(self) -> None:
        if not 0 <= self.schema_version <= 0xF:
            raise ValueError("schema_version must fit in 4 bits")
        if not 0 <= self.issuer_id <= 0xFFF:
            raise ValueError("issuer_id must fit in 12 bits")
        if not 0 <= self.model_id <= 0xFFFF:
            raise ValueError("model_id must fit in 16 bits")
        if not 0 <= self.model_version_id <= 0xFFFF:
            raise ValueError("model_version_id must fit in 16 bits")
        if not 0 <= self.key_id <= 0xFF:
            raise ValueError("key_id must fit in 8 bits")
        if self.repeat_interval_tokens < 1:
            raise ValueError("repeat_interval_tokens must be >= 1")
