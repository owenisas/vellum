from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .proof_bundle import ProofBundleV2


class AnchorRequest(BaseModel):
    text: str
    raw_text: str | None = None
    issuer_id: int
    signature_hex: str
    sig_scheme: str = "eip712"  # or "eip191_personal_sign"
    timestamp: int  # unix seconds, signed in EIP-712
    bundle_nonce_hex: str | None = None  # 32-byte bundle nonce, signed in EIP-712
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChainReceiptModel(BaseModel):
    tx_hash: str
    block_num: int
    data_hash: str
    issuer_id: int
    timestamp: str
    solana_tx_signature: str | None = None
    merkle_root: str | None = None
    leaf_index: int | None = None
    inclusion_proof: list[dict[str, str]] = Field(default_factory=list)


class AnchorResponse(BaseModel):
    verified_signer: str
    eth_address: str
    sha256_hash: str
    chain_receipt: ChainReceiptModel
    proof_bundle_v2: ProofBundleV2
    bundle_status: str = "ok"  # "ok" | "pending_batch"


class VerifyRequest(BaseModel):
    text: str


class VerifyResponse(BaseModel):
    verified: bool
    sha256_hash: str
    issuer_id: int | None = None
    company: str | None = None
    eth_address: str | None = None
    block_num: int | None = None
    tx_hash: str | None = None
    timestamp: str | None = None
    watermark: dict[str, Any]
    proof_bundle_v2: ProofBundleV2 | None = None
    reason: str | None = None


class ProofResponse(BaseModel):
    proof_bundle_v2: ProofBundleV2
    bundle_status: str = "ok"
