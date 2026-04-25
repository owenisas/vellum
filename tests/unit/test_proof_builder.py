"""Unit tests for :class:`ProofBundleBuilder`."""

from __future__ import annotations

from watermark import DetectResult, PayloadInfo

from vellum.chain.protocol import ChainReceipt
from vellum.config import ChainBackendType
from vellum.services.proof_builder import ProofBundleBuilder


COMPANY = {
    "issuer_id": 42,
    "name": "Acme AI",
    "eth_address": "0x1234567890abcdef1234567890abcdef12345678",
    "public_key_hex": "0x" + "ab" * 64,
}

SIG = "0x" + "11" * 65


def _empty_watermark() -> DetectResult:
    return DetectResult(False, 0, 0, 0, [])


def _populated_watermark() -> DetectResult:
    payloads = [
        PayloadInfo(
            schema_version=1,
            issuer_id=42,
            model_id=1001,
            model_version_id=1,
            key_id=1,
            crc_valid=True,
            raw_payload_hex="0x" + "01" * 8,
        ),
        PayloadInfo(
            schema_version=1,
            issuer_id=42,
            model_id=1001,
            model_version_id=1,
            key_id=1,
            crc_valid=True,
            raw_payload_hex="0x" + "02" * 8,
        ),
    ]
    return DetectResult(True, 2, 2, 0, payloads)


def _receipt(*, solana_sig: str | None = None, block_num: int = 1) -> ChainReceipt:
    return ChainReceipt(
        tx_hash="a" * 64,
        block_num=block_num,
        data_hash="b" * 64,
        issuer_id=42,
        timestamp="2026-01-01T00:00:00+00:00",
        solana_tx_signature=solana_sig,
    )


def test_simulated_bundle_shape():
    builder = ProofBundleBuilder(ChainBackendType.SIMULATED)
    bundle = builder.build(
        receipt=_receipt(),
        company=COMPANY,
        watermark=_empty_watermark(),
        signature_hex=SIG,
    )

    assert bundle["spec"] == "vellum-proof-bundle/v2"
    assert bundle["bundle_id"].startswith("vpb2_")

    assert bundle["anchors"][0]["type"] == "simulated_chain"
    assert bundle["anchors"][0]["network"] == "vellum-simulated"
    assert bundle["anchors"][0]["tx_hash"] == "a" * 64
    assert bundle["verification_hints"]["chain_type"] == "simulated"
    assert "explorer_url" in bundle["verification_hints"]


def test_solana_bundle_includes_explorer_url():
    builder = ProofBundleBuilder(
        ChainBackendType.SOLANA,
        solana_cluster="devnet",
        solana_rpc_url="https://api.devnet.solana.com",
    )
    bundle = builder.build(
        receipt=_receipt(solana_sig="5abc"),
        company=COMPANY,
        watermark=_empty_watermark(),
        signature_hex=SIG,
    )

    anchor = bundle["anchors"][0]
    hints = bundle["verification_hints"]

    assert anchor["type"] == "solana"
    assert anchor["tx_signature"] == "5abc"
    assert anchor["network"] == "solana-devnet"
    assert hints["chain_type"] == "solana"
    assert hints["cluster"] == "devnet"
    assert "explorer.solana.com" in hints["explorer_url"]
    assert "devnet" in hints["explorer_url"]
    assert hints["explorer_url"].endswith("?cluster=devnet")


def test_bundle_id_deterministic():
    builder = ProofBundleBuilder(ChainBackendType.SIMULATED)
    a = builder.build(
        receipt=_receipt(),
        company=COMPANY,
        watermark=_empty_watermark(),
        signature_hex=SIG,
    )
    b = builder.build(
        receipt=_receipt(),
        company=COMPANY,
        watermark=_empty_watermark(),
        signature_hex=SIG,
    )
    assert a["bundle_id"] == b["bundle_id"]


def test_bundle_id_excludes_self():
    """Mutating the embedded `bundle_id` must not change the recomputed id."""
    builder = ProofBundleBuilder(ChainBackendType.SIMULATED)
    bundle = builder.build(
        receipt=_receipt(),
        company=COMPANY,
        watermark=_empty_watermark(),
        signature_hex=SIG,
    )
    original_id = bundle["bundle_id"]

    tampered = dict(bundle)
    tampered["bundle_id"] = "vpb2_tampered"
    recomputed = ProofBundleBuilder.bundle_id(tampered)

    assert recomputed == original_id


def test_watermark_payloads_pass_through():
    builder = ProofBundleBuilder(ChainBackendType.SIMULATED)
    bundle = builder.build(
        receipt=_receipt(),
        company=COMPANY,
        watermark=_populated_watermark(),
        signature_hex=SIG,
    )

    payloads = bundle["watermark"]["payloads"]
    assert len(payloads) == 2
    for p in payloads:
        assert p["issuer_id"] == 42
        assert p["model_id"] == 1001
        assert p["crc_valid"] is True
    assert bundle["watermark"]["detected"] is True
    assert bundle["watermark"]["valid_count"] == 2
