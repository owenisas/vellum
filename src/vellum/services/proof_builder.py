"""Builds Proof Bundle v2 documents.

Extracted from AnchorService so it can be unit-tested in isolation.
"""

from __future__ import annotations

import hashlib
import json

from watermark import DetectResult

from vellum.chain.protocol import ChainReceipt
from vellum.config import ChainBackendType


class ProofBundleBuilder:
    """Build self-verifiable provenance bundles."""

    SPEC = "vellum-proof-bundle/v2"

    def __init__(
        self,
        chain_backend: ChainBackendType,
        solana_cluster: str | None = None,
        solana_rpc_url: str | None = None,
    ) -> None:
        self.chain_backend = chain_backend
        self.solana_cluster = solana_cluster or "devnet"
        self.solana_rpc_url = solana_rpc_url or "https://api.devnet.solana.com"

    def build(
        self,
        *,
        receipt: ChainReceipt,
        company: dict,
        watermark: DetectResult,
        signature_hex: str,
    ) -> dict:
        """Construct a Proof Bundle v2 dict (pre-`bundle_id`)."""
        text_hash = receipt.data_hash

        watermark_payloads = [p.to_dict() for p in watermark.payloads]
        watermark_section = {
            "detected": bool(watermark.watermarked),
            "tag_count": watermark.tag_count,
            "valid_count": watermark.valid_count,
            "invalid_count": watermark.invalid_count,
            "payloads": watermark_payloads,
        }

        if self.chain_backend == ChainBackendType.SOLANA and receipt.solana_tx_signature:
            anchors = [
                {
                    "type": "solana",
                    "network": f"solana-{self.solana_cluster}",
                    "tx_signature": receipt.solana_tx_signature,
                    "block_num": receipt.block_num,
                    "timestamp": receipt.timestamp,
                    "data_hash": text_hash,
                }
            ]
            verification_hints = {
                "chain_type": "solana",
                "cluster": self.solana_cluster,
                "rpc_urls": [self.solana_rpc_url],
                "explorer_url": (
                    f"https://explorer.solana.com/tx/{receipt.solana_tx_signature}"
                    f"?cluster={self.solana_cluster}"
                ),
                "memo_program": "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr",
            }
        else:
            anchors = [
                {
                    "type": "simulated_chain",
                    "network": "vellum-simulated",
                    "tx_hash": receipt.tx_hash,
                    "block_num": receipt.block_num,
                    "timestamp": receipt.timestamp,
                    "data_hash": text_hash,
                }
            ]
            verification_hints = {
                "chain_type": "simulated",
                "explorer_url": f"/api/chain/blocks/{receipt.block_num}",
            }

        bundle = {
            "spec": self.SPEC,
            "hashing": {
                "algorithm": "sha256",
                "text_hash": text_hash,
                "input_encoding": "utf-8",
                "normalization": "none",
            },
            "issuer": {
                "issuer_id": int(company.get("issuer_id", 0)),
                "name": company.get("name", ""),
                "eth_address": company.get("eth_address", ""),
                "public_key_hex": company.get("public_key_hex", ""),
            },
            "signature": {
                "scheme": "eip191_personal_sign",
                "signed_payload": f"sha256:{text_hash}",
                "signature_hex": signature_hex,
                "recoverable_address": True,
            },
            "watermark": watermark_section,
            "anchors": anchors,
            "verification_hints": verification_hints,
        }
        bundle["bundle_id"] = self.bundle_id(bundle)
        return bundle

    @staticmethod
    def bundle_id(payload: dict) -> str:
        """SHA-256 of canonical JSON, prefixed with 'vpb2_'.

        We strip any pre-existing `bundle_id` because it's self-referential.
        """
        copy = {k: v for k, v in payload.items() if k != "bundle_id"}
        canonical = json.dumps(copy, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"vpb2_{digest}"
