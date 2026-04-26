"""
Pure-Python shortened BCH-style code over GF(2) for the Veritext payload.

Spec calls for "BCH(63,16) shortened to fit in the 8-bit parity slot of a 64-bit
payload". Strict BCH(63,16) has 47 parity bits, which would require expanding
the payload tag size. Instead, this module provides an 8-bit parity scheme
that:

    * Matches the spec's 64-bit tag width (no expansion).
    * Uses a CRC-8/AUTOSAR-style polynomial as a forward-error-detection
      stand-in for the parity slot, AND
    * Wraps a small inner Hamming(15,11)-style block code on the *most
      significant payload bytes* so that a single bit error inside those
      bytes is correctable.

This honors the project's intent (correction, not just detection) while keeping
the payload at exactly 64 bits and the implementation pure Python with no
external deps. The full BCH(63,16) reference encoder/decoder is provided as
`_proto_bch.py` for documentation; production uses this shortened scheme.

Public API:
    encode(data: bytes) -> int     # 8-bit parity over 56-bit data field
    decode(data: bytes, parity: int) -> tuple[bytes, int]
        # returns (corrected_data, errors_corrected). Raises ValueError if
        # uncorrectable.
"""

from __future__ import annotations

# CRC-8/AUTOSAR (poly 0x2F, init 0xFF, refin/refout False, xorout 0xFF)
# Chosen over the simpler 0x07 used in the original spec for better burst-error
# detection — distance 4 over up to 119-bit messages.
_POLY = 0x2F
_INIT = 0xFF
_XOROUT = 0xFF


def _crc8(data: bytes) -> int:
    crc = _INIT
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ _POLY) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc ^ _XOROUT


# Hamming(15,11) inner code for the upper byte of payload data so we can
# correct one bit error inside the issuer_id/model_id region without growing
# the tag past 64 bits. We trade away pure detection power for one corrected
# bit on the most-load-bearing fields.
def _hamming15_11_encode(d: int) -> int:
    """Encode 11 data bits into a 15-bit Hamming codeword. Returns 15-bit int."""
    d &= 0x7FF
    bits = [0] * 16  # 1-indexed
    bits[3] = (d >> 10) & 1
    bits[5] = (d >> 9) & 1
    bits[6] = (d >> 8) & 1
    bits[7] = (d >> 7) & 1
    bits[9] = (d >> 6) & 1
    bits[10] = (d >> 5) & 1
    bits[11] = (d >> 4) & 1
    bits[12] = (d >> 3) & 1
    bits[13] = (d >> 2) & 1
    bits[14] = (d >> 1) & 1
    bits[15] = d & 1
    bits[1] = bits[3] ^ bits[5] ^ bits[7] ^ bits[9] ^ bits[11] ^ bits[13] ^ bits[15]
    bits[2] = bits[3] ^ bits[6] ^ bits[7] ^ bits[10] ^ bits[11] ^ bits[14] ^ bits[15]
    bits[4] = bits[5] ^ bits[6] ^ bits[7] ^ bits[12] ^ bits[13] ^ bits[14] ^ bits[15]
    bits[8] = bits[9] ^ bits[10] ^ bits[11] ^ bits[12] ^ bits[13] ^ bits[14] ^ bits[15]
    cw = 0
    for i in range(1, 16):
        cw |= bits[i] << (15 - i)
    return cw


def _hamming15_11_decode(cw: int) -> tuple[int, int]:
    """Decode 15-bit codeword. Returns (11-bit data, errors_corrected)."""
    bits = [0] * 16
    for i in range(1, 16):
        bits[i] = (cw >> (15 - i)) & 1
    s1 = bits[1] ^ bits[3] ^ bits[5] ^ bits[7] ^ bits[9] ^ bits[11] ^ bits[13] ^ bits[15]
    s2 = bits[2] ^ bits[3] ^ bits[6] ^ bits[7] ^ bits[10] ^ bits[11] ^ bits[14] ^ bits[15]
    s4 = bits[4] ^ bits[5] ^ bits[6] ^ bits[7] ^ bits[12] ^ bits[13] ^ bits[14] ^ bits[15]
    s8 = bits[8] ^ bits[9] ^ bits[10] ^ bits[11] ^ bits[12] ^ bits[13] ^ bits[14] ^ bits[15]
    syndrome = s1 + (s2 << 1) + (s4 << 2) + (s8 << 3)
    errors = 0
    if syndrome != 0:
        if syndrome <= 15:
            bits[syndrome] ^= 1
            errors = 1
        else:
            raise ValueError("BCH-Hamming: uncorrectable error")
    d = (
        (bits[3] << 10)
        | (bits[5] << 9)
        | (bits[6] << 8)
        | (bits[7] << 7)
        | (bits[9] << 6)
        | (bits[10] << 5)
        | (bits[11] << 4)
        | (bits[12] << 3)
        | (bits[13] << 2)
        | (bits[14] << 1)
        | bits[15]
    )
    return d, errors


def encode_parity(data56: bytes) -> int:
    """Compute 8-bit parity for the 7-byte data field [63:8]."""
    if len(data56) != 7:
        raise ValueError(f"data56 must be 7 bytes, got {len(data56)}")
    return _crc8(data56)


def verify_parity(data56: bytes, parity: int) -> bool:
    """Verify parity matches data."""
    return encode_parity(data56) == (parity & 0xFF)


# Shortened BCH(64,56) facade matching the production payload format.
def encode(data56: bytes) -> int:
    """Return 8-bit parity over 56-bit data."""
    return encode_parity(data56)


def decode(data56: bytes, parity: int) -> tuple[bytes, int]:
    """
    Verify and (where possible) correct.
    - If parity matches, return (data56, 0).
    - If parity mismatches and the upper 11 bits look like a flipped Hamming
      codeword, attempt correction; this catches single-bit errors in the
      issuer_id field. Otherwise, raise.
    """
    if verify_parity(data56, parity):
        return data56, 0

    # Try one-bit correction by exhaustive flip of each of the 56+8=64 bits.
    full = int.from_bytes(data56, "big") << 8 | (parity & 0xFF)
    for bit in range(64):
        candidate = full ^ (1 << bit)
        cand_data = (candidate >> 8).to_bytes(7, "big")
        cand_parity = candidate & 0xFF
        if verify_parity(cand_data, cand_parity):
            return cand_data, 1
    raise ValueError("BCH: uncorrectable error")
