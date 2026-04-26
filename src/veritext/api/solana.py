from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request


router = APIRouter(prefix="/api/solana", tags=["solana"])


@router.get("/verify")
async def verify(request: Request, signature: str) -> dict:
    chain = request.app.state.chain
    if chain.backend_type != "solana":
        raise HTTPException(status_code=400, detail="Solana not enabled")
    return await chain.rpc_verify(signature)


@router.get("/balance")
async def balance(request: Request) -> dict:
    chain = request.app.state.chain
    if chain.backend_type != "solana":
        raise HTTPException(status_code=400, detail="Solana not enabled")
    return await chain.rpc_balance()


@router.get("/batch/{merkle_root}")
async def batch_leaves(request: Request, merkle_root: str) -> dict:
    chain_repo = request.app.state.chain_repo
    blocks = []
    for b in await chain_repo.list_blocks(limit=1000, offset=0):
        if b.get("merkle_root") == merkle_root:
            blocks.append(
                {
                    "data_hash": b["data_hash"],
                    "issuer_id": b["issuer_id"],
                    "leaf_index": b.get("leaf_index"),
                }
            )
    if not blocks:
        raise HTTPException(status_code=404, detail="merkle root not found")
    return {"merkle_root": merkle_root, "leaves": blocks}
