"""Browser wallet signature verification helpers.

The backend only verifies public wallet proofs. Private keys stay in browser
wallets such as MetaMask, Phantom, or Solflare.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from eth_account import Account
from eth_account.messages import encode_defunct
from pydantic import BaseModel, Field

WalletType = Literal["evm", "solana"]
SignatureEncoding = Literal["base64", "hex", "base58"]

_B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_INDEX = {ch: idx for idx, ch in enumerate(_B58_ALPHABET)}


class WalletProof(BaseModel):
    """Proof that a browser wallet authorized anchoring a specific text hash."""

    wallet_type: WalletType
    address: str
    message: str
    signature: str
    signature_encoding: SignatureEncoding = "base64"
    chain_id: str | None = None
    cluster: str | None = None
    tx_signature: str | None = None


class WalletNonceResponse(BaseModel):
    """Canonical message for frontend wallet signing prompts."""

    wallet_type: WalletType
    address: str
    data_hash: str = Field(min_length=64, max_length=64)
    message: str


@dataclass(frozen=True)
class VerifiedWalletProof:
    wallet_type: WalletType
    address: str
    message: str
    signature: str
    signature_encoding: str
    chain_id: str | None = None
    cluster: str | None = None
    tx_signature: str | None = None
    on_chain: dict | None = None

    def to_dict(self) -> dict:
        return {
            "wallet_type": self.wallet_type,
            "address": self.address,
            "message": self.message,
            "signature": self.signature,
            "signature_encoding": self.signature_encoding,
            "chain_id": self.chain_id,
            "cluster": self.cluster,
            "tx_signature": self.tx_signature,
            "on_chain": self.on_chain,
        }


def build_wallet_message(data_hash: str, wallet_type: WalletType, address: str) -> str:
    """Return the exact message a wallet must sign for a text hash."""
    _validate_sha256(data_hash)
    return (
        "Vellum wallet proof\n"
        f"wallet_type: {wallet_type}\n"
        f"address: {address}\n"
        f"text_hash: {data_hash}\n"
        "purpose: authorize_ai_provenance_anchor"
    )


def verify_wallet_proof(
    proof: WalletProof,
    *,
    data_hash: str,
    on_chain: dict | None = None,
) -> VerifiedWalletProof:
    """Verify wallet control and return normalized proof metadata."""
    expected_message = build_wallet_message(data_hash, proof.wallet_type, proof.address)
    if proof.message != expected_message:
        raise ValueError("Wallet proof message does not match anchored text hash")

    if proof.wallet_type == "evm":
        _verify_evm(proof)
    else:
        _verify_solana(proof)

    return VerifiedWalletProof(
        wallet_type=proof.wallet_type,
        address=proof.address,
        message=proof.message,
        signature=proof.signature,
        signature_encoding=proof.signature_encoding,
        chain_id=proof.chain_id,
        cluster=proof.cluster,
        tx_signature=proof.tx_signature,
        on_chain=on_chain,
    )


def _verify_evm(proof: WalletProof) -> None:
    message = encode_defunct(text=proof.message)
    try:
        recovered = Account.recover_message(message, signature=_normalize_hex(proof.signature))
    except Exception as exc:
        raise ValueError("Invalid EVM wallet proof signature") from exc

    if recovered.lower() != proof.address.lower():
        raise ValueError("EVM wallet proof signature does not match address")


def _verify_solana(proof: WalletProof) -> None:
    try:
        public_key = Ed25519PublicKey.from_public_bytes(base58_decode(proof.address))
        signature = decode_signature(proof.signature, proof.signature_encoding)
        public_key.verify(signature, proof.message.encode("utf-8"))
    except InvalidSignature as exc:
        raise ValueError("Invalid Solana wallet proof signature") from exc
    except Exception as exc:
        raise ValueError("Invalid Solana wallet proof") from exc


def decode_signature(signature: str, encoding: str) -> bytes:
    if encoding == "base64":
        return base64.b64decode(signature, validate=True)
    if encoding == "hex":
        return bytes.fromhex(signature.removeprefix("0x"))
    if encoding == "base58":
        return base58_decode(signature)
    raise ValueError(f"Unsupported signature encoding: {encoding}")


def base58_decode(value: str) -> bytes:
    """Decode Solana base58 values without adding another dependency."""
    num = 0
    for char in value:
        if char not in _B58_INDEX:
            raise ValueError("Invalid base58 character")
        num = num * 58 + _B58_INDEX[char]

    decoded = num.to_bytes((num.bit_length() + 7) // 8, "big") if num else b""
    leading_zeroes = len(value) - len(value.lstrip("1"))
    return b"\0" * leading_zeroes + decoded


def base58_encode(data: bytes) -> str:
    """Encode bytes as base58; useful for tests and local wallet tooling."""
    if not data:
        return ""
    num = int.from_bytes(data, "big")
    chars: list[str] = []
    while num:
        num, rem = divmod(num, 58)
        chars.append(_B58_ALPHABET[rem])
    leading_zeroes = len(data) - len(data.lstrip(b"\0"))
    return "1" * leading_zeroes + "".join(reversed(chars or ["1"]))


def _normalize_hex(value: str) -> str:
    value = value.strip()
    return value if value.startswith("0x") else f"0x{value}"


def _validate_sha256(value: str) -> None:
    try:
        raw = bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError("data_hash must be a SHA-256 hex string") from exc
    if len(raw) != 32:
        raise ValueError("data_hash must be 32 bytes")
