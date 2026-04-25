"""secp256k1 sign / verify / recover using EIP-191 personal_sign style."""

from __future__ import annotations

import hashlib
import secrets

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_keys import keys


def hash_text(text: str) -> str:
    """SHA-256 of UTF-8 encoded text. Returns hex string (no 0x prefix)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_signature(signature_hex: str) -> str:
    """Ensure signature is 0x-prefixed and lower-case."""
    s = signature_hex.strip().lower()
    return s if s.startswith("0x") else f"0x{s}"


def recover_address(data_hash: str, signature_hex: str) -> str:
    """Recover Ethereum address from EIP-191 personal_sign signature.

    `data_hash` is treated as the *message text* (hex string) — exactly matching
    `ethers.utils.signMessage(hash)` on the frontend.
    """
    message = encode_defunct(text=data_hash)
    sig = _normalize_signature(signature_hex)
    return Account.recover_message(message, signature=sig)


def verify_signature(data_hash: str, signature_hex: str, expected_address: str) -> bool:
    """Verify signature recovers to the expected address (case-insensitive)."""
    try:
        recovered = recover_address(data_hash, signature_hex)
    except Exception:
        return False
    return recovered.lower() == expected_address.lower()


def sign_hash(data_hash: str, private_key_hex: str) -> str:
    """Sign a SHA-256 hex hash with EIP-191 personal_sign. Returns 0x-prefixed signature."""
    pk = private_key_hex.strip().lower().removeprefix("0x")
    message = encode_defunct(text=data_hash)
    signed = Account.sign_message(message, private_key=bytes.fromhex(pk))
    return signed.signature.to_0x_hex() if hasattr(signed.signature, "to_0x_hex") else signed.signature.hex()


def public_key_to_address(public_key_hex: str) -> str:
    """Derive checksum Ethereum address from an uncompressed secp256k1 public key (hex, no 0x)."""
    pk_bytes = bytes.fromhex(public_key_hex.removeprefix("0x"))
    if len(pk_bytes) == 65 and pk_bytes[0] == 0x04:
        pk_bytes = pk_bytes[1:]
    if len(pk_bytes) != 64:
        raise ValueError("Public key must be 64 raw bytes (uncompressed, no 0x04 prefix)")
    pk = keys.PublicKey(pk_bytes)
    return pk.to_checksum_address()


def generate_keypair() -> tuple[str, str, str]:
    """Generate a new secp256k1 keypair.

    Returns (private_key_hex, public_key_hex, eth_address).
    """
    raw = secrets.token_bytes(32)
    pk = keys.PrivateKey(raw)
    private_key_hex = pk.to_hex()
    public_key_hex = pk.public_key.to_hex()
    eth_address = pk.public_key.to_checksum_address()
    return private_key_hex, public_key_hex, eth_address
