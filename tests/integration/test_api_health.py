"""Integration tests for /api/health."""

from __future__ import annotations


async def test_health_endpoint(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["status"] == "ok"
    assert data["demo_mode"] == "fixture"
    assert data["chain_backend"] == "simulated"
    assert data["auth0_enabled"] is False
    # Solana cluster only populated when chain_backend == solana
    assert data.get("solana_cluster") in (None, "")
    assert "chain" in data
    assert data["chain"]["valid"] is True
    assert data["chain"]["length"] == 0
