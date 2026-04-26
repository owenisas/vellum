"""Simulated hash-chain backed by aiosqlite."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from vellum.db.connection import get_db, init_db

from .protocol import ChainBackend, ChainReceipt, ChainRecord

GENESIS_PREV_HASH = "0" * 64


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _compute_tx_hash(prev_hash: str, data_hash: str, issuer_id: int, timestamp: str) -> str:
    h = hashlib.sha256()
    h.update(prev_hash.encode())
    h.update(b"|")
    h.update(data_hash.encode())
    h.update(b"|")
    h.update(str(issuer_id).encode())
    h.update(b"|")
    h.update(timestamp.encode())
    return h.hexdigest()


class SimulatedChain(ChainBackend):
    """In-DB SHA-256 linked list. No external RPC."""

    backend_name = "simulated"

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def initialize(self) -> None:
        await init_db(self.db_path)

    async def _latest_tx_hash(self) -> str:
        async with get_db(self.db_path) as db:
            cur = await db.execute(
                "SELECT tx_hash FROM chain_blocks ORDER BY block_num DESC LIMIT 1"
            )
            row = await cur.fetchone()
            return row["tx_hash"] if row else GENESIS_PREV_HASH

    async def anchor(
        self,
        data_hash: str,
        issuer_id: int,
        signature_hex: str,
        metadata: dict | None = None,
    ) -> ChainReceipt:
        await self.initialize()
        prev_hash = await self._latest_tx_hash()
        timestamp = _utcnow()
        tx_hash = _compute_tx_hash(prev_hash, data_hash, issuer_id, timestamp)

        async with get_db(self.db_path) as db:
            cur = await db.execute(
                """
                INSERT INTO chain_blocks
                  (prev_hash, tx_hash, data_hash, issuer_id, signature_hex, payload_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prev_hash,
                    tx_hash,
                    data_hash,
                    issuer_id,
                    signature_hex,
                    json.dumps(metadata or {}),
                    timestamp,
                ),
            )
            block_num = int(cur.lastrowid or 0)

        return ChainReceipt(
            tx_hash=tx_hash,
            block_num=block_num,
            data_hash=data_hash,
            issuer_id=issuer_id,
            timestamp=timestamp,
        )

    async def lookup(self, data_hash: str) -> ChainRecord | None:
        async with get_db(self.db_path) as db:
            cur = await db.execute(
                "SELECT * FROM chain_blocks WHERE data_hash = ? ORDER BY block_num ASC LIMIT 1",
                (data_hash,),
            )
            row = await cur.fetchone()
            return _row_to_record(row)

    async def lookup_tx(self, tx_hash: str) -> ChainRecord | None:
        async with get_db(self.db_path) as db:
            cur = await db.execute(
                "SELECT * FROM chain_blocks WHERE tx_hash = ?", (tx_hash,)
            )
            row = await cur.fetchone()
            return _row_to_record(row)

    async def verify(self, data_hash: str, tx_hash: str) -> bool:
        rec = await self.lookup_tx(tx_hash)
        if rec is None:
            return False
        return rec.data_hash == data_hash

    async def chain_length(self) -> int:
        async with get_db(self.db_path) as db:
            cur = await db.execute("SELECT COUNT(*) AS c FROM chain_blocks")
            row = await cur.fetchone()
            return int(row["c"]) if row else 0

    async def validate_chain(self) -> tuple[bool, str]:
        async with get_db(self.db_path) as db:
            cur = await db.execute(
                "SELECT * FROM chain_blocks ORDER BY block_num ASC"
            )
            rows = await cur.fetchall()

        if not rows:
            return True, "Chain is empty"

        prev_hash = GENESIS_PREV_HASH
        for row in rows:
            expected_tx = _compute_tx_hash(
                prev_hash,
                row["data_hash"],
                int(row["issuer_id"]),
                row["timestamp"],
            )
            if row["prev_hash"] != prev_hash:
                return False, f"Block {row['block_num']}: prev_hash mismatch"
            if row["tx_hash"] != expected_tx:
                return False, f"Block {row['block_num']}: tx_hash mismatch"
            prev_hash = row["tx_hash"]

        return True, f"Chain valid ({len(rows)} blocks)"


def _row_to_record(row) -> ChainRecord | None:
    if row is None:
        return None
    try:
        payload = json.loads(row["payload_json"] or "{}")
    except (TypeError, ValueError):
        payload = {}
    return ChainRecord(
        block_num=int(row["block_num"]),
        prev_hash=row["prev_hash"],
        tx_hash=row["tx_hash"],
        data_hash=row["data_hash"],
        issuer_id=int(row["issuer_id"]),
        signature_hex=row["signature_hex"],
        timestamp=row["timestamp"],
        solana_tx_signature=row["solana_tx_signature"],
        payload=payload,
    )
