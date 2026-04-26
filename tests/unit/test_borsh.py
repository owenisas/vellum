"""Phase 7 / improvement #13: Borsh memo round-trip."""

import os

from veritext.chain.borsh_schema import MemoV2, decode_memo, encode_memo


def test_memo_round_trip_no_root():
    m = MemoV2(
        data_hash=os.urandom(32),
        issuer_id=42,
        sig_prefix=os.urandom(20),
        timestamp_unix=1_700_000_000,
    )
    decoded = decode_memo(encode_memo(m))
    assert decoded.data_hash == m.data_hash
    assert decoded.issuer_id == m.issuer_id
    assert decoded.sig_prefix == m.sig_prefix
    assert decoded.timestamp_unix == m.timestamp_unix
    assert decoded.merkle_root is None


def test_memo_round_trip_with_root():
    m = MemoV2(
        data_hash=os.urandom(32),
        issuer_id=7,
        sig_prefix=os.urandom(20),
        timestamp_unix=1_700_000_000,
        merkle_root=os.urandom(32),
    )
    decoded = decode_memo(encode_memo(m))
    assert decoded.merkle_root == m.merkle_root


def test_memo_size_under_byte_limits():
    m = MemoV2(
        data_hash=os.urandom(32),
        issuer_id=42,
        sig_prefix=os.urandom(20),
        timestamp_unix=1_700_000_000,
        merkle_root=os.urandom(32),
    )
    encoded = encode_memo(m)
    # Solana memo program max: 566 bytes (per CU). Our memo is well under.
    assert len(encoded) < 100
