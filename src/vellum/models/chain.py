"""Chain-related response shapes."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChainReceiptModel(BaseModel):
    tx_hash: str
    block_num: int
    data_hash: str
    issuer_id: int
    timestamp: str
    solana_tx_signature: str | None = None


class ChainRecordModel(BaseModel):
    block_num: int
    prev_hash: str
    tx_hash: str
    data_hash: str
    issuer_id: int
    signature_hex: str
    timestamp: str
    solana_tx_signature: str | None = None


class ChainBlock(BaseModel):
    block_num: int
    prev_hash: str
    tx_hash: str
    data_hash: str
    issuer_id: int
    signature_hex: str
    timestamp: str
    solana_tx_signature: str | None = None


class ChainStatusResponse(BaseModel):
    length: int = 0
    valid: bool = True
    message: str = ""
    backend: str = "simulated"
    latest_block_num: int | None = None
    latest_data_hash: str | None = None
    extra: dict = Field(default_factory=dict)
