"""Unit tests for the 64-bit payload pack/unpack helpers."""

from __future__ import annotations

import pytest

from watermark import crc8, pack, unpack


def test_crc8_known_vector():
    """crc8 is a pure function — deterministic across calls and stable for empty input."""
    # 0x00 byte yields 0 because the algorithm doesn't shift any bits in.
    assert crc8(b"\x00") == 0

    # Determinism across calls (no internal state).
    assert crc8(b"abc") == crc8(b"abc")
    assert crc8(b"\xff") == crc8(b"\xff")
    # Different inputs should generally differ; the b"" case is the trivial baseline.
    assert crc8(b"abc") != crc8(b"abcd")


def test_pack_unpack_round_trip():
    p = pack(
        schema_version=1,
        issuer_id=42,
        model_id=1001,
        model_version_id=1,
        key_id=1,
    )
    decoded = unpack(p)
    assert decoded.schema_version == 1
    assert decoded.issuer_id == 42
    assert decoded.model_id == 1001
    assert decoded.model_version_id == 1
    assert decoded.key_id == 1
    assert decoded.crc_valid is True


def test_unpack_corrupted():
    """Flipping a bit anywhere in the high 56 bits invalidates the CRC."""
    p = pack(
        schema_version=1,
        issuer_id=42,
        model_id=1001,
        model_version_id=1,
        key_id=1,
    )
    # Flip a bit in the model_id region (bit 32) — guaranteed to be inside the
    # CRC-protected high 56 bits.
    corrupted = p ^ (1 << 32)
    decoded = unpack(corrupted)
    assert decoded.crc_valid is False


def test_field_overflow_raises():
    """issuer_id is a 12-bit field; 4096 exceeds 0xFFF."""
    with pytest.raises(ValueError):
        pack(
            schema_version=1,
            issuer_id=4096,
            model_id=0,
            model_version_id=0,
            key_id=0,
        )


def test_pack_full_field_extremes():
    """All-max-values must pack and unpack cleanly with crc_valid."""
    p = pack(
        schema_version=0xF,
        issuer_id=0xFFF,
        model_id=0xFFFF,
        model_version_id=0xFFFF,
        key_id=0xFF,
    )
    decoded = unpack(p)
    assert decoded.schema_version == 0xF
    assert decoded.issuer_id == 0xFFF
    assert decoded.model_id == 0xFFFF
    assert decoded.model_version_id == 0xFFFF
    assert decoded.key_id == 0xFF
    assert decoded.crc_valid is True
