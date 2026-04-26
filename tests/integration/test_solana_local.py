import base64
import hashlib
import json

import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data

from veritext.chain.borsh_schema import decode_memo
from veritext.chain.solana import SolanaChain
from veritext.config.settings import get_settings


DATA_HASH = "ab" * 32
SIGNATURE_HEX = "cd" * 65
SOLANA_SIGNATURE = "5xLocalSolanaSignature111111111111111111111111111111111"


def _sign_anchor(text: str, issuer_id: int, private_key, timestamp: int, bundle_nonce: str):
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    typed = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "VeritextAnchor": [
                {"name": "textHash", "type": "bytes32"},
                {"name": "issuerId", "type": "uint256"},
                {"name": "timestamp", "type": "uint256"},
                {"name": "bundleNonce", "type": "bytes32"},
            ],
        },
        "primaryType": "VeritextAnchor",
        "domain": {
            "name": "Veritext",
            "version": "2",
            "chainId": 1,
            "verifyingContract": "0x0000000000000000000000000000000000000000",
        },
        "message": {
            "textHash": bytes.fromhex(text_hash),
            "issuerId": issuer_id,
            "timestamp": timestamp,
            "bundleNonce": bytes.fromhex(bundle_nonce),
        },
    }
    return Account.sign_message(encode_typed_data(full_message=typed), private_key=private_key)


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
async def test_solana_local_hash_chain_links_blocks(local_solana_env, db_conn, monkeypatch):
    async def fake_post_memo(self, memo_bytes):
        return SOLANA_SIGNATURE

    monkeypatch.setattr(SolanaChain, "_post_memo", fake_post_memo)
    chain = SolanaChain(settings=get_settings(), db_conn=db_conn)

    receipts = []
    for idx in range(3):
        receipts.append(
            await chain.anchor(
                data_hash=f"{idx + 1:064x}",
                issuer_id=42,
                signature_hex=SIGNATURE_HEX,
            )
        )

    blocks = await chain.list_blocks(limit=10, offset=0)
    blocks = sorted(blocks, key=lambda block: block.block_num)
    assert [block.block_num for block in blocks] == [0, 1, 2]
    assert [block.tx_hash for block in blocks] == [receipt.tx_hash for receipt in receipts]
    assert blocks[0].prev_hash == "0" * 64
    assert blocks[1].prev_hash == blocks[0].tx_hash
    assert blocks[2].prev_hash == blocks[1].tx_hash


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


@pytest.mark.asyncio
async def test_solana_block_list_exposes_signatures(solana_app_client, monkeypatch):
    client, app = solana_app_client

    async def fake_post_memo(self, memo_bytes):
        return SOLANA_SIGNATURE

    monkeypatch.setattr(SolanaChain, "_post_memo", fake_post_memo)
    receipt = await app.state.chain.anchor(
        data_hash=DATA_HASH,
        issuer_id=42,
        signature_hex=SIGNATURE_HEX,
    )

    resp = await client.get("/api/chain/blocks")

    assert resp.status_code == 200
    [block] = resp.json()
    assert block["tx_hash"] == receipt.tx_hash
    assert block["data_hash"] == DATA_HASH
    assert block["solana_tx_signature"] == SOLANA_SIGNATURE


@pytest.mark.asyncio
async def test_proof_bundle_solana_anchor_metadata(solana_app_client, monkeypatch):
    client, app = solana_app_client
    issuer_id = 42
    text = "locally anchored Solana proof bundle"
    timestamp = 1_700_000_000
    bundle_nonce = "00" * 32
    acct = Account.create()

    async def fake_post_memo(self, memo_bytes):
        return SOLANA_SIGNATURE

    monkeypatch.setattr(SolanaChain, "_post_memo", fake_post_memo)
    company_resp = await client.post(
        "/api/companies",
        json={
            "name": "Solana Co",
            "issuer_id": issuer_id,
            "eth_address": acct.address,
            "public_key_hex": acct.address,
            "admin_secret": app.state.settings.registry_admin_secret,
        },
    )
    assert company_resp.status_code == 200, company_resp.text
    signed = _sign_anchor(text, issuer_id, acct.key, timestamp, bundle_nonce)

    anchor_resp = await client.post(
        "/api/anchor",
        json={
            "text": text,
            "issuer_id": issuer_id,
            "signature_hex": signed.signature.hex(),
            "sig_scheme": "eip712",
            "timestamp": timestamp,
            "bundle_nonce_hex": bundle_nonce,
        },
    )

    assert anchor_resp.status_code == 200, anchor_resp.text
    body = anchor_resp.json()
    anchor = body["proof_bundle_v2"]["anchors"][0]
    assert body["chain_receipt"]["tx_hash"] != SOLANA_SIGNATURE
    assert body["chain_receipt"]["solana_tx_signature"] == SOLANA_SIGNATURE
    assert anchor["type"] == "solana_per_response"
    assert anchor["memo_encoding"] == "borsh"
    assert anchor["tx_hash"] == SOLANA_SIGNATURE
    assert body["proof_bundle_v2"]["verification_hints"]["explorer_url"] == (
        f"https://explorer.solana.com/tx/{SOLANA_SIGNATURE}?cluster=devnet"
    )


