"""BCH-Hamming parity round-trip and 1-bit recovery tests."""

import os

import pytest

from watermark import _bch


def test_parity_roundtrip_zero():
    data = bytes(7)
    p = _bch.encode(data)
    out, errors = _bch.decode(data, p)
    assert out == data
    assert errors == 0


def test_parity_roundtrip_random():
    for _ in range(100):
        data = os.urandom(7)
        p = _bch.encode(data)
        out, errors = _bch.decode(data, p)
        assert out == data
        assert errors == 0


def test_one_bit_correction_in_data():
    data = b"\x12\x34\x56\x78\x9a\xbc\xde"
    p = _bch.encode(data)
    # Flip bit 5 of byte 3
    bad = bytearray(data)
    bad[3] ^= 0b00100000
    out, errors = _bch.decode(bytes(bad), p)
    assert out == data
    assert errors == 1


def test_one_bit_correction_in_parity():
    data = b"\xaa" * 7
    p = _bch.encode(data)
    out, errors = _bch.decode(data, p ^ 0b1000)
    assert out == data
    assert errors == 1


def test_uncorrectable_two_bits():
    # Two flips far apart should NOT decode to original.
    data = b"\x11\x22\x33\x44\x55\x66\x77"
    p = _bch.encode(data)
    bad = bytearray(data)
    bad[0] ^= 0b1
    bad[6] ^= 0b1
    # We expect either an exception or a non-equal result; not silent corruption.
    try:
        out, errors = _bch.decode(bytes(bad), p)
    except ValueError:
        return
    assert out != data, "two-bit error should not decode silently to original"
