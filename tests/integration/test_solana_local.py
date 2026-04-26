import base64
import json

import pytest

from veritext.chain.borsh_schema import decode_memo
from veritext.chain.solana import SolanaChain
from veritext.config.settings import get_settings


DATA_HASH = "ab" * 32
SIGNATURE_HEX = "cd" * 65
SOLANA_SIGNATURE = "5xLocalSolanaSignature111111111111111111111111111111111"


@pytest.mark.asyncio
async def test_solana_anchor_persists_local_block(local_solana_env, db_conn, monkeypatch):
    async def fake_post_memo(self, memo_bytes):
        return SOLANA_SIGNATURE

    monkeypatch.setattr(SolanaChain, "_post_memo", fake_post_memo)
    chain = SolanaChain(settings=get_settings(), db_conn=db_conn)

    receipt = await chain.anchor(
        data_hash=DATA_HASH,
        issuer_id=42,
        signature_hex=SIGNATURE_HEX,
    )

    latest = await chain.latest()
    assert latest is not None
    assert receipt.block_num == latest.block_num == 0
    assert receipt.tx_hash == latest.tx_hash
    assert receipt.data_hash == latest.data_hash == DATA_HASH
    assert receipt.issuer_id == latest.issuer_id == 42
    assert receipt.solana_tx_signature == latest.solana_tx_signature == SOLANA_SIGNATURE


@pytest.mark.asyncio
async def test_solana_rpc_failure_falls_back_to_local_anchor(local_solana_env, db_conn, monkeypatch):
    async def fail_post_memo(self, memo_bytes):
        raise RuntimeError("rpc unavailable")

    monkeypatch.setattr(SolanaChain, "_post_memo", fail_post_memo)
    chain = SolanaChain(settings=get_settings(), db_conn=db_conn)

    receipt = await chain.anchor(
        data_hash="ef" * 32,
        issuer_id=7,
        signature_hex=SIGNATURE_HEX,
    )

    latest = await chain.latest()
    assert latest is not None
    assert receipt.tx_hash == latest.tx_hash
    assert len(receipt.tx_hash) == 64
    assert receipt.solana_tx_signature is None
    assert latest.solana_tx_signature is None


@pytest.mark.asyncio
async def test_solana_memo_payload_is_stored(local_solana_env, db_conn, monkeypatch):
    async def fake_post_memo(self, memo_bytes):
        return SOLANA_SIGNATURE

    monkeypatch.setattr(SolanaChain, "_post_memo", fake_post_memo)
    chain = SolanaChain(settings=get_settings(), db_conn=db_conn)

    await chain.anchor(
        data_hash=DATA_HASH,
        issuer_id=99,
        signature_hex=SIGNATURE_HEX,
    )

    cur = await db_conn.execute("SELECT payload_json FROM chain_blocks ORDER BY block_num DESC LIMIT 1")
    row = await cur.fetchone()
    payload = json.loads(row["payload_json"])
    memo = decode_memo(base64.b64decode(payload["memo_b64"]))

    assert memo.data_hash.hex() == DATA_HASH
    assert memo.issuer_id == 99
    assert memo.sig_prefix == bytes.fromhex(SIGNATURE_HEX)[:20]
    assert memo.merkle_root is None


@pytest.mark.asyncio
async def test_solana_status_api_uses_local_db_state(solana_app_client, monkeypatch):
    client, app = solana_app_client

    async def fake_post_memo(self, memo_bytes):
        return SOLANA_SIGNATURE

    monkeypatch.setattr(SolanaChain, "_post_memo", fake_post_memo)
    receipt = await app.state.chain.anchor(
        data_hash=DATA_HASH,
        issuer_id=42,
        signature_hex=SIGNATURE_HEX,
    )

    resp = await client.get("/api/chain/status")

    assert resp.status_code == 200
    body = resp.json()
    assert body["chain_type"] == "solana"
    assert body["block_count"] == 1
    assert body["latest_tx_hash"] == receipt.tx_hash
