"""SQLite connection with aiosqlite + schema bootstrap (Alembic-free for simplicity)."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import aiosqlite

from veritext.config import get_settings


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS companies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    issuer_id       INTEGER NOT NULL UNIQUE,
    current_key_id  INTEGER NOT NULL DEFAULT 1,
    eth_address     TEXT    NOT NULL,
    public_key_hex  TEXT    NOT NULL,
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS company_keys (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    issuer_id       INTEGER NOT NULL,
    key_id          INTEGER NOT NULL,
    eth_address     TEXT    NOT NULL,
    public_key_hex  TEXT    NOT NULL,
    active_from     TEXT    NOT NULL,
    active_until    TEXT,
    active          INTEGER NOT NULL DEFAULT 1,
    UNIQUE(issuer_id, key_id),
    FOREIGN KEY(issuer_id) REFERENCES companies(issuer_id)
);

CREATE INDEX IF NOT EXISTS idx_company_keys_issuer ON company_keys(issuer_id);

CREATE TABLE IF NOT EXISTS responses (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    sha256_hash      TEXT    NOT NULL,
    issuer_id        INTEGER NOT NULL,
    signature_hex    TEXT    NOT NULL,
    sig_scheme       TEXT    NOT NULL DEFAULT 'eip712',
    raw_text         TEXT    NOT NULL,
    watermarked_text TEXT    NOT NULL,
    metadata_json    TEXT    NOT NULL DEFAULT '{}',
    bundle_id        TEXT    NOT NULL DEFAULT '',
    created_at       TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (issuer_id) REFERENCES companies(issuer_id)
);

CREATE INDEX IF NOT EXISTS idx_responses_hash ON responses(sha256_hash);
CREATE INDEX IF NOT EXISTS idx_responses_bundle ON responses(bundle_id);

CREATE TABLE IF NOT EXISTS chain_blocks (
    block_num            INTEGER PRIMARY KEY,
    prev_hash            TEXT    NOT NULL,
    tx_hash              TEXT    NOT NULL UNIQUE,
    data_hash            TEXT    NOT NULL,
    issuer_id            INTEGER NOT NULL,
    signature_hex        TEXT    NOT NULL,
    payload_json         TEXT    NOT NULL DEFAULT '{}',
    timestamp            TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    solana_tx_signature  TEXT,
    merkle_root          TEXT,
    leaf_index           INTEGER,
    inclusion_proof_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_chain_data_hash ON chain_blocks(data_hash);
CREATE INDEX IF NOT EXISTS idx_chain_solana_sig ON chain_blocks(solana_tx_signature);
CREATE INDEX IF NOT EXISTS idx_chain_merkle_root ON chain_blocks(merkle_root);

CREATE TABLE IF NOT EXISTS pending_anchors (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    bundle_id     TEXT    NOT NULL UNIQUE,
    data_hash     TEXT    NOT NULL,
    issuer_id     INTEGER NOT NULL,
    signature_hex TEXT    NOT NULL,
    payload_json  TEXT    NOT NULL DEFAULT '{}',
    created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    promoted      INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_pending_promoted ON pending_anchors(promoted);
"""


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> aiosqlite.Connection:
        if self._conn is None:
            Path(os.path.dirname(self.path) or ".").mkdir(parents=True, exist_ok=True)
            self._conn = await aiosqlite.connect(self.path)
            self._conn.row_factory = aiosqlite.Row
            await self._conn.executescript(SCHEMA_SQL)
            await self._conn.commit()
        return self._conn

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None


async def init_db(path: str | None = None) -> Database:
    db = Database(path or get_settings().db_path)
    await db.connect()
    return db


@asynccontextmanager
async def get_db(path: str | None = None) -> AsyncIterator[aiosqlite.Connection]:
    db = await init_db(path)
    try:
        conn = await db.connect()
        yield conn
    finally:
        await db.close()
