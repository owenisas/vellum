"""Payload pack/unpack and BCH-protected error correction tests."""

import pytest

from watermark.payload import Payload, pack, unpack, bytes_to_bits, bits_to_bytes


def test_pack_unpack_roundtrip():
    p = Payload(schema_version=1, issuer_id=42, model_id=1001, model_version_id=2, key_id=7)
    buf = pack(p)
    assert len(buf) == 8
    out, valid, errors = unpack(buf)
    assert out == p
    assert valid is True
    assert errors == 0


def test_pack_field_overflow():
    with pytest.raises(ValueError):
        pack(Payload(schema_version=99, issuer_id=0, model_id=0, model_version_id=0, key_id=0))
    with pytest.raises(ValueError):
        pack(Payload(schema_version=0, issuer_id=99999, model_id=0, model_version_id=0, key_id=0))


def test_bits_byte_roundtrip():
    buf = bytes(range(8))
    bits = bytes_to_bits(buf)
    assert len(bits) == 64
    assert bits_to_bytes(bits) == buf


def test_one_bit_corruption_recovers():
    p = Payload(schema_version=1, issuer_id=42, model_id=1001, model_version_id=2, key_id=7)
    buf = bytearray(pack(p))
    buf[2] ^= 0b00000010  # one-bit error
    out, valid, errors = unpack(bytes(buf))
    assert valid is True
    assert errors == 1
    assert out == p


def test_corrupted_returns_invalid_when_uncorrectable():
    p = Payload(schema_version=1, issuer_id=42, model_id=1001, model_version_id=2, key_id=7)
    buf = bytearray(pack(p))
    # Two bit flips → uncorrectable
    buf[0] ^= 0b1
    buf[6] ^= 0b1
    out, valid, errors = unpack(bytes(buf))
    assert valid is False
    assert errors == 0
