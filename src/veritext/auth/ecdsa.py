"""
ECDSA secp256k1 signing/verification.

EIP-712 typed-data is the primary path (improvement #6); EIP-191 personal_sign
remains supported as a fallback verifier for backward compatibility.

The Veritext EIP-712 domain is **immutable once published**:
    name:              "Veritext"
    version:           "2"
    chainId:           1
    verifyingContract: 0x0000...0000

Anchors sign a `VeritextAnchor` typed struct:
    text_hash:    bytes32   # sha256(text)
    issuer_id:    uint256
    timestamp:    uint256   # unix seconds
    bundle_nonce: bytes32   # bundle_id_canonical_hash (links sig to bundle)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from eth_account import Account
from eth_account.messages import encode_defunct, encode_typed_data


VERITEXT_DOMAIN: dict[str, Any] = {
    "name": "Veritext",
    "version": "2",
    "chainId": 1,
    "verifyingContract": "0x0000000000000000000000000000000000000000",
}

VERITEXT_TYPES: dict[str, list[dict[str, str]]] = {
    "EIP712Domain": [
        {"name": "name", "type": "string"},
        {"name": "version", "type": "string"},
        {"name": "chainId", "type": "uint256"},
        {"name": "verifyingContract", "type": "address"},
    ],
    "VeritextAnchor": [
        {"name": "textHash", "type": "bytes32"},
        {"name": "issuerId", "type": "uint256"},
        {"name": "timestamp", "type": "uint256"},
        {"name": "bundleNonce", "type": "bytes32"},
    ],
}


@dataclass
class TypedDataMessage:
    text_hash: bytes  # 32 bytes
    issuer_id: int
    timestamp: int
    bundle_nonce: bytes  # 32 bytes

    def to_eip712(self) -> dict[str, Any]:
        return {
            "types": VERITEXT_TYPES,
            "primaryType": "VeritextAnchor",
            "domain": VERITEXT_DOMAIN,
            "message": {
                "textHash": self.text_hash,
                "issuerId": self.issuer_id,
                "timestamp": self.timestamp,
                "bundleNonce": self.bundle_nonce,
            },
        }


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class EcdsaService:
    @staticmethod
    def sign_eip712(message: TypedDataMessage, private_key_hex: str) -> str:
        signable = encode_typed_data(full_message=message.to_eip712())
        signed = Account.sign_message(signable, private_key=private_key_hex)
        return signed.signature.hex()

    @staticmethod
    def sign_eip191(text_hash_hex: str, private_key_hex: str) -> str:
        msg = encode_defunct(hexstr=text_hash_hex)
        signed = Account.sign_message(msg, private_key=private_key_hex)
        return signed.signature.hex()


def recover_address_eip712(message: TypedDataMessage, signature_hex: str) -> str:
    signable = encode_typed_data(full_message=message.to_eip712())
    return Account.recover_message(signable, signature=_normalize_sig(signature_hex))


def recover_address_eip191(text_hash_hex: str, signature_hex: str) -> str:
    msg = encode_defunct(hexstr=text_hash_hex)
    return Account.recover_message(msg, signature=_normalize_sig(signature_hex))


def _normalize_sig(signature_hex: str) -> bytes:
    s = signature_hex
    if s.startswith("0x") or s.startswith("0X"):
        s = s[2:]
    return bytes.fromhex(s)
