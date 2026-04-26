async def test_health(app_client):
    client, _ = app_client
    r = await client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "veritext"
