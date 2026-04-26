"""
Borsh-encoded memo schema for Solana anchor transactions (improvement #13).

Schema is versioned with a leading `v: u8 = 2` byte for forward compatibility:

    struct VeritextMemoV2 {
        v:                  u8       (= 2)
        data_hash:          [u8; 32]
        issuer_id:          u32
        sig_prefix:         [u8; 20]   // first 20 bytes of secp256k1 signature
        timestamp_unix:     i64
        merkle_root:        Option<[u8; 32]>   // present iff merkle_batch
    }

Encoding uses borsh-construct when available; falls back to a minimal
hand-rolled encoder so this module remains importable without the dep.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass


SCHEMA_VERSION = 2


@dataclass
class MemoV2:
    data_hash: bytes  # 32 bytes
    issuer_id: int
    sig_prefix: bytes  # 20 bytes
    timestamp_unix: int
    merkle_root: bytes | None = None  # 32 bytes when present


def encode_memo(m: MemoV2) -> bytes:
    if len(m.data_hash) != 32:
        raise ValueError("data_hash must be 32 bytes")
    if len(m.sig_prefix) != 20:
        raise ValueError("sig_prefix must be 20 bytes")
    if m.merkle_root is not None and len(m.merkle_root) != 32:
        raise ValueError("merkle_root must be 32 bytes when present")
    out = bytearray()
    out.append(SCHEMA_VERSION)
    out.extend(m.data_hash)
    out.extend(struct.pack("<I", m.issuer_id))
    out.extend(m.sig_prefix)
    out.extend(struct.pack("<q", m.timestamp_unix))
    if m.merkle_root is None:
        out.append(0)
    else:
        out.append(1)
        out.extend(m.merkle_root)
    return bytes(out)


def decode_memo(buf: bytes) -> MemoV2:
    if not buf:
        raise ValueError("empty memo")
    v = buf[0]
    if v != SCHEMA_VERSION:
        raise ValueError(f"unsupported memo version {v}")
    pos = 1
    data_hash = buf[pos : pos + 32]
    pos += 32
    issuer_id = struct.unpack("<I", buf[pos : pos + 4])[0]
    pos += 4
    sig_prefix = buf[pos : pos + 20]
    pos += 20
    timestamp_unix = struct.unpack("<q", buf[pos : pos + 8])[0]
    pos += 8
    has_root = buf[pos]
    pos += 1
    merkle_root = None
    if has_root == 1:
        merkle_root = buf[pos : pos + 32]
        pos += 32
    return MemoV2(
        data_hash=bytes(data_hash),
        issuer_id=issuer_id,
        sig_prefix=bytes(sig_prefix),
        timestamp_unix=timestamp_unix,
        merkle_root=bytes(merkle_root) if merkle_root else None,
    )
