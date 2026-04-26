"""Integration tests for /api/chain/*."""

from __future__ import annotations

from tests.conftest import sign_text


async def _anchor(client, company: dict, prompt: str) -> dict:
    chat = await client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": prompt}]},
    )
    text = chat.json()["text"]
    _hash, sig = sign_text(text, company["private_key_hex"])
    resp = await client.post(
        "/api/anchor",
        json={
            "text": text,
            "raw_text": text,
            "signature_hex": sig,
            "issuer_id": company["issuer_id"],
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_chain_status_after_two_anchors(client, make_company):
    company = await make_company("Chain Co")

    a = await _anchor(client, company, "first anchor")
    b = await _anchor(client, company, "second anchor")
    assert a["chain_receipt"]["block_num"] == 1
    assert b["chain_receipt"]["block_num"] == 2

    resp = await client.get("/api/chain/status")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["length"] == 2
    assert data["valid"] is True


async def test_list_blocks_returns_descending(client, make_company):
    company = await make_company("Blocks Co")
    await _anchor(client, company, "alpha")
    await _anchor(client, company, "beta")

    resp = await client.get("/api/chain/blocks")
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert isinstance(rows, list)
    assert len(rows) == 2

    # Listing should be in descending block_num order (latest first).
    assert rows[0]["block_num"] >= rows[1]["block_num"]


async def test_get_block_by_num(client, make_company):
    company = await make_company("Lookup Co")
    await _anchor(client, company, "block 1")

    resp = await client.get("/api/chain/blocks/1")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["block_num"] == 1
    assert data["tx_hash"]
    assert data["data_hash"]


async def test_get_block_unknown_returns_404(client):
    resp = await client.get("/api/chain/blocks/9999")
    assert resp.status_code == 404
