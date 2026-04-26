"""Solana backend coverage for local persistence and RPC fallback behavior."""

from __future__ import annotations

import pytest

from tests.conftest import sign_text
from vellum.chain.factory import create_chain
from vellum.chain.solana import SolanaChain
from vellum.db.repositories import ChainBlockRepository

DATA_HASH = "ab" * 32
SIGNATURE_HEX = "0x" + "cd" * 65
SOLANA_SIGNATURE = "5xLocalSolanaSignature111111111111111111111111111111111"


async def _solana_chain(settings):
    chain = await create_chain(settings)
    assert isinstance(chain, SolanaChain)
    return chain


async def test_solana_anchor_persists_local_block(local_solana_env, monkeypatch):
    async def fake_send_memo(self, memo):
        return SOLANA_SIGNATURE

    monkeypatch.setattr(SolanaChain, "_send_memo", fake_send_memo)
    chain = await _solana_chain(local_solana_env)

    receipt = await chain.anchor(
        data_hash=DATA_HASH,
        issuer_id=42,
        signature_hex=SIGNATURE_HEX,
    )

    latest = await ChainBlockRepository(local_solana_env.db_path).latest()
    assert latest is not None
    assert receipt.block_num == int(latest["block_num"])
    assert receipt.tx_hash == latest["tx_hash"]
    assert receipt.data_hash == latest["data_hash"] == DATA_HASH
    assert receipt.issuer_id == int(latest["issuer_id"]) == 42
    assert receipt.solana_tx_signature == latest["solana_tx_signature"] == SOLANA_SIGNATURE
    assert latest["payload"]["solana_local_fallback"] is False


async def test_solana_rpc_failure_falls_back_to_local_anchor(local_solana_env, monkeypatch):
    async def fail_send_memo(self, memo):
        return None

    monkeypatch.setattr(SolanaChain, "_send_memo", fail_send_memo)
    chain = await _solana_chain(local_solana_env)

    receipt = await chain.anchor(
        data_hash="ef" * 32,
        issuer_id=7,
        signature_hex=SIGNATURE_HEX,
    )

    latest = await ChainBlockRepository(local_solana_env.db_path).latest()
    assert latest is not None
    assert receipt.tx_hash == latest["tx_hash"]
    assert len(receipt.tx_hash) == 64
    assert receipt.solana_tx_signature is None
    assert latest["solana_tx_signature"] is None
    assert latest["payload"]["solana_local_fallback"] is True


async def test_solana_local_hash_chain_links_blocks(local_solana_env, monkeypatch):
    async def fake_send_memo(self, memo):
        return None

    monkeypatch.setattr(SolanaChain, "_send_memo", fake_send_memo)
    chain = await _solana_chain(local_solana_env)

    receipts = []
    for idx in range(3):
        receipts.append(
            await chain.anchor(
                data_hash=f"{idx + 1:064x}",
                issuer_id=42,
                signature_hex=SIGNATURE_HEX,
            )
        )

    blocks = await ChainBlockRepository(local_solana_env.db_path).list_blocks(limit=10)
    blocks = sorted(blocks, key=lambda block: block["block_num"])
    assert [block["tx_hash"] for block in blocks] == [receipt.tx_hash for receipt in receipts]
    assert blocks[0]["prev_hash"] == "0" * 64
    assert blocks[1]["prev_hash"] == blocks[0]["tx_hash"]
    assert blocks[2]["prev_hash"] == blocks[1]["tx_hash"]


async def test_solana_memo_payload_is_stored(local_solana_env, monkeypatch):
    async def fake_send_memo(self, memo):
        return SOLANA_SIGNATURE

    monkeypatch.setattr(SolanaChain, "_send_memo", fake_send_memo)
    chain = await _solana_chain(local_solana_env)

    await chain.anchor(
        data_hash=DATA_HASH,
        issuer_id=99,
        signature_hex=SIGNATURE_HEX,
    )

    latest = await ChainBlockRepository(local_solana_env.db_path).latest()
    memo = latest["payload"]["solana_memo"]
    assert memo["h"] == DATA_HASH
    assert memo["i"] == 99
    assert memo["s"] == SIGNATURE_HEX[:42]


async def test_solana_status_and_blocks_api_use_local_db(solana_client, monkeypatch):
    client, app = solana_client

    async def fake_send_memo(self, memo):
        return SOLANA_SIGNATURE

    monkeypatch.setattr(SolanaChain, "_send_memo", fake_send_memo)
    receipt = await app.state.chain_backend.anchor(
        data_hash=DATA_HASH,
        issuer_id=42,
        signature_hex=SIGNATURE_HEX,
    )

    status_resp = await client.get("/api/chain/status")
    assert status_resp.status_code == 200, status_resp.text
    status = status_resp.json()
    assert status["backend"] == "solana"
    assert status["length"] == 1
    assert status["latest_data_hash"] == DATA_HASH

    blocks_resp = await client.get("/api/chain/blocks")
    assert blocks_resp.status_code == 200, blocks_resp.text
    block = blocks_resp.json()[0]
    assert block["tx_hash"] == receipt.tx_hash
    assert block["solana_tx_signature"] == SOLANA_SIGNATURE


async def test_solana_proof_marks_local_fallback(solana_client, monkeypatch):
    client, _app = solana_client

    async def fail_send_memo(self, memo):
        return None

    monkeypatch.setattr(SolanaChain, "_send_memo", fail_send_memo)
    company_resp = await client.post(
        "/api/companies",
        json={"name": "Fallback Co", "auto_generate": True, "admin_secret": "dev-admin-secret"},
    )
    assert company_resp.status_code == 200, company_resp.text
    company = company_resp.json()

    chat_resp = await client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "fallback proof"}]},
    )
    text = chat_resp.json()["text"]
    _hash, sig = sign_text(text, company["private_key_hex"])
    anchor_resp = await client.post(
        "/api/anchor",
        json={
            "text": text,
            "raw_text": text,
            "signature_hex": sig,
            "issuer_id": company["issuer_id"],
        },
    )

    assert anchor_resp.status_code == 200, anchor_resp.text
    body = anchor_resp.json()
    anchor = body["proof_bundle_v2"]["anchors"][0]
    assert body["chain_receipt"]["solana_tx_signature"] is None
    assert anchor["type"] == "solana_local_fallback"
    assert anchor["tx_hash"] == body["chain_receipt"]["tx_hash"]
    assert body["proof_bundle_v2"]["verification_hints"]["explorer_url"] is None


async def test_solana_rejects_short_data_hash_before_local_write(local_solana_env):
    chain = await _solana_chain(local_solana_env)

    with pytest.raises(ValueError, match="data_hash must be 32 bytes"):
        await chain.anchor(
            data_hash="aa" * 31,
            issuer_id=42,
            signature_hex=SIGNATURE_HEX,
        )

    assert await ChainBlockRepository(local_solana_env.db_path).count() == 0


async def test_solana_rejects_bad_signature_before_local_write(local_solana_env):
    chain = await _solana_chain(local_solana_env)

    with pytest.raises(ValueError, match="non-hexadecimal number"):
        await chain.anchor(
            data_hash=DATA_HASH,
            issuer_id=42,
            signature_hex="not-a-hex-signature",
        )

    assert await ChainBlockRepository(local_solana_env.db_path).count() == 0
