"""
Optional AES-128-CCM encryption for watermark payloads (improvement #7).

When `payload_visibility=encrypted`, the 8-byte raw payload is encrypted to a
slightly larger ciphertext + nonce + tag bundle. The result is encoded as
multiple zero-width tags (since each tag is exactly 64 bits).

Lazy-imports `cryptography` so the package remains usable in plaintext mode
without the dep.
"""

from __future__ import annotations

import os


CCM_NONCE_BYTES = 12
CCM_TAG_BYTES = 8
ENCRYPTED_PAYLOAD_BYTES = 8 + CCM_NONCE_BYTES + CCM_TAG_BYTES  # 28 bytes => requires multi-tag encoding


def encrypt(plaintext_8bytes: bytes, key: bytes) -> bytes:
    """
    Encrypt the 8-byte raw payload. Returns nonce(12) || ciphertext(8) || tag(8) = 28 bytes.

    The caller is responsible for fragmenting these 28 bytes into multiple
    64-bit zero-width tags (each tag carries exactly 8 bytes; sequence number
    + total are encoded by reusing the `key_id` field as a fragment index in
    encrypted mode — see Watermarker).
    """
    if len(plaintext_8bytes) != 8:
        raise ValueError("plaintext must be exactly 8 bytes")
    if len(key) != 16:
        raise ValueError("AES-128-CCM key must be 16 bytes")
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESCCM
    except ImportError as exc:
        raise RuntimeError(
            "encrypted payload mode requires `cryptography`. Install it or "
            "set PAYLOAD_VISIBILITY=plaintext."
        ) from exc
    nonce = os.urandom(CCM_NONCE_BYTES)
    aesccm = AESCCM(key, tag_length=CCM_TAG_BYTES)
    ct_with_tag = aesccm.encrypt(nonce, plaintext_8bytes, None)  # ct + tag
    return nonce + ct_with_tag


def decrypt(blob_28bytes: bytes, key: bytes) -> bytes:
    """Reverse of encrypt(). Returns the 8-byte plaintext payload."""
    if len(blob_28bytes) != ENCRYPTED_PAYLOAD_BYTES:
        raise ValueError(f"expected {ENCRYPTED_PAYLOAD_BYTES} bytes, got {len(blob_28bytes)}")
    if len(key) != 16:
        raise ValueError("AES-128-CCM key must be 16 bytes")
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESCCM
    except ImportError as exc:
        raise RuntimeError("encrypted payload mode requires `cryptography`.") from exc
    nonce = blob_28bytes[:CCM_NONCE_BYTES]
    ct_with_tag = blob_28bytes[CCM_NONCE_BYTES:]
    aesccm = AESCCM(key, tag_length=CCM_TAG_BYTES)
    return aesccm.decrypt(nonce, ct_with_tag, None)
