"""Chain status / blocks endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from vellum.models.chain import ChainBlock, ChainStatusResponse

from .deps import get_anchor_service, get_chain_repo

router = APIRouter(prefix="/api/chain", tags=["chain"])


@router.get("/status", response_model=ChainStatusResponse)
async def status_endpoint(svc=Depends(get_anchor_service)) -> ChainStatusResponse:
    s = await svc.chain_status()
    return ChainStatusResponse(**s)


@router.get("/blocks", response_model=list[ChainBlock])
async def list_blocks(
    limit: int = 50,
    offset: int = 0,
    repo=Depends(get_chain_repo),
) -> list[ChainBlock]:
    rows = await repo.list_blocks(limit=limit, offset=offset)
    return [_row_to_block(r) for r in rows]


@router.get("/blocks/{block_num}", response_model=ChainBlock)
async def get_block(block_num: int, repo=Depends(get_chain_repo)) -> ChainBlock:
    row = await repo.get_block(block_num)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")
    return _row_to_block(row)


def _row_to_block(row: dict) -> ChainBlock:
    return ChainBlock(
        block_num=int(row["block_num"]),
        prev_hash=row["prev_hash"],
        tx_hash=row["tx_hash"],
        data_hash=row["data_hash"],
        issuer_id=int(row["issuer_id"]),
        signature_hex=row["signature_hex"],
        timestamp=row["timestamp"],
        solana_tx_signature=row.get("solana_tx_signature"),
    )
