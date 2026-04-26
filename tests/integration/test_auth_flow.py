"""Integration tests for demo-mode auth and signature-mismatch behavior."""

from __future__ import annotations

from eth_account import Account
from eth_account.messages import encode_defunct

from tests.conftest import sign_text
from vellum.auth.ecdsa import generate_keypair
from vellum.auth.wallets import build_wallet_message


async def test_demo_identity_grants_chat(client):
    """In demo mode (Auth0 disabled), POST /api/chat works without an Authorization header."""
    resp = await client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "demo identity"}]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["text"]


async def test_demo_auto_register_is_idempotent(client):
    """The public demo can bootstrap a browser-held issuer without admin setup."""
    _private_key, public_key, eth_address = generate_keypair()

    first = await client.post(
        "/api/demo/auto-register",
        json={"eth_address": eth_address, "public_key_hex": public_key},
    )
    assert first.status_code == 200, first.text
    created = first.json()
    assert created["issuer_id"] == 1
    assert created["eth_address"].lower() == eth_address.lower()

    again = await client.post(
        "/api/demo/auto-register",
        json={"eth_address": eth_address, "public_key_hex": public_key},
    )
    assert again.status_code == 200, again.text
    assert again.json()["issuer_id"] == created["issuer_id"]

    companies = await client.get("/api/companies")
    assert companies.status_code == 200
    assert len(companies.json()) == 1


async def test_demo_auto_registered_issuer_can_anchor_and_verify(client):
    """Mirrors the public /studio happy path after browser issuer bootstrap."""
    private_key, public_key, eth_address = generate_keypair()

    issuer = await client.post(
        "/api/demo/auto-register",
        json={"eth_address": eth_address, "public_key_hex": public_key},
    )
    assert issuer.status_code == 200, issuer.text

    chat = await client.post(
        "/api/chat",
        json={
            "provider": "fixture",
            "messages": [{"role": "user", "content": "studio happy path"}],
            "watermark": True,
            "wm_params": {
                "issuer_id": issuer.json()["issuer_id"],
                "model_id": 1,
                "model_version_id": 1,
                "key_id": 1,
            },
        },
    )
    assert chat.status_code == 200, chat.text
    text = chat.json()["text"]
    _hash, sig = sign_text(text, private_key)

    anchor = await client.post(
        "/api/anchor",
        json={
            "text": text,
            "raw_text": chat.json()["raw_text"],
            "signature_hex": sig,
            "issuer_id": issuer.json()["issuer_id"],
            "metadata": {"provider": "fixture", "model": "fixture"},
        },
    )
    assert anchor.status_code == 200, anchor.text

    verify = await client.post("/api/verify", json={"text": text})
    assert verify.status_code == 200, verify.text
    assert verify.json()["verified"] is True
    assert verify.json()["issuer_id"] == issuer.json()["issuer_id"]


async def test_anchor_requires_signature_match(client, make_company):
    """A malformed signature should be rejected with 403 mentioning 'signature'."""
    company = await make_company("Mismatch Co")

    chat = await client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "to be signed"}]},
    )
    text = chat.json()["text"]

    # Use a syntactically-valid but content-wrong signature
    bad_sig = "0x" + "00" * 65

    resp = await client.post(
        "/api/anchor",
        json={
            "text": text,
            "raw_text": text,
            "signature_hex": bad_sig,
            "issuer_id": company["issuer_id"],
        },
    )
    assert resp.status_code == 403, resp.text
    detail = resp.json().get("detail", "")
    assert "signature" in detail.lower() or "match" in detail.lower()


