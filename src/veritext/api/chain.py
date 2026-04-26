from __future__ import annotations

from fastapi import APIRouter, Request

from veritext.models.chain import ChainBlockModel, ChainStatusResponse


router = APIRouter(prefix="/api/chain", tags=["chain"])


@router.get("/status", response_model=ChainStatusResponse)
async def status(request: Request) -> ChainStatusResponse:
    chain = request.app.state.chain
    settings = request.app.state.settings
    pending_repo = request.app.state.pending_repo
    latest = await chain.latest()
    return ChainStatusResponse(
        chain_type=settings.chain_backend.value,
        anchor_strategy=settings.anchor_strategy.value,
        block_count=await chain.count(),
        latest_block_num=latest.block_num if latest else None,
        latest_tx_hash=latest.tx_hash if latest else None,
        pending_batch_size=await pending_repo.count(),
    )


@router.get("/blocks", response_model=list[ChainBlockModel])
async def blocks(request: Request, limit: int = 50, offset: int = 0) -> list[ChainBlockModel]:
    chain = request.app.state.chain
    out = []
    for b in await chain.list_blocks(limit=limit, offset=offset):
        out.append(
            ChainBlockModel(
                block_num=b.block_num,
                prev_hash=b.prev_hash,
                tx_hash=b.tx_hash,
                data_hash=b.data_hash,
                issuer_id=b.issuer_id,
                signature_hex=b.signature_hex,
                timestamp=b.timestamp,
                solana_tx_signature=b.solana_tx_signature,
            )
        )
    return out