@pytest.mark.asyncio
async def test_proof_bundle_labels_solana_fallback_as_local(solana_app_client, monkeypatch):
    client, app = solana_app_client
    issuer_id = 43
    text = "Solana RPC fallback proof bundle"
    timestamp = 1_700_000_001
    bundle_nonce = "11" * 32
    acct = Account.create()

    async def fail_post_memo(self, memo_bytes):
        raise RuntimeError("rpc unavailable")

    monkeypatch.setattr(SolanaChain, "_post_memo", fail_post_memo)
    company_resp = await client.post(
        "/api/companies",
        json={
            "name": "Fallback Co",
            "issuer_id": issuer_id,
            "eth_address": acct.address,
            "public_key_hex": acct.address,
            "admin_secret": app.state.settings.registry_admin_secret,
        },
    )
    assert company_resp.status_code == 200, company_resp.text
    signed = _sign_anchor(text, issuer_id, acct.key, timestamp, bundle_nonce)

    anchor_resp = await client.post(
        "/api/anchor",
        json={
            "text": text,
            "issuer_id": issuer_id,
            "signature_hex": signed.signature.hex(),
            "sig_scheme": "eip712",
            "timestamp": timestamp,
            "bundle_nonce_hex": bundle_nonce,
        },
    )

    assert anchor_resp.status_code == 200, anchor_resp.text
    body = anchor_resp.json()
    anchor = body["proof_bundle_v2"]["anchors"][0]
    assert body["chain_receipt"]["solana_tx_signature"] is None
    assert anchor["type"] == "solana_local_fallback"
    assert anchor["tx_hash"] == body["chain_receipt"]["tx_hash"]
    assert body["proof_bundle_v2"]["verification_hints"]["explorer_url"] is None


@pytest.mark.asyncio
async def test_solana_rejects_short_data_hash_before_local_write(local_solana_env, db_conn):
    chain = SolanaChain(settings=get_settings(), db_conn=db_conn)

    with pytest.raises(ValueError, match="data_hash must be 32 bytes"):
        await chain.anchor(
            data_hash="aa" * 31,
            issuer_id=42,
            signature_hex=SIGNATURE_HEX,
        )

    assert await chain.count() == 0


@pytest.mark.asyncio
async def test_solana_batch_hint_merkle_root_is_stored_in_memo(local_solana_env, db_conn, monkeypatch):
    merkle_root = "12" * 32

    async def fake_post_memo(self, memo_bytes):
        return SOLANA_SIGNATURE

    monkeypatch.setattr(SolanaChain, "_post_memo", fake_post_memo)
    chain = SolanaChain(settings=get_settings(), db_conn=db_conn)

    receipt = await chain.anchor(
        data_hash=DATA_HASH,
        issuer_id=42,
        signature_hex=SIGNATURE_HEX,
        batch_hint={"merkle_root": merkle_root},
    )

    cur = await db_conn.execute(
        "SELECT payload_json, merkle_root FROM chain_blocks ORDER BY block_num DESC LIMIT 1"
    )
    row = await cur.fetchone()
    payload = json.loads(row["payload_json"])
    memo = decode_memo(base64.b64decode(payload["memo_b64"]))

    assert receipt.merkle_root == merkle_root
    assert row["merkle_root"] == merkle_root
    assert memo.merkle_root == bytes.fromhex(merkle_root)
