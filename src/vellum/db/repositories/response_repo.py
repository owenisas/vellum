"""Response repository — stores LLM outputs (raw + watermarked)."""

from __future__ import annotations

import json

from ..connection import get_db


def _row_to_dict(row) -> dict | None:
    if row is None:
        return None
    d = dict(row)
    try:
        d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
    except (TypeError, ValueError):
        d["metadata"] = {}
    return d


class ResponseRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def save(
        self,
        sha256_hash: str,
        issuer_id: int,
        signature_hex: str,
        raw_text: str,
        watermarked_text: str,
        metadata: dict | None = None,
    ) -> int:
        async with get_db(self.db_path) as db:
            cur = await db.execute(
                """
                INSERT INTO responses
                  (sha256_hash, issuer_id, signature_hex, raw_text, watermarked_text, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    sha256_hash,
                    issuer_id,
                    signature_hex,
                    raw_text,
                    watermarked_text,
                    json.dumps(metadata or {}),
                ),
            )
            return int(cur.lastrowid or 0)

    async def get_by_hash(self, sha256_hash: str) -> dict | None:
        async with get_db(self.db_path) as db:
            cur = await db.execute(
                "SELECT * FROM responses WHERE sha256_hash = ? ORDER BY id DESC LIMIT 1",
                (sha256_hash,),
            )
            row = await cur.fetchone()
            return _row_to_dict(row)

    async def list_recent(self, limit: int = 50, offset: int = 0) -> list[dict]:
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        async with get_db(self.db_path) as db:
            cur = await db.execute(
                "SELECT * FROM responses ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            rows = await cur.fetchall()
            return [_row_to_dict(r) or {} for r in rows]

    async def latest(self) -> dict | None:
        async with get_db(self.db_path) as db:
            cur = await db.execute("SELECT * FROM responses ORDER BY id DESC LIMIT 1")
            row = await cur.fetchone()
            return _row_to_dict(row)

    async def delete_all(self) -> int:
        async with get_db(self.db_path) as db:
            cur = await db.execute("DELETE FROM responses")
            return cur.rowcount or 0
