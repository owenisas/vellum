"""Shared pytest fixtures."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio


@pytest.fixture(autouse=True)
def _set_env(monkeypatch, tmp_path):
    """Each test gets an isolated DB and disables Auth0/Solana by default."""
    db_file = tmp_path / "veritext_test.db"
    monkeypatch.setenv("DB_PATH", str(db_file))
    monkeypatch.setenv("CHAIN_BACKEND", "simulated")
    monkeypatch.setenv("ANCHOR_STRATEGY", "per_response")
    monkeypatch.setenv("AUTH0_DOMAIN", "")
    monkeypatch.setenv("LOG_FORMAT", "json")
    monkeypatch.setenv("LOG_LEVEL", "warning")
    # Reset singleton
    from veritext.config.settings import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def db_conn(tmp_path):
    from veritext.db.connection import Database

    db = Database(str(tmp_path / "veritext_test.db"))
    conn = await db.connect()
    try:
        yield conn
    finally:
        await db.close()


@pytest_asyncio.fixture
async def app_client(monkeypatch, tmp_path):
    from httpx import ASGITransport, AsyncClient

    from veritext.app import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, app


@pytest.fixture
def local_solana_env(monkeypatch, tmp_path):
    """Run Solana-mode tests against local SQLite and mocked RPC only."""
    keypair_path = tmp_path / "solana-keypair.json"
    keypair_path.write_text("[]", encoding="utf-8")
    monkeypatch.setenv("CHAIN_BACKEND", "solana")
    monkeypatch.setenv("SOLANA_KEYPAIR_PATH", str(keypair_path))
    monkeypatch.setenv("SOLANA_RPC_URL", "http://local-solana-rpc.invalid")

    from veritext.config.settings import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def solana_app_client(local_solana_env):
    from httpx import ASGITransport, AsyncClient

    from veritext.app import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, app