async def test_anchor_proof_includes_auth0_agent_action(client, make_company):
    """Anchored proof bundles record the authenticated actor behind the AI action."""
    company = await make_company("Agent Action Co")

    chat = await client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "auth0 agent action"}]},
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
            "metadata": {"provider": "fixture", "model": "fixture-model"},
        },
    )

    assert resp.status_code == 200, resp.text
    agent_action = resp.json()["proof_bundle_v2"]["agent_action"]
    assert agent_action["type"] == "auth0_secured_ai_action"
    assert agent_action["subject"] == "demo|anonymous"
    assert agent_action["permissions"]
    assert agent_action["provider"] == "fixture"
    assert agent_action["model"] == "fixture-model"

    verify = await client.post("/api/verify", json={"text": text})
    assert verify.status_code == 200, verify.text
    assert (
        verify.json()["proof_bundle_v2"]["agent_action"]["subject"]
        == "demo|anonymous"
    )


async def test_anchor_proof_includes_verified_wallet_proof(client, make_company):
    company = await make_company("Wallet Proof Co")

    chat = await client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "wallet proof"}]},
    )
    text = chat.json()["text"]
    data_hash, sig = sign_text(text, company["private_key_hex"])
    wallet_message = build_wallet_message(data_hash, "evm", company["eth_address"])
    wallet_sig = Account.sign_message(
        encode_defunct(text=wallet_message),
        private_key=company["private_key_hex"],
    ).signature.hex()

    resp = await client.post(
        "/api/anchor",
        json={
            "text": text,
            "raw_text": text,
            "signature_hex": sig,
            "issuer_id": company["issuer_id"],
            "wallet_proofs": [
                {
                    "wallet_type": "evm",
                    "address": company["eth_address"],
                    "message": wallet_message,
                    "signature": wallet_sig,
                    "signature_encoding": "hex",
                    "chain_id": "31337",
                }
            ],
        },
    )

    assert resp.status_code == 200, resp.text
    wallet_proofs = resp.json()["proof_bundle_v2"]["wallet_proofs"]
    assert wallet_proofs[0]["wallet_type"] == "evm"
    assert wallet_proofs[0]["address"].lower() == company["eth_address"].lower()
    assert wallet_proofs[0]["chain_id"] == "31337"

    verify = await client.post("/api/verify", json={"text": text})
    assert verify.status_code == 200, verify.text
    assert verify.json()["proof_bundle_v2"]["wallet_proofs"][0]["wallet_type"] == "evm"


async def test_anchor_rejects_invalid_wallet_proof(client, make_company):
    company = await make_company("Bad Wallet Proof Co")

    chat = await client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "bad wallet proof"}]},
    )
    text = chat.json()["text"]
    data_hash, sig = sign_text(text, company["private_key_hex"])
    wallet_message = build_wallet_message(data_hash, "evm", company["eth_address"])

    resp = await client.post(
        "/api/anchor",
        json={
            "text": text,
            "raw_text": text,
            "signature_hex": sig,
            "issuer_id": company["issuer_id"],
            "wallet_proofs": [
                {
                    "wallet_type": "evm",
                    "address": company["eth_address"],
                    "message": wallet_message,
                    "signature": "0x" + "00" * 65,
                    "signature_encoding": "hex",
                }
            ],
        },
    )

    assert resp.status_code == 400, resp.text
    assert "wallet proof" in resp.json()["detail"].lower()


async def test_demo_mode_allows_companies_get_without_auth(client, make_company):
    """In demo mode, GET /api/companies (auth-required) succeeds without Authorization."""
    await make_company("Auth Demo Co")
    resp = await client.get("/api/companies")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_anchor_with_unknown_issuer_id(client, make_company):
    """Unknown issuer_id is a permission error (caught and re-raised as 403)."""
    company = await make_company("Issuer Co")

    chat = await client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "unknown issuer"}]},
    )
    text = chat.json()["text"]
    _hash, sig = sign_text(text, company["private_key_hex"])

    resp = await client.post(
        "/api/anchor",
        json={
            "text": text,
            "raw_text": text,
            "signature_hex": sig,
            "issuer_id": 999999,  # never registered
        },
    )
    assert resp.status_code == 403
