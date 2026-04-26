"""
Merkle batching service. Drains pending anchors every N seconds, builds a
Merkle tree, anchors the root, and back-fills inclusion proofs.

This service is wired into the FastAPI lifespan in app.py.
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

import structlog

from merklebatch import build_root_and_proofs
from veritext.db.repositories import ChainRepo, PendingAnchorRepo

if TYPE_CHECKING:
    from veritext.chain.protocol import ChainBackend

log = structlog.get_logger("veritext.merkle")


class MerkleBatchService:
    """
    Run as a background task. Periodically reads pending anchors, builds a
    Merkle tree from their data hashes, anchors only the root, and writes
    chain blocks for each leaf with the inclusion proof attached.
    """

    def __init__(
        self,
        *,
        chain: "ChainBackend",
        chain_repo: ChainRepo,
        pending_repo: PendingAnchorRepo,
        window_seconds: int,
        max_leaves: int,
    ) -> None:
        self._chain = chain
        self._chain_repo = chain_repo
        self._pending = pending_repo
        self._window = window_seconds
        self._max_leaves = max_leaves
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    def start(self) -> None:
        if self._task is None:
            self._stop.clear()
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self._window)
            except asyncio.TimeoutError:
                pass
            await self.drain_once()

    async def drain_once(self) -> int:
        pending = await self._pending.list_unpromoted(limit=self._max_leaves)
        if not pending:
            return 0
        leaves = [row["data_hash"] for row in pending]
        root, proofs = build_root_and_proofs(leaves)
        receipt = await self._chain.anchor(
            data_hash=root,
            issuer_id=0,
            signature_hex="",
            metadata={"type": "merkle_root", "leaf_count": len(leaves)},
            batch_hint={"merkle_root": root, "leaf_count": len(leaves)},
        )
        timestamp = receipt.timestamp
        for proof, row in zip(proofs, pending):
            payload = json.loads(row["payload_json"]) if row.get("payload_json") else {}
            await self._chain_repo.append(
                prev_hash=receipt.tx_hash,
                tx_hash=receipt.tx_hash,
                data_hash=row["data_hash"],
                issuer_id=row["issuer_id"],
                signature_hex=row["signature_hex"],
                payload=payload,
                timestamp=timestamp,
                solana_tx_signature=receipt.solana_tx_signature,
                merkle_root=root,
                leaf_index=proof.leaf_index,
                inclusion_proof=proof.steps,
            )
        await self._pending.mark_promoted([row["id"] for row in pending])
        log.info("merkle_batch_drained", leaves=len(leaves), root=root[:16])
        return len(leaves)
