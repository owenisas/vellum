"""
AnchorService — orchestrates verify-signature + write-response + anchor-chain
for an /api/anchor request.

When `anchor_strategy=merkle_batch`, the data hash is enqueued in
`pending_anchors`; the actual chain block is written by MerkleBatchService.
The bundle returns `pending_batch` until the batch closes.
"""

from __future__ import annotations

import json
from typing import Any

from veritext.config import AnchorStrategy
from veritext.db.repositories import (
    ChainRepo,
    CompanyRepo,
    KeyRotationRepo,
    PendingAnchorRepo,
    ResponseRepo,
)
from veritext.models.registry import (
    AnchorRequest,
    AnchorResponse,
    ChainReceiptModel,
)
from .proof_builder import ProofBuilder
from .signing_service import SigningError, SigningService
from .watermark_service import WatermarkService


class AnchorError(Exception):
    pass


class AnchorService:
    def __init__(
        self,
        *,
        chain,
        company_repo: CompanyRepo,
        response_repo: ResponseRepo,
        chain_repo: ChainRepo,
        pending_repo: PendingAnchorRepo,
        key_repo: KeyRotationRepo,
        signing: SigningService,
        watermark: WatermarkService,
        proof_builder: ProofBuilder,
        anchor_strategy: AnchorStrategy,
        chain_backend_type: str,
    ) -> None:
        self._chain = chain
        self._companies = company_repo
        self._responses = response_repo
        self._chain_repo = chain_repo
        self._pending = pending_repo
        self._keys = key_repo
        self._signing = signing
        self._wm = watermark
        self._proof = proof_builder
        self._strategy = anchor_strategy
        self._chain_backend_type = chain_backend_type

    async def anchor(self, req: AnchorRequest) -> AnchorResponse:
        try:
            text_hash, recovered = await self._signing.verify_anchor(
                text=req.text,
                issuer_id=req.issuer_id,
                signature_hex=req.signature_hex,
                sig_scheme=req.sig_scheme,
                timestamp=req.timestamp,
                bundle_nonce_hex=req.bundle_nonce_hex,
            )
        except SigningError as exc:
            raise AnchorError(str(exc)) from exc

        company = await self._companies.get_by_issuer(req.issuer_id)
        assert company is not None  # verified in signing service
        wm_result = self._wm.detect(req.text)

        if self._strategy == AnchorStrategy.MERKLE_BATCH:
            return await self._anchor_merkle(
                req=req,
                text_hash=text_hash,
                recovered=recovered,
                company=company,
                wm_result=wm_result,
            )
        return await self._anchor_per_response(
            req=req,
            text_hash=text_hash,
            recovered=recovered,
            company=company,
            wm_result=wm_result,
        )

    async def _anchor_per_response(
        self, *, req: AnchorRequest, text_hash: str, recovered: str, company: dict[str, Any], wm_result
    ) -> AnchorResponse:
        receipt = await self._chain.anchor(
            data_hash=text_hash,
            issuer_id=req.issuer_id,
            signature_hex=req.signature_hex,
            metadata=req.metadata,
        )
        bundle = await self._proof.build(
            text_hash=text_hash,
            company=company,
            wm_detect=wm_result,
            chain_receipt=receipt,
            chain_backend_type=self._chain_backend_type,
            sig_scheme=req.sig_scheme,
            signature_hex=req.signature_hex,
            timestamp=req.timestamp,
            bundle_nonce_hex=req.bundle_nonce_hex,
        )
        await self._responses.save(
            sha256_hash=text_hash,
            issuer_id=req.issuer_id,
            signature_hex=req.signature_hex,
            sig_scheme=req.sig_scheme,
            raw_text=req.raw_text or req.text,
            watermarked_text=req.text,
            metadata=req.metadata,
            bundle_id=bundle.bundle_id,
        )
        return AnchorResponse(
            verified_signer=recovered,
            eth_address=recovered,
            sha256_hash=text_hash,
            chain_receipt=ChainReceiptModel(
                tx_hash=receipt.tx_hash,
                block_num=receipt.block_num,
                data_hash=receipt.data_hash,
                issuer_id=receipt.issuer_id,
                timestamp=receipt.timestamp,
                solana_tx_signature=receipt.solana_tx_signature,
            ),
            proof_bundle_v2=bundle,
            bundle_status="ok",
        )

    async def _anchor_merkle(
        self, *, req: AnchorRequest, text_hash: str, recovered: str, company: dict[str, Any], wm_result
    ) -> AnchorResponse:
        # Build a "pending" bundle (no chain receipt yet) and enqueue.
        bundle = await self._proof.build(
            text_hash=text_hash,
            company=company,
            wm_detect=wm_result,
            chain_receipt=None,
            chain_backend_type=self._chain_backend_type,
            sig_scheme=req.sig_scheme,
            signature_hex=req.signature_hex,
            timestamp=req.timestamp,
            bundle_nonce_hex=req.bundle_nonce_hex,
            pending_batch=True,
        )
        await self._pending.enqueue(
            bundle_id=bundle.bundle_id,
            data_hash=text_hash,
            issuer_id=req.issuer_id,
            signature_hex=req.signature_hex,
            payload={"sig_scheme": req.sig_scheme, "metadata": req.metadata},
        )
        await self._responses.save(
            sha256_hash=text_hash,
            issuer_id=req.issuer_id,
            signature_hex=req.signature_hex,
            sig_scheme=req.sig_scheme,
            raw_text=req.raw_text or req.text,
            watermarked_text=req.text,
            metadata=req.metadata,
            bundle_id=bundle.bundle_id,
        )
        return AnchorResponse(
            verified_signer=recovered,
            eth_address=recovered,
            sha256_hash=text_hash,
            chain_receipt=ChainReceiptModel(
                tx_hash="pending",
                block_num=-1,
                data_hash=text_hash,
                issuer_id=req.issuer_id,
                timestamp="pending",
            ),
            proof_bundle_v2=bundle,
            bundle_status="pending_batch",
        )
