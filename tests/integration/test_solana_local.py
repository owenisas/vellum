import pytest

from veritext.chain.solana import SolanaChain
from veritext.config.settings import get_settings


DATA_HASH = "ab" * 32
SIGNATURE_HEX = "cd" * 65
SOLANA_SIGNATURE = "5xLocalSolanaSignature111111111111111111111111111111111"


@pytest.mark.asyncio
async def test_solana_anchor_persists_local_block(local_solana_env, db_conn, monkeypatch):
    async def fake_post_memo(self, memo_bytes):
        return SOLANA_SIGNATURE

    monkeypatch.setattr(SolanaChain, "_post_memo", fake_post_memo)
    chain = SolanaChain(settings=get_settings(), db_conn=db_conn)

    receipt = await chain.anchor(
        data_hash=DATA_HASH,
        issuer_id=42,
        signature_hex=SIGNATURE_HEX,
    )

    latest = await chain.latest()
    assert latest is not None
    assert receipt.block_num == latest.block_num == 0
    assert receipt.tx_hash == latest.tx_hash
    assert receipt.data_hash == latest.data_hash == DATA_HASH
    assert receipt.issuer_id == latest.issuer_id == 42
    assert receipt.solana_tx_signature == latest.solana_tx_signature == SOLANA_SIGNATURE


@pytest.mark.asyncio
async def test_solana_rpc_failure_falls_back_to_local_anchor(local_solana_env, db_conn, monkeypatch):
    async def fail_post_memo(self, memo_bytes):
        raise RuntimeError("rpc unavailable")

    monkeypatch.setattr(SolanaChain, "_post_memo", fail_post_memo)
    chain = SolanaChain(settings=get_settings(), db_conn=db_conn)

    receipt = await chain.anchor(
        data_hash="ef" * 32,
        issuer_id=7,
        signature_hex=SIGNATURE_HEX,
    )

    latest = await chain.latest()
    assert latest is not None
    assert receipt.tx_hash == latest.tx_hash
    assert len(receipt.tx_hash) == 64
    assert receipt.solana_tx_signature is None
    assert latest.solana_tx_signature is None
