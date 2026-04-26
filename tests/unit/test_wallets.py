"""Unit tests for browser wallet proof verification."""

from __future__ import annotations

import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from eth_account import Account
from eth_account.messages import encode_defunct

from vellum.auth.ecdsa import generate_keypair, hash_text
from vellum.auth.wallets import (
    WalletProof,
    base58_encode,
    build_wallet_message,
    verify_wallet_proof,
)


def test_verify_evm_wallet_proof():
    private_key, _public_key, address = generate_keypair()
    data_hash = hash_text("wallet proof")
    message = build_wallet_message(data_hash, "evm", address)
    signature = Account.sign_message(
        encode_defunct(text=message),
        private_key=private_key,
    ).signature.hex()

    verified = verify_wallet_proof(
        WalletProof(
            wallet_type="evm",
            address=address,
            message=message,
            signature=signature,
            signature_encoding="hex",
            chain_id="1",
        ),
        data_hash=data_hash,
    )

    assert verified.wallet_type == "evm"
    assert verified.address.lower() == address.lower()
    assert verified.chain_id == "1"


def test_verify_evm_wallet_proof_rejects_tampered_message():
    private_key, _public_key, address = generate_keypair()
    data_hash = hash_text("wallet proof")
    message = build_wallet_message(data_hash, "evm", address)
    signature = Account.sign_message(
        encode_defunct(text=message),
        private_key=private_key,
    ).signature.hex()

    with pytest.raises(ValueError, match="does not match"):
        verify_wallet_proof(
            WalletProof(
                wallet_type="evm",
                address=address,
                message=message.replace(data_hash, hash_text("other")),
                signature=signature,
                signature_encoding="hex",
            ),
            data_hash=data_hash,
        )


def test_verify_solana_wallet_proof():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    address = base58_encode(public_key)
    data_hash = hash_text("solana wallet proof")
    message = build_wallet_message(data_hash, "solana", address)
    signature = private_key.sign(message.encode("utf-8"))

    verified = verify_wallet_proof(
        WalletProof(
            wallet_type="solana",
            address=address,
            message=message,
            signature=base64.b64encode(signature).decode("ascii"),
            signature_encoding="base64",
            cluster="devnet",
        ),
        data_hash=data_hash,
    )

    assert verified.wallet_type == "solana"
    assert verified.address == address
    assert verified.cluster == "devnet"
