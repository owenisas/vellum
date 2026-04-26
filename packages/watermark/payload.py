"""64-bit payload pack/unpack with CRC-8 (poly 0x07)."""

from __future__ import annotations

from dataclasses import dataclass


def crc8(data: bytes) -> int:
    """Standard CRC-8 with polynomial 0x07. Matches the JS implementation."""
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


@dataclass(frozen=True)
class Payload:
    """Decoded watermark payload (matches the 64-bit on-wire format)."""

    schema_version: int
    issuer_id: int
    model_id: int
    model_version_id: int
    key_id: int
    crc: int
    crc_valid: bool


def pack(
    *,
    schema_version: int,
    issuer_id: int,
    model_id: int,
    model_version_id: int,
    key_id: int,
) -> int:
    """Encode the 64-bit payload as an integer.

    Layout (MSB first):
        [63:60] schema_version    4 bits
        [59:48] issuer_id        12 bits
        [47:32] model_id         16 bits
        [31:16] model_version_id 16 bits
        [15:8]  key_id            8 bits
        [7:0]   crc8              8 bits
    """
    if not 0 <= schema_version <= 0xF:
        raise ValueError("schema_version overflow")
    if not 0 <= issuer_id <= 0xFFF:
        raise ValueError("issuer_id overflow")
    if not 0 <= model_id <= 0xFFFF:
        raise ValueError("model_id overflow")
    if not 0 <= model_version_id <= 0xFFFF:
        raise ValueError("model_version_id overflow")
    if not 0 <= key_id <= 0xFF:
        raise ValueError("key_id overflow")

    high56 = (
        (schema_version & 0xF) << 52
        | (issuer_id & 0xFFF) << 40
        | (model_id & 0xFFFF) << 24
        | (model_version_id & 0xFFFF) << 8
        | (key_id & 0xFF)
    )
    crc = crc8(high56.to_bytes(7, "big"))
    return (high56 << 8) | crc


def unpack(payload64: int) -> Payload:
    """Decode a 64-bit payload integer."""
    if not 0 <= payload64 <= 0xFFFFFFFFFFFFFFFF:
        raise ValueError("payload64 must fit in 64 bits")

    schema_version = (payload64 >> 60) & 0xF
    issuer_id = (payload64 >> 48) & 0xFFF
    model_id = (payload64 >> 32) & 0xFFFF
    model_version_id = (payload64 >> 16) & 0xFFFF
    key_id = (payload64 >> 8) & 0xFF
    crc = payload64 & 0xFF

    high56 = payload64 >> 8
    expected_crc = crc8(high56.to_bytes(7, "big"))

    return Payload(
        schema_version=schema_version,
        issuer_id=issuer_id,
        model_id=model_id,
        model_version_id=model_version_id,
        key_id=key_id,
        crc=crc,
        crc_valid=crc == expected_crc,
    )


def to_bits(payload64: int, bit_count: int = 64) -> str:
    """Render integer payload as a binary string of fixed length (MSB first)."""
    if bit_count < 1:
        raise ValueError("bit_count must be positive")
    return format(payload64 & ((1 << bit_count) - 1), f"0{bit_count}b")


def from_bits(bits: str) -> int:
    """Parse a binary string into an integer payload."""
    if not bits or any(c not in "01" for c in bits):
        raise ValueError("bits must be a non-empty binary string")
    return int(bits, 2)


def to_hex(payload64: int) -> str:
    """Render payload as 0x-prefixed 16 hex chars."""
    return f"0x{payload64:016x}"


def from_hex(hex_str: str) -> int:
    """Parse a hex payload back into an integer."""
    s = hex_str.lower().removeprefix("0x")
    return int(s, 16)
