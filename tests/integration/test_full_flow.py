"""End-to-end: chat → sign → anchor → verify on simulated chain."""

import hashlib

import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data


@pytest.mark.asyncio
async def test_chat_anchor_verify_flow(app_client):
    client, app = app_client

    # 1. Register a company (Auth0 disabled → admin_secret path)
    acct = Account.create()
    company_resp = await client.post(
        "/api/companies",
        json={
            "name": "Acme",
            "issuer_id": 42,
            "eth_address": acct.address,
            "public_key_hex": acct.address,
            "admin_secret": app.state.settings.registry_admin_secret,
        },
    )
    assert company_resp.status_code == 200, company_resp.text

    # 2. Generate watermarked text via fixture provider
    chat_resp = await client.post(
        "/api/chat",
        json={"prompt": "Hello", "model": "fixture", "provider": "fixture", "watermark": True,
              "watermark_params": {"issuer_id": 42, "model_id": 1, "model_version_id": 1}},
    )
    assert chat_resp.status_code == 200
    chat = chat_resp.json()
    assert chat["watermarked"] is True
    text = chat["text"]

    # 3. Sign EIP-712 typed-data
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    timestamp = 1_700_000_000
    bundle_nonce = "00" * 32
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
            "issuerId": 42,
            "timestamp": timestamp,
            "bundleNonce": bytes.fromhex(bundle_nonce),
        },
    }
    signable = encode_typed_data(full_message=typed)
    signed = Account.sign_message(signable, private_key=acct.key)

    # 4. Anchor
    anchor_resp = await client.post(
        "/api/anchor",
        json={
            "text": text,
            "issuer_id": 42,
            "signature_hex": signed.signature.hex(),
            "sig_scheme": "eip712",
            "timestamp": timestamp,
            "bundle_nonce_hex": bundle_nonce,
        },
    )
    assert anchor_resp.status_code == 200, anchor_resp.text
    body = anchor_resp.json()
    assert body["sha256_hash"] == text_hash
    assert body["proof_bundle_v2"]["spec"] == "veritext-proof-bundle/v2"
    assert body["proof_bundle_v2"]["bundle_id"].startswith("vtb2_")

    # 5. Verify
    verify_resp = await client.post("/api/verify", json={"text": text})
    assert verify_resp.status_code == 200
    v = verify_resp.json()
    assert v["verified"] is True
    assert v["issuer_id"] == 42
