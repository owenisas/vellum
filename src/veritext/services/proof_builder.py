"""
ProofBuilder — assembles the v2 bundle, signs it with JCS canonicalization
(improvement #1), enumerates signed_fields, and embeds inclusion proofs +
encrypted-payload metadata (improvements #3, #5, #6, #7, #14, #15).
"""

from __future__ import annotations

import hashlib
from typing import Any

from veritext.config import AppSettings
from veritext.db.repositories import KeyRotationRepo
from veritext.models.proof_bundle import (
    AnchorInfo,
    EncryptedPayloadMetadata,
    GenerationTimeInfo,
    HashingInfo,
    InclusionProofStep,
    IssuerInfo,
    ProofBundleV2,
    SignatureInfo,
    TypedDataView,
    VerificationHints,
    WatermarkInfo,
    WatermarkPayloadInfo,
)

from ._jcs import canonicalize
from .watermark_service import CombinedDetectResult


SIGNED_FIELDS = ["spec", "hashing", "issuer", "watermark", "anchors", "verification_hints"]


def _bundle_id_from_canonical(bundle_minus_sig_minus_id: dict[str, Any]) -> str:
    canon = canonicalize(bundle_minus_sig_minus_id)
    return "vtb2_" + hashlib.sha256(canon).hexdigest()


