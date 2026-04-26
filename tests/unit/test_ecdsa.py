"""Unit tests for ECDSA helpers in :mod:`vellum.auth.ecdsa`."""

from __future__ import annotations

from vellum.auth.ecdsa import (
    generate_keypair,
    hash_text,
    recover_address,
    sign_hash,
    verify_signature,
)


def test_generate_and_sign_verify():
    private_key, _public_key, address = generate_keypair()

    h = hash_text("hello, world")
    sig = sign_hash(h, private_key)

    assert verify_signature(h, sig, address) is True


def test_verify_wrong_address_fails():
    private_key, _public_key, _address = generate_keypair()
    _other_priv, _other_pub, other_address = generate_keypair()

    h = hash_text("payload")
    sig = sign_hash(h, private_key)

    # Should return False — must NOT raise.
    assert verify_signature(h, sig, other_address) is False


def test_recover_address_matches():
    private_key, _public_key, address = generate_keypair()

    h = hash_text("any message")
    sig = sign_hash(h, private_key)

    recovered = recover_address(h, sig)
    assert recovered.lower() == address.lower()


def test_invalid_signature_returns_false():
    """Malformed signature hex must NOT raise from verify_signature."""
    _priv, _pub, address = generate_keypair()
    h = hash_text("anything")

    # Garbage hex (right shape, wrong content)
    bad_sig = "0x" + "00" * 65

    assert verify_signature(h, bad_sig, address) is False


def test_hash_text_is_hex_no_prefix():
    h = hash_text("abc")
    assert isinstance(h, str)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)
    assert not h.startswith("0x")
