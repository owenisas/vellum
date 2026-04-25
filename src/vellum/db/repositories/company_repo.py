"""Company repository — async CRUD over companies table."""

from __future__ import annotations

from ..connection import get_db


def _row_to_dict(row) -> dict | None:
    if row is None:
        return None
    d = dict(row)
    d["active"] = bool(d.get("active", 1))
    return d


class CompanyRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def create(
        self,
        name: str,
        issuer_id: int,
        eth_address: str,
        public_key_hex: str,
    ) -> dict:
        async with get_db(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO companies (name, issuer_id, eth_address, public_key_hex, active)
                VALUES (?, ?, ?, ?, 1)
                """,
                (name, issuer_id, eth_address, public_key_hex.removeprefix("0x")),
            )
            cursor = await db.execute(
                "SELECT * FROM companies WHERE issuer_id = ?", (issuer_id,)
            )
            row = await cursor.fetchone()
            return _row_to_dict(row) or {}

    async def get_by_issuer(self, issuer_id: int) -> dict | None:
        async with get_db(self.db_path) as db:
            cur = await db.execute("SELECT * FROM companies WHERE issuer_id = ?", (issuer_id,))
            row = await cur.fetchone()
            return _row_to_dict(row)

    async def get_by_address(self, eth_address: str) -> dict | None:
        async with get_db(self.db_path) as db:
            cur = await db.execute(
                "SELECT * FROM companies WHERE LOWER(eth_address) = ?",
                (eth_address.lower(),),
            )
            row = await cur.fetchone()
            return _row_to_dict(row)

    async def list_all(self) -> list[dict]:
        async with get_db(self.db_path) as db:
            cur = await db.execute("SELECT * FROM companies ORDER BY id ASC")
            rows = await cur.fetchall()
            return [_row_to_dict(r) or {} for r in rows]

    async def deactivate(self, issuer_id: int) -> None:
        async with get_db(self.db_path) as db:
            await db.execute(
                "UPDATE companies SET active = 0 WHERE issuer_id = ?",
                (issuer_id,),
            )

    async def next_issuer_id(self) -> int:
        async with get_db(self.db_path) as db:
            cur = await db.execute(
                "SELECT COALESCE(MAX(issuer_id), 0) + 1 AS next_id FROM companies"
            )
            row = await cur.fetchone()
            return int(row["next_id"]) if row else 1

    async def delete_all(self) -> int:
        async with get_db(self.db_path) as db:
            cur = await db.execute("DELETE FROM companies")
            return cur.rowcount or 0
