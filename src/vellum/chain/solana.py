"""Solana chain backend — dual-writes to Solana Memo program and local SQLite."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from vellum.db.connection import get_db, init_db

from .protocol import ChainBackend, ChainReceipt, ChainRecord
from .simulated import _compute_tx_hash, _row_to_record  # reuse hash logic

logger = logging.getLogger(__name__)

MEMO_PROGRAM_ID = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
GENESIS_PREV_HASH = "0" * 64


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _build_memo(data_hash: str, issuer_id: int, signature_hex: str, timestamp: str) -> str:
    return json.dumps(
        {
            "v": 1,
            "h": data_hash,
            "i": issuer_id,
            "s": signature_hex[:42],
            "t": timestamp,
        },
        separators=(",", ":"),
    )


class SolanaChain(ChainBackend):
    """Anchor records to Solana devnet via the Memo program; mirror to SQLite.

    The Solana RPC call is best-effort: if it fails for any reason, the local
    SQLite write still happens (with `solana_tx_signature = NULL`) and a
    warning is logged. This guarantees the API never fails because of a
    network blip on devnet.
    """

    backend_name = "solana"

    def __init__(
        self,
        rpc_url: str,
        keypair_path: str,
        cluster: str = "devnet",
        db_path: str = "data/vellum.db",
    ) -> None:
        self.rpc_url = rpc_url
        self.keypair_path = keypair_path
        self.cluster = cluster
        self.db_path = db_path
        self._client = None
        self._keypair = None
        self._memo_program = None

    async def initialize(self) -> None:
        await init_db(self.db_path)
        try:
            self._lazy_init_client()
        except Exception as exc:  # pragma: no cover — depends on optional deps
            logger.warning("solana client init failed: %s", exc)

    def _lazy_init_client(self) -> None:
        if self._client is not None:
            return
        try:
            from solana.rpc.api import Client  # type: ignore[import-not-found]
            from solders.keypair import Keypair  # type: ignore[import-not-found]
            from solders.pubkey import Pubkey  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            logger.warning("solana optional deps missing: %s", exc)
            return

        self._client = Client(self.rpc_url)
        self._memo_program = Pubkey.from_string(MEMO_PROGRAM_ID)

        if self.keypair_path:
            try:
                with open(self.keypair_path, "rb") as f:
                    raw = json.loads(f.read())
                self._keypair = Keypair.from_bytes(bytes(raw))
            except FileNotFoundError:
                logger.warning("solana keypair file not found: %s", self.keypair_path)
            except Exception as exc:  # pragma: no cover
                logger.warning("solana keypair load failed: %s", exc)

    async def get_balance(self) -> tuple[str, int]:
        """Returns (address, lamports). 0 lamports if RPC unavailable."""
        self._lazy_init_client()
        if not self._client or not self._keypair:
            return "", 0
        try:
            addr = str(self._keypair.pubkey())
            resp = self._client.get_balance(self._keypair.pubkey())
            value = getattr(resp, "value", None)
            return addr, int(value) if value else 0
        except Exception as exc:  # pragma: no cover
            logger.warning("solana get_balance failed: %s", exc)
            return "", 0

    async def _send_memo(self, memo: str) -> str | None:
        """Submit a memo transaction. Returns base58 signature or None on error."""
        self._lazy_init_client()
        if not self._client or not self._keypair or not self._memo_program:
            return None

        try:
            from solana.transaction import Transaction  # type: ignore[import-not-found]
            from solders.instruction import AccountMeta, Instruction  # type: ignore[import-not-found]

            ix = Instruction(
                program_id=self._memo_program,
                accounts=[
                    AccountMeta(pubkey=self._keypair.pubkey(), is_signer=True, is_writable=True),
                ],
                data=memo.encode("utf-8"),
            )
            tx = Transaction()
            tx.add(ix)
            resp = self._client.send_transaction(tx, self._keypair)
            sig = getattr(resp, "value", None)
            return str(sig) if sig else None
        except Exception as exc:  # pragma: no cover
            logger.warning("solana memo submit failed: %s", exc)
            return None

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

        timestamp = _utcnow()
        memo = _build_memo(data_hash, issuer_id, signature_hex, timestamp)
        solana_sig = await self._send_memo(memo)

        prev_hash = await self._latest_tx_hash()
        local_tx = _compute_tx_hash(prev_hash, data_hash, issuer_id, timestamp)
        # Prefer Solana signature as canonical tx_hash when available
        canonical_tx = solana_sig or local_tx

        async with get_db(self.db_path) as db:
            cur = await db.execute(
                """
                INSERT INTO chain_blocks
                  (prev_hash, tx_hash, data_hash, issuer_id, signature_hex, payload_json, timestamp, solana_tx_signature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prev_hash,
                    canonical_tx,
                    data_hash,
                    issuer_id,
                    signature_hex,
                    json.dumps(metadata or {}),
                    timestamp,
                    solana_sig,
                ),
            )
            block_num = int(cur.lastrowid or 0)

        return ChainReceipt(
            tx_hash=canonical_tx,
            block_num=block_num,
            data_hash=data_hash,
            issuer_id=issuer_id,
            timestamp=timestamp,
            solana_tx_signature=solana_sig,
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
                """
                SELECT * FROM chain_blocks
                WHERE tx_hash = ? OR solana_tx_signature = ?
                """,
                (tx_hash, tx_hash),
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
        # Same hash-chain validation as SimulatedChain — Solana tx is informational
        async with get_db(self.db_path) as db:
            cur = await db.execute("SELECT * FROM chain_blocks ORDER BY block_num ASC")
            rows = await cur.fetchall()

        if not rows:
            return True, "Chain is empty"

        # We don't fully reverify because tx_hash is sometimes the Solana sig.
        # Validate that prev_hash always equals previous row's tx_hash.
        for i, row in enumerate(rows):
            if i == 0:
                if row["prev_hash"] != GENESIS_PREV_HASH:
                    return False, f"Block {row['block_num']}: bad genesis"
            else:
                if row["prev_hash"] != rows[i - 1]["tx_hash"]:
                    return False, f"Block {row['block_num']}: prev_hash mismatch"
        return True, f"Chain valid ({len(rows)} blocks)"

    async def verify_on_chain(self, tx_signature: str) -> dict:
        """Fetch transaction from Solana RPC, extract memo if present."""
        self._lazy_init_client()
        if not self._client:
            return {
                "verified": False,
                "tx_signature": tx_signature,
                "reason": "Solana client not available",
            }
        try:
            from solders.signature import Signature  # type: ignore[import-not-found]

            sig = Signature.from_string(tx_signature)
            resp = self._client.get_transaction(
                sig,
                encoding="jsonParsed",
                max_supported_transaction_version=0,
            )
            value = getattr(resp, "value", None)
            if value is None:
                return {
                    "verified": False,
                    "tx_signature": tx_signature,
                    "reason": "Transaction not found",
                }
            memo_data = self._extract_memo_from_logs(value)
            slot = getattr(value, "slot", None)
            return {
                "verified": True,
                "tx_signature": tx_signature,
                "slot": slot,
                "memo_data": memo_data,
                "explorer_url": (
                    f"https://explorer.solana.com/tx/{tx_signature}?cluster={self.cluster}"
                ),
            }
        except Exception as exc:
            return {
                "verified": False,
                "tx_signature": tx_signature,
                "reason": f"RPC error: {exc}",
            }

    @staticmethod
    def _extract_memo_from_logs(tx_value) -> dict | None:
        """Extract the memo string from a transaction's log messages (best-effort)."""
        try:
            meta = getattr(tx_value, "transaction", None)
            log_messages = getattr(getattr(meta, "meta", None), "log_messages", None) or []
            for line in log_messages:
                if "Memo" in line:
                    # Format: 'Program log: Memo (len 145): "..."'
                    if '"' in line:
                        start = line.index('"') + 1
                        end = line.rindex('"')
                        memo_str = line[start:end]
                        try:
                            return json.loads(memo_str)
                        except json.JSONDecodeError:
                            return {"raw": memo_str}
        except Exception:  # pragma: no cover
            return None
        return None
