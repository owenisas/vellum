"""Unit tests for :class:`SimulatedChain`."""

from __future__ import annotations

import json

import pytest

from vellum.chain.simulated import GENESIS_PREV_HASH, SimulatedChain
from vellum.db.connection import get_db


@pytest.fixture
def chain(tmp_path):
    return SimulatedChain(str(tmp_path / "chain.db"))


async def test_anchor_then_lookup(chain):
    receipt = await chain.anchor(
        data_hash="d" * 64,
        issuer_id=1,
        signature_hex="0x" + "ab" * 65,
        metadata={"hello": "world"},
    )

    assert receipt.block_num == 1
    assert receipt.data_hash == "d" * 64

    record = await chain.lookup("d" * 64)
    assert record is not None
    assert record.tx_hash == receipt.tx_hash
    assert record.issuer_id == 1
    assert record.payload == {"hello": "world"}


async def test_chain_links_correctly(chain):
    hashes = [chr(ord("a") + i) * 64 for i in range(3)]
    receipts = []
    for h in hashes:
        r = await chain.anchor(
            data_hash=h,
            issuer_id=1,
            signature_hex="0x" + "11" * 65,
        )
        receipts.append(r)

    valid, message = await chain.validate_chain()
    assert valid is True, message

    # Inspect the raw rows to assert linkage
    async with get_db(chain.db_path) as db:
        cur = await db.execute(
            "SELECT block_num, prev_hash, tx_hash FROM chain_blocks ORDER BY block_num ASC"
        )
        rows = [dict(r) for r in await cur.fetchall()]

    assert rows[0]["prev_hash"] == GENESIS_PREV_HASH
    for prev, current in zip(rows, rows[1:]):
        assert current["prev_hash"] == prev["tx_hash"]


async def test_lookup_unknown_returns_none(chain):
    await chain.initialize()
    assert await chain.lookup("0" * 64) is None
    assert await chain.lookup_tx("0" * 64) is None


async def test_validate_chain_detects_tamper(chain):
    await chain.anchor(data_hash="a" * 64, issuer_id=1, signature_hex="0x00")
    await chain.anchor(data_hash="b" * 64, issuer_id=1, signature_hex="0x00")

    # Manually overwrite block 2's prev_hash with garbage.
    async with get_db(chain.db_path) as db:
        await db.execute(
            "UPDATE chain_blocks SET prev_hash = ? WHERE block_num = 2",
            ("f" * 64,),
        )

    valid, message = await chain.validate_chain()
    assert valid is False
    assert "prev_hash" in message or "mismatch" in message


async def test_chain_length(chain):
    await chain.initialize()
    assert await chain.chain_length() == 0

    await chain.anchor(data_hash="a" * 64, issuer_id=1, signature_hex="0x00")
    assert await chain.chain_length() == 1

    await chain.anchor(data_hash="b" * 64, issuer_id=1, signature_hex="0x00")
    assert await chain.chain_length() == 2


async def test_verify_matches_anchored_record(chain):
    receipt = await chain.anchor(
        data_hash="c" * 64,
        issuer_id=1,
        signature_hex="0x00",
    )
    assert await chain.verify("c" * 64, receipt.tx_hash) is True
    assert await chain.verify("0" * 64, receipt.tx_hash) is False
    assert await chain.verify("c" * 64, "deadbeef" * 8) is False


async def test_metadata_is_json_serialized(chain):
    """Sanity check: metadata round-trips through aiosqlite as JSON."""
    md = {"foo": [1, 2, 3], "nested": {"k": "v"}}
    receipt = await chain.anchor(
        data_hash="e" * 64,
        issuer_id=1,
        signature_hex="0x00",
        metadata=md,
    )
    record = await chain.lookup_tx(receipt.tx_hash)
    assert record is not None
    assert record.payload == md
    # And the raw column is genuinely JSON
    async with get_db(chain.db_path) as db:
        cur = await db.execute(
            "SELECT payload_json FROM chain_blocks WHERE block_num = ?",
            (receipt.block_num,),
        )
        row = await cur.fetchone()
    assert json.loads(row["payload_json"]) == md
