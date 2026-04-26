"""Integration tests for the /api/companies endpoints."""

from __future__ import annotations


async def test_create_company_returns_private_key(client):
    resp = await client.post(
        "/api/companies",
        json={
            "name": "Test Co",
            "auto_generate": True,
            "admin_secret": "dev-admin-secret",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["name"] == "Test Co"
    assert data["issuer_id"] >= 1
    assert data["eth_address"].startswith("0x")
    assert data["public_key_hex"]
    assert data["private_key_hex"]  # only present on creation
    assert data["private_key_hex"].startswith("0x") or len(data["private_key_hex"]) == 64
    assert data["note"]  # human-readable warning to save the key


async def test_list_companies_omits_private_key(client):
    create = await client.post(
        "/api/companies",
        json={"name": "Listable Co", "auto_generate": True, "admin_secret": "dev-admin-secret"},
    )
    assert create.status_code == 200
    created = create.json()

    resp = await client.get("/api/companies")
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert isinstance(rows, list)

    matched = [r for r in rows if r["issuer_id"] == created["issuer_id"]]
    assert matched, f"newly-created company missing from list: {rows}"
    row = matched[0]

    # private_key_hex must NOT be in the listing response
    assert "private_key_hex" not in row
    assert row["name"] == "Listable Co"
    assert row["eth_address"] == created["eth_address"]


async def test_create_company_assigns_unique_issuer_ids(client):
    a = await client.post(
        "/api/companies",
        json={"name": "Co A", "auto_generate": True, "admin_secret": "dev-admin-secret"},
    )
    b = await client.post(
        "/api/companies",
        json={"name": "Co B", "auto_generate": True, "admin_secret": "dev-admin-secret"},
    )
    assert a.status_code == 200
    assert b.status_code == 200
    assert a.json()["issuer_id"] != b.json()["issuer_id"]
