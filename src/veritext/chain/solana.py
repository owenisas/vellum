"""
Solana chain backend — Memo program transactions on devnet, with both
per-response and Merkle-batched modes (the latter via MerkleBatchService).

Uses Borsh-encoded memos (improvement #13). Falls back to dual-write to
SQLite if Solana RPC fails, per spec §11.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any

import structlog

from veritext.config import AppSettings
from veritext.db.repositories import ChainRepo

from .borsh_schema import MemoV2, encode_memo
from .protocol import ChainReceipt, ChainRecord, InclusionProofStep


log = structlog.get_logger("veritext.solana")

SPL_MEMO_PROGRAM_ID = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"


class SolanaChain:
    backend_type = "solana"

    def __init__(self, *, settings: AppSettings, db_conn) -> None:
        self._settings = settings
        self._repo = ChainRepo(db_conn)
        self._keypair = None  # lazy

    async def _ensure_keypair(self):
        if self._keypair is not None:
            return self._keypair
        path = self._settings.solana.solana_keypair_path
        if not path:
            raise RuntimeError("SOLANA_KEYPAIR_PATH not set")
        try:
            from solders.keypair import Keypair  # type: ignore
        except ImportError as exc:
            raise RuntimeError("solana extras not installed (`pip install veritext[solana]`)") from exc
        with open(path) as f:
            data = json.load(f)
        self._keypair = Keypair.from_bytes(bytes(data))
        return self._keypair

    async def anchor(
        self,
        *,
        data_hash: str,
        issuer_id: int,
        signature_hex: str,
        metadata: dict[str, Any] | None = None,
        batch_hint: dict[str, Any] | None = None,
    ) -> ChainReceipt:
        timestamp_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
        timestamp_unix = int(time.time())
        merkle_root = (batch_hint or {}).get("merkle_root")

        memo = MemoV2(
            data_hash=bytes.fromhex(data_hash),
            issuer_id=issuer_id,
            sig_prefix=_sig_prefix_20(signature_hex),
            timestamp_unix=timestamp_unix,
            merkle_root=bytes.fromhex(merkle_root) if merkle_root else None,
        )
        memo_bytes = encode_memo(memo)

        solana_sig: str | None = None
        try:
            solana_sig = await self._post_memo(memo_bytes)
        except Exception as exc:  # graceful fallback per spec §11
            log.warning("solana_anchor_failed", error=str(exc), data_hash=data_hash[:16])

        latest = await self._repo.latest_block()
        prev_hash = latest["tx_hash"] if latest else "0" * 64
        h = hashlib.sha256()
        h.update(prev_hash.encode())
        h.update(data_hash.encode())
        h.update(str(issuer_id).encode())
        h.update(timestamp_iso.encode())
        if solana_sig:
            h.update(solana_sig.encode())
        local_tx = h.hexdigest()

        block_num = await self._repo.append(
            prev_hash=prev_hash,
            tx_hash=local_tx,
            data_hash=data_hash,
            issuer_id=issuer_id,
            signature_hex=signature_hex,
            payload={"memo_b64": base64.b64encode(memo_bytes).decode(), **(metadata or {})},
            timestamp=timestamp_iso,
            solana_tx_signature=solana_sig,
            merkle_root=merkle_root,
        )
        return ChainReceipt(
            tx_hash=local_tx,
            block_num=block_num,
            data_hash=data_hash,
            issuer_id=issuer_id,
            timestamp=timestamp_iso,
            solana_tx_signature=solana_sig,
            merkle_root=merkle_root,
        )

    async def _post_memo(self, memo_bytes: bytes) -> str:
        """
        Build and send a Solana transaction containing only a Memo program
        instruction with `memo_bytes` as data. Returns the transaction signature.
        """
        try:
            from solana.rpc.async_api import AsyncClient  # type: ignore
            from solders.message import Message  # type: ignore
            from solders.instruction import Instruction, AccountMeta  # type: ignore
            from solders.pubkey import Pubkey  # type: ignore
            from solders.transaction import Transaction  # type: ignore
        except ImportError as exc:
            raise RuntimeError("solana extras not installed") from exc

        kp = await self._ensure_keypair()
        memo_program = Pubkey.from_string(SPL_MEMO_PROGRAM_ID)
        ix = Instruction(program_id=memo_program, accounts=[], data=memo_bytes)
        async with AsyncClient(self._settings.solana.solana_rpc_url) as client:
            recent = await client.get_latest_blockhash()
            blockhash = recent.value.blockhash
            msg = Message.new_with_blockhash([ix], kp.pubkey(), blockhash)
            tx = Transaction([kp], msg, blockhash)
            resp = await client.send_transaction(tx)
            return str(resp.value)

    async def rpc_verify(self, signature: str) -> dict:
        try:
            from solana.rpc.async_api import AsyncClient  # type: ignore
        except ImportError:
            return {"verified": False, "reason": "solana extras not installed"}
        async with AsyncClient(self._settings.solana.solana_rpc_url) as client:
            res = await client.get_transaction(signature)
            return {"verified": res.value is not None, "raw": str(res.value)[:500] if res.value else None}

    async def rpc_balance(self) -> dict:
        try:
            from solana.rpc.async_api import AsyncClient  # type: ignore
        except ImportError:
            return {"lamports": 0, "reason": "solana extras not installed"}
        kp = await self._ensure_keypair()
        async with AsyncClient(self._settings.solana.solana_rpc_url) as client:
            res = await client.get_balance(kp.pubkey())
            return {"lamports": res.value}

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


def _sig_prefix_20(sig_hex: str) -> bytes:
    s = sig_hex.removeprefix("0x")
    if not s:
        return bytes(20)
    raw = bytes.fromhex(s)
    return raw[:20].ljust(20, b"\x00")


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
