"""Phase 10: verify CLI exit codes against fixture bundles."""

import json
from pathlib import Path

import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data

from veritext.auth.ecdsa import TypedDataMessage
from veritext.cli.verify import verify_bundle


def _make_bundle(text: str, issuer_id: int = 42, *, tamper: str = ""):
    import hashlib

    acct = Account.create()
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    timestamp = 1_700_000_000
    bundle_nonce = "00" * 32
    msg = TypedDataMessage(
        text_hash=bytes.fromhex(text_hash),
        issuer_id=issuer_id,
        timestamp=timestamp,
        bundle_nonce=bytes.fromhex(bundle_nonce),
    )
    signable = encode_typed_data(full_message=msg.to_eip712())
    signed = Account.sign_message(signable, private_key=acct.key)

    bundle = {
        "spec": "veritext-proof-bundle/v2",
        "signed_fields": ["spec", "bundle_id", "hashing", "issuer", "watermark", "anchors", "verification_hints"],
        "hashing": {"algorithm": "sha256", "text_hash": text_hash, "input_encoding": "utf-8", "normalization": "none"},
        "issuer": {
            "issuer_id": issuer_id,
            "name": "test",
            "eth_address": acct.address,
            "public_key_hex": acct.address,
            "current_key_id": 1,
            "key_history": [],
        },
        "signature": {
            "scheme": "eip712",
            "canonicalization": "rfc8785",
            "signed_payload": "sha256:" + "0" * 64,
            "signature_hex": signed.signature.hex(),
            "recoverable_address": True,
            "typed_data": {
                "domain": {
                    "name": "Veritext", "version": "2", "chainId": 1,
                    "verifyingContract": "0x0000000000000000000000000000000000000000",
                },
                "types": {"VeritextAnchor": [
                    {"name": "textHash", "type": "bytes32"},
                    {"name": "issuerId", "type": "uint256"},
                    {"name": "timestamp", "type": "uint256"},
                    {"name": "bundleNonce", "type": "bytes32"},
                ]},
                "primaryType": "VeritextAnchor",
                "message": {
                    "textHash": "0x" + text_hash,
                    "issuerId": issuer_id,
                    "timestamp": timestamp,
                    "bundleNonce": bundle_nonce,
                },
            },
        },
        "watermark": {
            "detected": False, "injection_mode": "whitespace",
            "tag_count": 0, "valid_count": 0, "invalid_count": 0, "payloads": [],
        },
        "anchors": [],
        "verification_hints": {"chain_type": "simulated"},
    }
    # Compute bundle_id correctly
    from veritext.services._jcs import canonicalize
    import hashlib as _h

    partial = {k: v for k, v in bundle.items() if k not in ("bundle_id", "signature", "signed_fields")}
    bundle["bundle_id"] = "vtb2_" + _h.sha256(canonicalize(partial)).hexdigest()

    if tamper == "text":
        bundle["hashing"]["text_hash"] = "ff" * 32
        # bundle_id will mismatch; expected
    elif tamper == "signature":
        bundle["signature"]["signature_hex"] = "00" * 65
    return bundle


def test_valid_bundle_exits_zero():
    text = "hello world"
    b = _make_bundle(text)
    code, msg = verify_bundle(b, text=text)
    assert code == 0, msg


def test_text_tamper_exits_nonzero():
    text = "hello world"
    b = _make_bundle(text)
    # Change the text but keep the bundle as-is — should fail at text-hash check.
    code, msg = verify_bundle(b, text="different text")
    assert code != 0


def test_signature_tamper_exits_nonzero():
    text = "hello world"
    b = _make_bundle(text, tamper="signature")
    code, msg = verify_bundle(b, text=text)
    assert code != 0
