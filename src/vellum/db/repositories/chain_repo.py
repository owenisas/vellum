"""Chain block repository — read access to the simulated/Solana chain table."""

from __future__ import annotations

import json

from ..connection import get_db


def _row_to_dict(row) -> dict | None:
    if row is None:
        return None
    d = dict(row)
    try:
        d["payload"] = json.loads(d.pop("payload_json", "{}") or "{}")
    except (TypeError, ValueError):
        d["payload"] = {}
    return d


class ChainBlockRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def get_by_tx_hash(self, tx_hash: str) -> dict | None:
        async with get_db(self.db_path) as db:
            cur = await db.execute(
                "SELECT * FROM chain_blocks WHERE tx_hash = ?", (tx_hash,)
            )
            row = await cur.fetchone()
            return _row_to_dict(row)

    async def get_by_data_hash(self, data_hash: str) -> dict | None:
        async with get_db(self.db_path) as db:
            cur = await db.execute(
                "SELECT * FROM chain_blocks WHERE data_hash = ? ORDER BY block_num ASC LIMIT 1",
                (data_hash,),
            )
            row = await cur.fetchone()
            return _row_to_dict(row)

    async def get_by_solana_tx(self, signature: str) -> dict | None:
        async with get_db(self.db_path) as db:
            cur = await db.execute(
                "SELECT * FROM chain_blocks WHERE solana_tx_signature = ?",
                (signature,),
            )
            row = await cur.fetchone()
            return _row_to_dict(row)

    async def list_blocks(self, limit: int = 50, offset: int = 0) -> list[dict]:
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        async with get_db(self.db_path) as db:
            cur = await db.execute(
                "SELECT * FROM chain_blocks ORDER BY block_num DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            rows = await cur.fetchall()
            return [_row_to_dict(r) or {} for r in rows]

    async def get_block(self, block_num: int) -> dict | None:
        async with get_db(self.db_path) as db:
            cur = await db.execute(
                "SELECT * FROM chain_blocks WHERE block_num = ?", (block_num,)
            )
            row = await cur.fetchone()
            return _row_to_dict(row)

    async def latest(self) -> dict | None:
        async with get_db(self.db_path) as db:
            cur = await db.execute(
                "SELECT * FROM chain_blocks ORDER BY block_num DESC LIMIT 1"
            )
            row = await cur.fetchone()
            return _row_to_dict(row)

    async def count(self) -> int:
        async with get_db(self.db_path) as db:
            cur = await db.execute("SELECT COUNT(*) AS c FROM chain_blocks")
            row = await cur.fetchone()
            return int(row["c"]) if row else 0

    async def delete_all(self) -> int:
        async with get_db(self.db_path) as db:
            cur = await db.execute("DELETE FROM chain_blocks")
            return cur.rowcount or 0
