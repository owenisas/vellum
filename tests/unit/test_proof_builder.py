"""Phase 5 verification: proof bundle determinism + bundle_id round-trip."""

import hashlib

import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data

from veritext.auth.ecdsa import TypedDataMessage, recover_address_eip712
from veritext.services._jcs import canonicalize


def test_canonical_signing_payload_deterministic():
    bundle = {
        "spec": "veritext-proof-bundle/v2",
        "z": 1,
        "a": [3, 1, 2],
        "nested": {"k": True, "x": None},
    }
    a = canonicalize(bundle)
    bundle_perm = {
        "nested": {"x": None, "k": True},
        "a": [3, 1, 2],
        "z": 1,
        "spec": "veritext-proof-bundle/v2",
    }
    assert canonicalize(bundle_perm) == a


def test_bundle_id_recompute_from_jcs():
    # bundle minus signature minus bundle_id minus signed_fields, JCS, sha256, vtb2_ prefix.
    partial = {
        "spec": "veritext-proof-bundle/v2",
        "hashing": {"algorithm": "sha256", "text_hash": "00" * 32, "input_encoding": "utf-8", "normalization": "none"},
        "issuer": {"issuer_id": 1, "name": "x", "eth_address": "0x" + "1" * 40, "public_key_hex": "0x" + "1" * 40, "current_key_id": 1, "key_history": []},
        "watermark": {"detected": False, "injection_mode": "whitespace", "tag_count": 0, "valid_count": 0, "invalid_count": 0, "payloads": []},
        "anchors": [],
        "verification_hints": {"chain_type": "simulated"},
    }
    canon = canonicalize(partial)
    expected = "vtb2_" + hashlib.sha256(canon).hexdigest()
    assert expected.startswith("vtb2_")
    assert len(expected) == 5 + 64


def test_eip712_signature_round_trip():
    acct = Account.create()
    text_hash = b"\xab" * 32
    msg = TypedDataMessage(
        text_hash=text_hash,
        issuer_id=42,
        timestamp=1_700_000_000,
        bundle_nonce=b"\xcd" * 32,
    )
    signable = encode_typed_data(full_message=msg.to_eip712())
    signed = Account.sign_message(signable, private_key=acct.key)
    recovered = recover_address_eip712(msg, signed.signature.hex())
    assert recovered.lower() == acct.address.lower()
