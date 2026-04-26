"""
Signing service — verifies signatures over the canonical bundle hash, with
EIP-712 primary and EIP-191 fallback. Resolves the correct company key based
on the chain timestamp (key rotation history awareness — improvement #15).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from veritext.auth.ecdsa import (
    TypedDataMessage,
    recover_address_eip191,
    recover_address_eip712,
)
from veritext.db.repositories import CompanyRepo, KeyRotationRepo


class SigningError(Exception):
    pass


class SigningService:
    def __init__(self, *, company_repo: CompanyRepo, key_repo: KeyRotationRepo) -> None:
        self._companies = company_repo
        self._keys = key_repo

    async def verify_anchor(
        self,
        *,
        text: str,
        issuer_id: int,
        signature_hex: str,
        sig_scheme: str,
        timestamp: int | None = None,
        bundle_nonce_hex: str | None = None,
        verification_time_iso: str | None = None,
    ) -> tuple[str, str]:
        """
        Verify a signature for an anchor request. Returns (text_hash_hex,
        recovered_eth_address). Raises SigningError on failure.
        """
        company = await self._companies.get_by_issuer(issuer_id)
        if not company:
            raise SigningError(f"unknown issuer {issuer_id}")

        text_hash_hex = hashlib.sha256(text.encode("utf-8")).hexdigest()

        if sig_scheme == "eip712":
            if not timestamp or not bundle_nonce_hex:
                raise SigningError("eip712 requires timestamp + bundle_nonce_hex")
            nonce_bytes = bytes.fromhex(bundle_nonce_hex.removeprefix("0x"))
            if len(nonce_bytes) != 32:
                raise SigningError("bundle_nonce must be 32 bytes")
            msg = TypedDataMessage(
                text_hash=bytes.fromhex(text_hash_hex),
                issuer_id=issuer_id,
                timestamp=timestamp,
                bundle_nonce=nonce_bytes,
            )
            recovered = recover_address_eip712(msg, signature_hex)
        elif sig_scheme == "eip191_personal_sign":
            recovered = recover_address_eip191("0x" + text_hash_hex, signature_hex)
        else:
            raise SigningError(f"unknown sig_scheme {sig_scheme}")

        # Look up the company key that was active at verification_time_iso
        # (defaults to now). This honors rotation grace periods.
        check_iso = verification_time_iso or datetime.now(timezone.utc).isoformat(timespec="seconds")
        key = await self._keys.find_active_key_at(issuer_id, check_iso)
        expected_addresses = []
        if key:
            expected_addresses.append(key["eth_address"].lower())
        expected_addresses.append(company["eth_address"].lower())  # fallback

        if recovered.lower() not in expected_addresses:
            raise SigningError(
                f"signature does not match issuer {issuer_id}: "
                f"recovered={recovered}, expected one of {expected_addresses}"
            )
        return text_hash_hex, recovered
