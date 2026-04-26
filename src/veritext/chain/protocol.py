"""Chain backend Protocol + shared dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class InclusionProofStep:
    hash: str
    side: str  # "L" or "R"


@dataclass
class ChainReceipt:
    tx_hash: str
    block_num: int
    data_hash: str
    issuer_id: int
    timestamp: str
    solana_tx_signature: str | None = None
    merkle_root: str | None = None
    leaf_index: int | None = None
    inclusion_proof: list[InclusionProofStep] = field(default_factory=list)
    pending: bool = False  # True when awaiting Merkle batch close


@dataclass
class ChainRecord:
    block_num: int
    prev_hash: str
    tx_hash: str
    data_hash: str
    issuer_id: int
    signature_hex: str
    timestamp: str
    solana_tx_signature: str | None = None


class ChainBackend(Protocol):
    backend_type: str

    async def anchor(
        self,
        *,
        data_hash: str,
        issuer_id: int,
        signature_hex: str,
        metadata: dict[str, Any] | None = None,
        batch_hint: dict[str, Any] | None = None,
    ) -> ChainReceipt: ...

    async def latest(self) -> ChainRecord | None: ...

    async def list_blocks(self, *, limit: int, offset: int) -> list[ChainRecord]: ...

    async def get_by_data_hash(self, data_hash: str) -> ChainRecord | None: ...

    async def count(self) -> int: ...
