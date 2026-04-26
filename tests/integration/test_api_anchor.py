"""Integration tests for the full anchor → verify → proof pipeline."""

from __future__ import annotations

from tests.conftest import sign_text


async def _watermarked_chat(client, prompt: str = "anchor flow") -> str:
    chat = await client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": prompt}]},
    )
    assert chat.status_code == 200, chat.text
    data = chat.json()
    assert data["watermarked"] is True
    return data["text"]


async def test_full_anchor_verify_pipeline(client, make_company):
    company = await make_company("Pipeline Co")
    text = await _watermarked_chat(client, "the full pipeline")

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
    anchor = anchor_resp.json()

    bundle = anchor["proof_bundle_v2"]
    assert bundle["spec"] == "vellum-proof-bundle/v2"
    assert bundle["bundle_id"].startswith("vpb2_")
    assert anchor["chain_receipt"]["block_num"] >= 1
    assert bundle["anchors"][0]["block_num"] >= 1
    assert bundle["anchors"][0]["type"] == "simulated_chain"

    # verify the same text round-trips
    verify_resp = await client.post("/api/verify", json={"text": text})
    assert verify_resp.status_code == 200
    verify = verify_resp.json()
    assert verify["verified"] is True
    assert verify["issuer_id"] == company["issuer_id"]
    assert verify["proof_bundle_v2"] is not None


async def test_verify_unanchored_text_returns_false(client):
    resp = await client.post(
        "/api/verify",
        json={"text": "this text was never anchored"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["verified"] is False
    assert data["watermark"] is not None  # still populated
    assert data["sha256_hash"]


async def test_proof_by_tx_hash(client, make_company):
    company = await make_company("ProofTx Co")
    text = await _watermarked_chat(client, "proof by tx_hash")

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
    assert anchor_resp.status_code == 200
    tx_hash = anchor_resp.json()["chain_receipt"]["tx_hash"]

    resp = await client.get(f"/api/proof/tx/{tx_hash}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["found"] is True
    assert data["proof_bundle_v2"] is not None
    assert data["proof_bundle_v2"]["bundle_id"].startswith("vpb2_")


async def test_anchor_with_wrong_signature_returns_403(client, make_company):
    company = await make_company("Bad Sig Co")
    text = await _watermarked_chat(client, "wrong signature scenario")

    # Sign the text with a *different* private key.
    from vellum.auth.ecdsa import generate_keypair

    bad_priv, _bad_pub, _bad_addr = generate_keypair()
    _hash, sig = sign_text(text, bad_priv)

    resp = await client.post(
        "/api/anchor",
        json={
            "text": text,
            "raw_text": text,
            "signature_hex": sig,
            "issuer_id": company["issuer_id"],
        },
    )
    assert resp.status_code == 403, resp.text
    detail = resp.json().get("detail", "")
    assert "signature" in detail.lower() or "match" in detail.lower()


async def test_proof_by_text(client, make_company):
    company = await make_company("Proof Text Co")
    text = await _watermarked_chat(client, "proof by text")

    _hash, sig = sign_text(text, company["private_key_hex"])
    await client.post(
        "/api/anchor",
        json={
            "text": text,
            "raw_text": text,
            "signature_hex": sig,
            "issuer_id": company["issuer_id"],
        },
    )

    resp = await client.post("/api/proof/text", json={"text": text})
    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is True
    assert data["proof_bundle_v2"]["bundle_id"].startswith("vpb2_")
