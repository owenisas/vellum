"""Repositories — thin async wrappers over SQL."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import aiosqlite


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class CompanyRepo:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def create(
        self,
        *,
        name: str,
        issuer_id: int,
        eth_address: str,
        public_key_hex: str,
    ) -> int:
        now = _now_iso()
        cur = await self._conn.execute(
            "INSERT INTO companies (name, issuer_id, current_key_id, eth_address, public_key_hex, active, created_at) "
            "VALUES (?, ?, 1, ?, ?, 1, ?)",
            (name, issuer_id, eth_address, public_key_hex, now),
        )
        cid = cur.lastrowid
        await self._conn.execute(
            "INSERT INTO company_keys (issuer_id, key_id, eth_address, public_key_hex, active_from, active, active_until) "
            "VALUES (?, 1, ?, ?, ?, 1, NULL)",
            (issuer_id, eth_address, public_key_hex, now),
        )
        await self._conn.commit()
        return int(cid)

    async def get_by_issuer(self, issuer_id: int) -> dict[str, Any] | None:
        cur = await self._conn.execute(
            "SELECT * FROM companies WHERE issuer_id = ? AND active = 1",
            (issuer_id,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def list_all(self) -> list[dict[str, Any]]:
        cur = await self._conn.execute("SELECT * FROM companies ORDER BY id ASC")
        return [dict(r) for r in await cur.fetchall()]

    async def get_by_address(self, eth_address: str) -> dict[str, Any] | None:
        cur = await self._conn.execute(
            "SELECT * FROM companies WHERE LOWER(eth_address) = LOWER(?) AND active = 1",
            (eth_address,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None


class KeyRotationRepo:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def list_for_issuer(self, issuer_id: int) -> list[dict[str, Any]]:
        cur = await self._conn.execute(
            "SELECT * FROM company_keys WHERE issuer_id = ? ORDER BY key_id ASC",
            (issuer_id,),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def rotate(
        self,
        *,
        issuer_id: int,
        new_eth_address: str,
        new_public_key_hex: str,
        grace_period_days: int,
    ) -> tuple[int, int, str]:
        keys = await self.list_for_issuer(issuer_id)
        if not keys:
            raise ValueError(f"no existing keys for issuer {issuer_id}")
        old_key_id = max(k["key_id"] for k in keys if k["active"])
        new_key_id = max(k["key_id"] for k in keys) + 1
        now = datetime.now(timezone.utc)
        grace_until = (now + timedelta(days=grace_period_days)).isoformat(timespec="seconds")
        # Set active_until on old, but keep active flag on for grace period
        await self._conn.execute(
            "UPDATE company_keys SET active_until = ? WHERE issuer_id = ? AND key_id = ?",
            (grace_until, issuer_id, old_key_id),
        )
        # Insert new key
        await self._conn.execute(
            "INSERT INTO company_keys (issuer_id, key_id, eth_address, public_key_hex, active_from, active, active_until) "
            "VALUES (?, ?, ?, ?, ?, 1, NULL)",
            (issuer_id, new_key_id, new_eth_address, new_public_key_hex, now.isoformat(timespec="seconds")),
        )
        # Update companies.current_key_id
        await self._conn.execute(
            "UPDATE companies SET current_key_id = ?, eth_address = ?, public_key_hex = ? WHERE issuer_id = ?",
            (new_key_id, new_eth_address, new_public_key_hex, issuer_id),
        )
        await self._conn.commit()
        return old_key_id, new_key_id, grace_until

    async def find_active_key_at(self, issuer_id: int, at_iso: str) -> dict[str, Any] | None:
        """
        Return the key entry that was active for `issuer_id` at the given ISO
        timestamp. Used by anchor verification to honor grace periods.
        """
        cur = await self._conn.execute(
            "SELECT * FROM company_keys WHERE issuer_id = ? AND active_from <= ? "
            "AND (active_until IS NULL OR active_until >= ?) "
            "ORDER BY key_id DESC LIMIT 1",
            (issuer_id, at_iso, at_iso),
        )
        row = await cur.fetchone()
        return dict(row) if row else None


class ResponseRepo:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def save(
        self,
        *,
        sha256_hash: str,
        issuer_id: int,
        signature_hex: str,
        sig_scheme: str,
        raw_text: str,
        watermarked_text: str,
        metadata: dict[str, Any],
        bundle_id: str,
    ) -> int:
        cur = await self._conn.execute(
            "INSERT INTO responses (sha256_hash, issuer_id, signature_hex, sig_scheme, raw_text, "
            "watermarked_text, metadata_json, bundle_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                sha256_hash,
                issuer_id,
                signature_hex,
                sig_scheme,
                raw_text,
                watermarked_text,
                json.dumps(metadata),
                bundle_id,
            ),
        )
        await self._conn.commit()
        return int(cur.lastrowid)

    async def get_by_hash(self, sha256_hash: str) -> dict[str, Any] | None:
        cur = await self._conn.execute(
            "SELECT * FROM responses WHERE sha256_hash = ? ORDER BY id DESC LIMIT 1",
            (sha256_hash,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def get_by_bundle_id(self, bundle_id: str) -> dict[str, Any] | None:
        cur = await self._conn.execute(
            "SELECT * FROM responses WHERE bundle_id = ?", (bundle_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


class ChainRepo:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def latest_block(self) -> dict[str, Any] | None:
        cur = await self._conn.execute(
            "SELECT * FROM chain_blocks ORDER BY block_num DESC LIMIT 1"
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def append(
        self,
        *,
        prev_hash: str,
        tx_hash: str,
        data_hash: str,
        issuer_id: int,
        signature_hex: str,
        payload: dict[str, Any],
        timestamp: str,
        solana_tx_signature: str | None = None,
        merkle_root: str | None = None,
        leaf_index: int | None = None,
        inclusion_proof: list[dict[str, str]] | None = None,
    ) -> int:
        latest = await self.latest_block()
        block_num = (latest["block_num"] + 1) if latest else 0
        await self._conn.execute(
            "INSERT INTO chain_blocks (block_num, prev_hash, tx_hash, data_hash, issuer_id, "
            "signature_hex, payload_json, timestamp, solana_tx_signature, merkle_root, leaf_index, "
            "inclusion_proof_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                block_num,
                prev_hash,
                tx_hash,
                data_hash,
                issuer_id,
                signature_hex,
                json.dumps(payload),
                timestamp,
                solana_tx_signature,
                merkle_root,
                leaf_index,
                json.dumps(inclusion_proof or []),
            ),
        )
        await self._conn.commit()
        return block_num

    async def list_blocks(self, *, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        cur = await self._conn.execute(
            "SELECT * FROM chain_blocks ORDER BY block_num DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def get_by_data_hash(self, data_hash: str) -> dict[str, Any] | None:
        cur = await self._conn.execute(
            "SELECT * FROM chain_blocks WHERE data_hash = ? ORDER BY block_num DESC LIMIT 1",
            (data_hash,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def count(self) -> int:
        cur = await self._conn.execute("SELECT COUNT(*) FROM chain_blocks")
        row = await cur.fetchone()
        return int(row[0]) if row else 0


class PendingAnchorRepo:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def enqueue(self, *, bundle_id: str, data_hash: str, issuer_id: int, signature_hex: str, payload: dict[str, Any]) -> None:
        await self._conn.execute(
            "INSERT OR IGNORE INTO pending_anchors (bundle_id, data_hash, issuer_id, signature_hex, payload_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (bundle_id, data_hash, issuer_id, signature_hex, json.dumps(payload)),
        )
        await self._conn.commit()

    async def list_unpromoted(self, *, limit: int = 64) -> list[dict[str, Any]]:
        cur = await self._conn.execute(
            "SELECT * FROM pending_anchors WHERE promoted = 0 ORDER BY id ASC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def mark_promoted(self, ids: list[int]) -> None:
        if not ids:
            return
        q_marks = ",".join("?" * len(ids))
        await self._conn.execute(
            f"UPDATE pending_anchors SET promoted = 1 WHERE id IN ({q_marks})", ids
        )
        await self._conn.commit()

    async def count(self) -> int:
        cur = await self._conn.execute("SELECT COUNT(*) FROM pending_anchors WHERE promoted = 0")
        row = await cur.fetchone()
        return int(row[0]) if row else 0
