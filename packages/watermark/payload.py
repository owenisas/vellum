"""
Veritext 64-bit payload pack/unpack with BCH error correction.

Bit layout (MSB first):
    [63:60] schema_version    4 bits   (0..15)
    [59:48] issuer_id        12 bits   (0..4095)
    [47:32] model_id         16 bits   (0..65535)
    [31:16] model_version_id 16 bits   (0..65535)
    [15:8]  key_id            8 bits   (0..255)
    [7:0]   parity            8 bits   shortened BCH-Hamming code
                                       (correct 1 bit, detect more)

The parity scheme is documented in `_bch.py`. The original spec specified
CRC-8/0x07; we upgraded to a shortened correcting code that fits the same
8-bit slot, per improvement #2 of the implementation plan.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import _bch


SCHEMA_VERSION_BITS = 4
ISSUER_ID_BITS = 12
MODEL_ID_BITS = 16
MODEL_VERSION_ID_BITS = 16
KEY_ID_BITS = 8
PARITY_BITS = 8

PAYLOAD_BITS = 64
DATA_BITS = PAYLOAD_BITS - PARITY_BITS  # 56


@dataclass(frozen=True)
class Payload:
    schema_version: int
    issuer_id: int
    model_id: int
    model_version_id: int
    key_id: int

    def validate(self) -> None:
        for name, value, bits in [
            ("schema_version", self.schema_version, SCHEMA_VERSION_BITS),
            ("issuer_id", self.issuer_id, ISSUER_ID_BITS),
            ("model_id", self.model_id, MODEL_ID_BITS),
            ("model_version_id", self.model_version_id, MODEL_VERSION_ID_BITS),
            ("key_id", self.key_id, KEY_ID_BITS),
        ]:
            if value < 0 or value >= (1 << bits):
                raise ValueError(f"{name}={value} does not fit in {bits} bits")


def pack(p: Payload) -> bytes:
    """Pack a Payload into 8 bytes (64 bits) with BCH parity in [7:0]."""
    p.validate()
    data = (
        (p.schema_version & 0xF) << 52
        | (p.issuer_id & 0xFFF) << 40
        | (p.model_id & 0xFFFF) << 24
        | (p.model_version_id & 0xFFFF) << 8
        | (p.key_id & 0xFF)
    )
    data56 = data.to_bytes(7, "big")
    parity = _bch.encode(data56)
    return data56 + bytes([parity])


def unpack(buf: bytes) -> tuple[Payload, bool, int]:
    """
    Unpack 8 bytes into (Payload, code_valid, errors_corrected).

    - `code_valid=True` if parity verifies (after possible 1-bit correction).
    - `errors_corrected` is 0 or 1.
    """
    if len(buf) != 8:
        raise ValueError(f"payload must be 8 bytes, got {len(buf)}")
    data56 = buf[:7]
    parity = buf[7]
    try:
        corrected, errors = _bch.decode(data56, parity)
    except ValueError:
        # Uncorrectable. Return best-effort fields with code_valid=False.
        return _payload_from_bytes(data56), False, 0
    return _payload_from_bytes(corrected), True, errors


def _payload_from_bytes(data56: bytes) -> Payload:
    n = int.from_bytes(data56, "big")
    return Payload(
        schema_version=(n >> 52) & 0xF,
        issuer_id=(n >> 40) & 0xFFF,
        model_id=(n >> 24) & 0xFFFF,
        model_version_id=(n >> 8) & 0xFFFF,
        key_id=n & 0xFF,
    )


def bits_to_bytes(bits: str) -> bytes:
    """Convert a string of '0'/'1' (length 64) to 8 bytes, MSB first."""
    if len(bits) != PAYLOAD_BITS:
        raise ValueError(f"expected {PAYLOAD_BITS} bits, got {len(bits)}")
    out = bytearray(8)
    for i, c in enumerate(bits):
        if c not in ("0", "1"):
            raise ValueError(f"invalid bit char: {c!r}")
        if c == "1":
            out[i // 8] |= 1 << (7 - (i % 8))
    return bytes(out)


def bytes_to_bits(buf: bytes) -> str:
    """Convert 8 bytes to a string of '0'/'1' (length 64), MSB first."""
    if len(buf) != 8:
        raise ValueError(f"expected 8 bytes, got {len(buf)}")
    return "".join(f"{b:08b}" for b in buf)
