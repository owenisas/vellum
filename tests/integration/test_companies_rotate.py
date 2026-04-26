"""Improvement #15: company key rotation."""

import pytest
from eth_account import Account


@pytest.mark.asyncio
async def test_rotate_key(app_client):
    client, app = app_client
    a1 = Account.create()
    await client.post(
        "/api/companies",
        json={
            "name": "Acme",
            "issuer_id": 7,
            "eth_address": a1.address,
            "public_key_hex": a1.address,
            "admin_secret": app.state.settings.registry_admin_secret,
        },
    )
    # Demo identity has company:rotate_key scope
    a2 = Account.create()
    rot = await client.post(
        "/api/companies/7/rotate-key",
        json={
            "new_eth_address": a2.address,
            "new_public_key_hex": a2.address,
            "grace_period_days": 7,
        },
    )
    assert rot.status_code == 200
    body = rot.json()
    assert body["old_key_id"] == 1
    assert body["new_key_id"] == 2
    # Inspect history
    listing = await client.get("/api/companies")
    assert listing.status_code == 200
    target = next(c for c in listing.json() if c["issuer_id"] == 7)
    assert len(target["key_history"]) == 2
    assert target["current_key_id"] == 2
