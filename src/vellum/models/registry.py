"""Registry / anchor / verify / proof / health / demo response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .chain import ChainReceiptModel
from .chat import WatermarkInfo, WmParams


class HealthResponse(BaseModel):
    status: str = "ok"
    demo_mode: str = "live"
    chain_backend: str = "simulated"
    solana_cluster: str | None = None
    auth0_enabled: bool = False
    google_api_key_configured: bool = False
    minimax_api_key_configured: bool = False
    chain: dict = Field(
        default_factory=lambda: {"length": 0, "valid": True, "message": "ok"}
    )


class AnchorRequest(BaseModel):
    text: str
    raw_text: str = ""
    signature_hex: str
    issuer_id: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    wm_params: WmParams | None = None


class ProofBundleV2(BaseModel):
    spec: str = "vellum-proof-bundle/v2"
    bundle_id: str
    hashing: dict[str, Any]
    issuer: dict[str, Any]
    signature: dict[str, Any]
    watermark: dict[str, Any]
    anchors: list[dict[str, Any]] = Field(default_factory=list)
    verification_hints: dict[str, Any] = Field(default_factory=dict)


class AnchorResponse(BaseModel):
    verified_signer: str
    eth_address: str
    sha256_hash: str
    chain_receipt: ChainReceiptModel
    proof_bundle_v2: ProofBundleV2


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
    watermark: WatermarkInfo
    proof_bundle_v2: ProofBundleV2 | None = None
    reason: str | None = None


class ProofByTextRequest(BaseModel):
    text: str


class ProofResponse(BaseModel):
    found: bool
    proof_bundle_v2: ProofBundleV2 | None = None
    reason: str | None = None


class ProofSpecResponse(BaseModel):
    spec: str = "vellum-proof-bundle/v2"
    description: str = "Self-verifiable proof bundle for AI-generated text provenance."
    schema_url: str = "/api/proof/spec"
    sections: list[str] = Field(
        default_factory=lambda: [
            "hashing",
            "issuer",
            "signature",
            "watermark",
            "anchors",
            "verification_hints",
        ]
    )


class SolanaVerifyResponse(BaseModel):
    verified: bool = False
    tx_signature: str
    slot: int | None = None
    memo_data: dict | None = None
    explorer_url: str | None = None
    reason: str | None = None


class SolanaBalanceResponse(BaseModel):
    address: str
    cluster: str
    balance_sol: float
    balance_lamports: int


class DemoScenarioResponse(BaseModel):
    company: dict[str, Any]
    text: str
    watermarked_text: str
    watermark: WatermarkInfo
    signature_hex: str
    sha256_hash: str
    instructions: list[str]


class ResetResponse(BaseModel):
    status: str = "ok"
    cleared: dict[str, int] = Field(default_factory=dict)


class ResponseRecord(BaseModel):
    id: int
    sha256_hash: str
    issuer_id: int
    signature_hex: str
    raw_text: str
    watermarked_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
