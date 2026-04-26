"""Canonical SQL schema. Used by `init_db` and as reference for migrations."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    issuer_id       INTEGER NOT NULL UNIQUE,
    eth_address     TEXT    NOT NULL UNIQUE,
    public_key_hex  TEXT    NOT NULL,
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS responses (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    sha256_hash      TEXT    NOT NULL,
    issuer_id        INTEGER NOT NULL,
    signature_hex    TEXT    NOT NULL,
    raw_text         TEXT    NOT NULL,
    watermarked_text TEXT    NOT NULL,
    metadata_json    TEXT    NOT NULL DEFAULT '{}',
    created_at       TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (issuer_id) REFERENCES companies(issuer_id)
);
CREATE INDEX IF NOT EXISTS idx_responses_hash ON responses(sha256_hash);

CREATE TABLE IF NOT EXISTS chain_blocks (
    block_num             INTEGER PRIMARY KEY AUTOINCREMENT,
    prev_hash             TEXT    NOT NULL,
    tx_hash               TEXT    NOT NULL UNIQUE,
    data_hash             TEXT    NOT NULL,
    issuer_id             INTEGER NOT NULL,
    signature_hex         TEXT    NOT NULL,
    payload_json          TEXT    NOT NULL DEFAULT '{}',
    timestamp             TEXT    NOT NULL DEFAULT (datetime('now')),
    solana_tx_signature   TEXT    DEFAULT NULL
);
CREATE INDEX IF NOT EXISTS idx_chain_data_hash ON chain_blocks(data_hash);
CREATE INDEX IF NOT EXISTS idx_chain_solana_tx ON chain_blocks(solana_tx_signature);
"""
