"""SimulatedChain — local SHA-256 hash chain over SQLite."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from veritext.db.repositories import ChainRepo

from .protocol import ChainReceipt, ChainRecord, InclusionProofStep


GENESIS_PREV_HASH = "0" * 64


class SimulatedChain:
    backend_type = "simulated"

    def __init__(self, db_conn: aiosqlite.Connection) -> None:
        self._repo = ChainRepo(db_conn)

    async def anchor(
        self,
        *,
        data_hash: str,
        issuer_id: int,
        signature_hex: str,
        metadata: dict[str, Any] | None = None,
        batch_hint: dict[str, Any] | None = None,  # ignored by simulated chain
    ) -> ChainReceipt:
        latest = await self._repo.latest_block()
        prev_hash = latest["tx_hash"] if latest else GENESIS_PREV_HASH
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        tx_hash = _compute_tx_hash(prev_hash, data_hash, issuer_id, timestamp)

        block_num = await self._repo.append(
            prev_hash=prev_hash,
            tx_hash=tx_hash,
            data_hash=data_hash,
            issuer_id=issuer_id,
            signature_hex=signature_hex,
            payload=metadata or {},
            timestamp=timestamp,
        )
        return ChainReceipt(
            tx_hash=tx_hash,
            block_num=block_num,
            data_hash=data_hash,
            issuer_id=issuer_id,
            timestamp=timestamp,
        )

    async def latest(self) -> ChainRecord | None:
        row = await self._repo.latest_block()
        return _row_to_record(row) if row else None

    async def list_blocks(self, *, limit: int = 50, offset: int = 0) -> list[ChainRecord]:
        rows = await self._repo.list_blocks(limit=limit, offset=offset)
        return [_row_to_record(r) for r in rows]

    async def get_by_data_hash(self, data_hash: str) -> ChainRecord | None:
        row = await self._repo.get_by_data_hash(data_hash)
        return _row_to_record(row) if row else None

    async def count(self) -> int:
        return await self._repo.count()


def _compute_tx_hash(prev_hash: str, data_hash: str, issuer_id: int, timestamp: str) -> str:
    h = hashlib.sha256()
    h.update(prev_hash.encode())
    h.update(data_hash.encode())
    h.update(str(issuer_id).encode())
    h.update(timestamp.encode())
    return h.hexdigest()


def _row_to_record(row: dict[str, Any]) -> ChainRecord:
    return ChainRecord(
        block_num=row["block_num"],
        prev_hash=row["prev_hash"],
        tx_hash=row["tx_hash"],
        data_hash=row["data_hash"],
        issuer_id=row["issuer_id"],
        signature_hex=row["signature_hex"],
        timestamp=row["timestamp"],
        solana_tx_signature=row.get("solana_tx_signature"),
    )
