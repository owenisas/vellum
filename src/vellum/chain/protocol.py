"""Chain backend Protocol — typed contract for SimulatedChain and SolanaChain."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ChainReceipt:
    """Returned from `anchor()` — minimum information to identify the entry."""

    tx_hash: str
    block_num: int
    data_hash: str
    issuer_id: int
    timestamp: str
    solana_tx_signature: str | None = None

    def to_dict(self) -> dict:
        return {
            "tx_hash": self.tx_hash,
            "block_num": self.block_num,
            "data_hash": self.data_hash,
            "issuer_id": self.issuer_id,
            "timestamp": self.timestamp,
            "solana_tx_signature": self.solana_tx_signature,
        }


@dataclass(frozen=True)
class ChainRecord:
    """Full chain record returned by `lookup`."""

    block_num: int
    prev_hash: str
    tx_hash: str
    data_hash: str
    issuer_id: int
    signature_hex: str
    timestamp: str
    solana_tx_signature: str | None = None
    payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "block_num": self.block_num,
            "prev_hash": self.prev_hash,
            "tx_hash": self.tx_hash,
            "data_hash": self.data_hash,
            "issuer_id": self.issuer_id,
            "signature_hex": self.signature_hex,
            "timestamp": self.timestamp,
            "solana_tx_signature": self.solana_tx_signature,
            "payload": self.payload,
        }


@runtime_checkable
class ChainBackend(Protocol):
    """Async chain backend contract."""

    backend_name: str

    async def initialize(self) -> None:
        """Set up tables, RPC clients, etc. Idempotent."""

    async def anchor(
        self,
        data_hash: str,
        issuer_id: int,
        signature_hex: str,
        metadata: dict | None = None,
    ) -> ChainReceipt: ...

    async def lookup(self, data_hash: str) -> ChainRecord | None: ...

    async def lookup_tx(self, tx_hash: str) -> ChainRecord | None: ...

    async def verify(self, data_hash: str, tx_hash: str) -> bool: ...

    async def chain_length(self) -> int: ...

    async def validate_chain(self) -> tuple[bool, str]: ...
