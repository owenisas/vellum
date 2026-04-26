from __future__ import annotations

import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from veritext.auth.jwt import AuthClaims
from veritext.models.registry import (
    AnchorRequest,
    AnchorResponse,
    ProofResponse,
    VerifyRequest,
    VerifyResponse,
)
from veritext.services.anchor_service import AnchorError
from .deps import require_scopes


router = APIRouter(prefix="/api", tags=["registry"])


@router.post("/anchor", response_model=AnchorResponse)
async def anchor(
    request: Request,
    body: AnchorRequest,
    _claims: Annotated[AuthClaims, Depends(require_scopes("anchor:create"))],
) -> AnchorResponse:
    service = request.app.state.anchor_service
    try:
        return await service.anchor(body)
    except AnchorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/verify", response_model=VerifyResponse)
async def verify(request: Request, body: VerifyRequest) -> VerifyResponse:
    chain = request.app.state.chain
    company_repo = request.app.state.company_repo
    response_repo = request.app.state.response_repo
    wm_service = request.app.state.watermark_service

    text_hash = hashlib.sha256(body.text.encode("utf-8")).hexdigest()
    record = await response_repo.get_by_hash(text_hash)
    chain_block = await chain.get_by_data_hash(text_hash)
    wm = wm_service.detect(body.text)
    wm_dict = {
        "present": wm.present,
        "unicode": wm.unicode,
        "statistical": wm.statistical,
    }
    if not record or not chain_block:
        return VerifyResponse(
            verified=False,
            sha256_hash=text_hash,
            watermark=wm_dict,
            reason="not found in registry",
        )
    company = await company_repo.get_by_issuer(record["issuer_id"])
    return VerifyResponse(
        verified=True,
        sha256_hash=text_hash,
        issuer_id=record["issuer_id"],
        company=company["name"] if company else None,
        eth_address=company["eth_address"] if company else None,
        block_num=chain_block.block_num,
        tx_hash=chain_block.tx_hash,
        timestamp=chain_block.timestamp,
        watermark=wm_dict,
    )


@router.get("/proof/{bundle_id}", response_model=ProofResponse)
async def get_proof(request: Request, bundle_id: str) -> ProofResponse:
    response_repo = request.app.state.response_repo
    chain_repo = request.app.state.chain_repo
    proof_builder = request.app.state.proof_builder
    company_repo = request.app.state.company_repo
    wm_service = request.app.state.watermark_service

    record = await response_repo.get_by_bundle_id(bundle_id)
    if not record:
        raise HTTPException(status_code=404, detail="bundle not found")

    company = await company_repo.get_by_issuer(record["issuer_id"])
    block = await chain_repo.get_by_data_hash(record["sha256_hash"])
    wm_detect = wm_service.detect(record["watermarked_text"])

    receipt = None
    pending_batch = block is None
    if block is not None:
        from veritext.chain.protocol import ChainReceipt, InclusionProofStep
        import json

        ip = json.loads(block.get("inclusion_proof_json") or "[]")
        receipt = ChainReceipt(
            tx_hash=block["tx_hash"],
            block_num=block["block_num"],
            data_hash=block["data_hash"],
            issuer_id=block["issuer_id"],
            timestamp=block["timestamp"],
            solana_tx_signature=block.get("solana_tx_signature"),
            merkle_root=block.get("merkle_root"),
            leaf_index=block.get("leaf_index"),
            inclusion_proof=[InclusionProofStep(**s) for s in ip],
        )

    chain_backend_type = request.app.state.settings.chain_backend.value
    bundle = await proof_builder.build(
        text_hash=record["sha256_hash"],
        company=company,
        wm_detect=wm_detect,
        chain_receipt=receipt,
        chain_backend_type=chain_backend_type,
        sig_scheme=record["sig_scheme"],
        signature_hex=record["signature_hex"],
        timestamp=None,
        bundle_nonce_hex=None,
        pending_batch=pending_batch,
    )
    return ProofResponse(
        proof_bundle_v2=bundle,
        bundle_status="pending_batch" if pending_batch else "ok",
    )