class ProofBuilder:
    def __init__(self, *, settings: AppSettings, key_repo: KeyRotationRepo | None = None) -> None:
        self._settings = settings
        self._keys = key_repo

    async def build(
        self,
        *,
        text_hash: str,
        company: dict[str, Any],
        wm_detect: CombinedDetectResult,
        chain_receipt: Any | None,  # ChainReceipt or None when pending
        chain_backend_type: str,
        sig_scheme: str,
        signature_hex: str,
        timestamp: int | None,
        bundle_nonce_hex: str | None,
        pending_batch: bool = False,
    ) -> ProofBundleV2:
        # Issuer info with key_history
        key_history: list[dict[str, Any]] = []
        if self._keys is not None:
            keys = await self._keys.list_for_issuer(company["issuer_id"])
            for k in keys:
                key_history.append(
                    {
                        "key_id": k["key_id"],
                        "eth_address": k["eth_address"],
                        "public_key_hex": k["public_key_hex"],
                        "active_from": k["active_from"],
                        "active_until": k["active_until"],
                    }
                )

        issuer = IssuerInfo(
            issuer_id=company["issuer_id"],
            name=company["name"],
            eth_address=company["eth_address"],
            public_key_hex=company["public_key_hex"],
            current_key_id=company.get("current_key_id", 1),
            key_history=key_history,
        )

        # Watermark
        wm_info = self._build_watermark_info(wm_detect)

        # Anchors
        anchors: list[AnchorInfo] = []
        verification_hints = VerificationHints(
            chain_type=chain_backend_type,
            rpc_url=self._settings.solana.solana_rpc_url
            if chain_backend_type == "solana"
            else None,
            explorer_url=None,
            merkle_root=getattr(chain_receipt, "merkle_root", None),
        )

        if pending_batch:
            anchors.append(
                AnchorInfo(
                    type="solana_merkle" if chain_backend_type == "solana" else "simulated_chain",
                    timestamp="pending",
                )
            )
        elif chain_receipt is not None:
            anchor_type = self._anchor_type(chain_backend_type, chain_receipt)
            anchor_info = AnchorInfo(
                type=anchor_type,
                tx_hash=chain_receipt.tx_hash,
                block_num=chain_receipt.block_num,
                timestamp=chain_receipt.timestamp,
                memo_encoding="borsh" if chain_backend_type == "solana" else "json",
                merkle_root=chain_receipt.merkle_root,
                inclusion_proof=[
                    InclusionProofStep(hash=s.hash, side=s.side)
                    for s in (chain_receipt.inclusion_proof or [])
                ],
                leaf_index=chain_receipt.leaf_index,
            )
            if chain_receipt.solana_tx_signature:
                verification_hints.explorer_url = (
                    f"https://explorer.solana.com/tx/{chain_receipt.solana_tx_signature}"
                    f"?cluster={self._settings.solana.solana_cluster}"
                )
                anchor_info.tx_hash = chain_receipt.solana_tx_signature
            anchors.append(anchor_info)

        # Encrypted payload metadata
        encrypted_meta: EncryptedPayloadMetadata | None = None
        if (
            self._settings.watermark.payload_visibility.value == "encrypted"
            and any(p.get("encrypted") for p in wm_detect.payloads)
        ):
            encrypted_meta = EncryptedPayloadMetadata(
                key_kid=int(self._settings.watermark.watermark_encryption_key[:2] or "0", 16),
                algorithm="aes-128-ccm",
            )

        hashing = HashingInfo(text_hash=text_hash)

        # Build the bundle minus signature + bundle_id + signed_fields,
        # canonicalize via JCS, hash → bundle_id. The CLI verifier uses the
        # exact same "everything-except-{signature,bundle_id,signed_fields}"
        # rule.
        partial = {
            "spec": "veritext-proof-bundle/v2",
            "hashing": hashing.model_dump(),
            "issuer": issuer.model_dump(),
            "watermark": wm_info.model_dump(),
            "encrypted_payload_metadata": (
                encrypted_meta.model_dump() if encrypted_meta else None
            ),
            "anchors": [a.model_dump() for a in anchors],
            "verification_hints": verification_hints.model_dump(),
        }
        bundle_id = _bundle_id_from_canonical(partial)

        # Build signature info
        signed_payload_canon = canonicalize(partial)
        signed_payload_hash = "sha256:" + hashlib.sha256(signed_payload_canon).hexdigest()

        typed_data = None
        if sig_scheme == "eip712" and timestamp and bundle_nonce_hex:
            typed_data = TypedDataView(
                domain={
                    "name": "Veritext",
                    "version": "2",
                    "chainId": 1,
                    "verifyingContract": "0x0000000000000000000000000000000000000000",
                },
                types={
                    "VeritextAnchor": [
                        {"name": "textHash", "type": "bytes32"},
                        {"name": "issuerId", "type": "uint256"},
                        {"name": "timestamp", "type": "uint256"},
                        {"name": "bundleNonce", "type": "bytes32"},
                    ]
                },
                primaryType="VeritextAnchor",
                message={
                    "textHash": "0x" + text_hash,
                    "issuerId": company["issuer_id"],
                    "timestamp": timestamp,
                    "bundleNonce": bundle_nonce_hex,
                },
            )

        signature = SignatureInfo(
            scheme=sig_scheme,  # type: ignore
            canonicalization="rfc8785",
            signed_payload=signed_payload_hash,
            signature_hex=signature_hex,
            recoverable_address=True,
            typed_data=typed_data,
        )

        return ProofBundleV2(
            bundle_id=bundle_id,
            signed_fields=["spec", "bundle_id", *SIGNED_FIELDS],
            hashing=hashing,
            issuer=issuer,
            signature=signature,
            watermark=wm_info,
            encrypted_payload_metadata=encrypted_meta,
            anchors=anchors,
            verification_hints=verification_hints,
        )

    def _anchor_type(self, chain_backend_type: str, receipt: Any) -> str:
        if chain_backend_type == "solana":
            if receipt.merkle_root:
                return "solana_merkle"
            return "solana_per_response"
        return "simulated_chain"

    def _build_watermark_info(self, detect: CombinedDetectResult) -> WatermarkInfo:
        payloads = [
            WatermarkPayloadInfo(
                schema_version=p["schema_version"],
                issuer_id=p["issuer_id"],
                model_id=p["model_id"],
                model_version_id=p["model_version_id"],
                key_id=p["key_id"],
                fec={
                    "type": "bch63_16",
                    "errors_corrected": p.get("errors_corrected", 0),
                    "code_valid": p.get("code_valid", False),
                },
                encrypted=False,
                raw_payload_hex=p["raw_payload_hex"],
            )
            for p in detect.payloads
        ]
        gen_time = None
        if detect.statistical:
            gen_time = GenerationTimeInfo(
                type=detect.statistical.get("type", "synthid"),
                present=bool(detect.statistical.get("present", False)),
                detector_score=float(detect.statistical.get("detector_score", 0.0)),
                p_value=float(detect.statistical.get("p_value", 1.0)),
            )
        return WatermarkInfo(
            detected=detect.unicode["detected"],
            injection_mode=self._settings.watermark.watermark_injection_mode.value,  # type: ignore
            generation_time=gen_time,
            tag_count=detect.unicode["tag_count"],
            valid_count=detect.unicode["valid_count"],
            invalid_count=detect.unicode["invalid_count"],
            payloads=payloads,
        )
