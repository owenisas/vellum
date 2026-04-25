"""Integration tests for /api/models, /api/chat, /api/detect, /api/strip."""

from __future__ import annotations


async def test_models_endpoint_lists_known_providers(client):
    resp = await client.get("/api/models")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Three known buckets — all present, may be empty if no api keys.
    assert "google" in data
    assert "minimax" in data
    assert "bedrock" in data


async def test_chat_returns_watermarked_text(client):
    resp = await client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["watermarked"] is True
    assert data["raw_text"]
    assert data["text"] != data["raw_text"]
    assert data["provider"] == "fixture"


async def test_detect_finds_watermark(client):
    chat_resp = await client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )
    text = chat_resp.json()["text"]

    resp = await client.post("/api/detect", json={"text": text})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["watermark"]["watermarked"] is True
    assert data["watermark"]["valid_count"] >= 1


async def test_strip_returns_clean_text(client):
    chat_resp = await client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "hi again"}]},
    )
    chat_data = chat_resp.json()
    watermarked = chat_data["text"]
    raw = chat_data["raw_text"]

    resp = await client.post("/api/strip", json={"text": watermarked})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["stripped"] == raw
    assert data["removed"] >= 0


async def test_chat_can_disable_watermark(client):
    resp = await client.post(
        "/api/chat",
        json={
            "messages": [{"role": "user", "content": "no watermark please"}],
            "watermark": False,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["watermarked"] is False
    assert data["text"] == data["raw_text"]
