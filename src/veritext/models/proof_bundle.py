"""Proof Bundle v2 schema (Pydantic) — cumulative result of improvements 1, 3, 5, 6, 7, 14, 15."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class HashingInfo(BaseModel):
    algorithm: Literal["sha256"] = "sha256"
    text_hash: str
    input_encoding: Literal["utf-8"] = "utf-8"
    normalization: Literal["none"] = "none"


class IssuerInfo(BaseModel):
    issuer_id: int
    name: str
    eth_address: str
    public_key_hex: str
    current_key_id: int = 1
    key_history: list[dict[str, Any]] = Field(default_factory=list)


class TypedDataView(BaseModel):
    domain: dict[str, Any]
    types: dict[str, Any]
    primaryType: str
    message: dict[str, Any]


class SignatureInfo(BaseModel):
    scheme: Literal["eip712", "eip191_personal_sign"]
    canonicalization: Literal["rfc8785"] = "rfc8785"
    signed_payload: str  # sha256:hex of canonical bundle minus signature
    signature_hex: str
    recoverable_address: bool = True
    typed_data: TypedDataView | None = None


class WatermarkPayloadInfo(BaseModel):
    schema_version: int
    issuer_id: int
    model_id: int
    model_version_id: int
    key_id: int
    fec: dict[str, Any] = Field(default_factory=lambda: {"type": "bch63_16", "errors_corrected": 0})
    encrypted: bool = False
    nonce_hex: str | None = None
    raw_payload_hex: str


class GenerationTimeInfo(BaseModel):
    type: str = "synthid"
    present: bool = False
    detector_score: float = 0.0
    p_value: float = 1.0


class WatermarkInfo(BaseModel):
    detected: bool
    injection_mode: Literal["whitespace", "grapheme"] = "whitespace"
    generation_time: GenerationTimeInfo | None = None
    tag_count: int
    valid_count: int
    invalid_count: int
    payloads: list[WatermarkPayloadInfo] = Field(default_factory=list)


class EncryptedPayloadMetadata(BaseModel):
    key_kid: int
    algorithm: Literal["aes-128-ccm"] = "aes-128-ccm"


class InclusionProofStep(BaseModel):
    hash: str
    side: Literal["L", "R"]


class AnchorInfo(BaseModel):
    type: Literal["solana_per_response", "solana_merkle", "simulated_chain"]
    tx_hash: str | None = None
    block_num: int | None = None
    timestamp: str
    memo_encoding: Literal["borsh", "json"] = "json"
    memo_borsh_hex: str | None = None
    merkle_root: str | None = None
    inclusion_proof: list[InclusionProofStep] = Field(default_factory=list)
    leaf_index: int | None = None


class VerificationHints(BaseModel):
    chain_type: str
    rpc_url: str | None = None
    explorer_url: str | None = None
    merkle_root: str | None = None


class ProofBundleV2(BaseModel):
    spec: Literal["veritext-proof-bundle/v2"] = "veritext-proof-bundle/v2"
    bundle_id: str  # vtb2_<sha256>
    signed_fields: list[str] = Field(
        default_factory=lambda: [
            "spec",
            "bundle_id",
            "hashing",
            "issuer",
            "watermark",
            "anchors",
            "verification_hints",
        ]
    )
    hashing: HashingInfo
    issuer: IssuerInfo
    signature: SignatureInfo
    watermark: WatermarkInfo
    encrypted_payload_metadata: EncryptedPayloadMetadata | None = None
    anchors: list[AnchorInfo] = Field(default_factory=list)
    verification_hints: VerificationHints
