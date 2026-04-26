"""Integration tests for demo-mode auth and signature-mismatch behavior."""

from __future__ import annotations

from tests.conftest import sign_text


async def test_demo_identity_grants_chat(client):
    """In demo mode (Auth0 disabled), POST /api/chat works without an Authorization header."""
    resp = await client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "demo identity"}]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["text"]


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
