from __future__ import annotations

from pydantic import BaseModel


class ChainBlockModel(BaseModel):
    block_num: int
    prev_hash: str
    tx_hash: str
    data_hash: str
    issuer_id: int
    signature_hex: str
    timestamp: str
    solana_tx_signature: str | None = None


class ChainStatusResponse(BaseModel):
    chain_type: str  # "simulated" | "solana"
    anchor_strategy: str  # "per_response" | "merkle_batch"
    block_count: int
    latest_block_num: int | None = None
    latest_tx_hash: str | None = None
    pending_batch_size: int = 0
