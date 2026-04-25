"""Signing service — ECDSA verification and company CRUD."""

from __future__ import annotations

from vellum.auth.ecdsa import (
    generate_keypair,
    public_key_to_address,
    recover_address,
    verify_signature,
)
from vellum.db.repositories import CompanyRepository


class SignatureMismatchError(Exception):
    """Raised when a signature does not recover to the expected address."""


class SigningService:
    def __init__(
        self,
        company_repo: CompanyRepository,
        admin_secret: str = "dev-admin-secret",
    ) -> None:
        self.company_repo = company_repo
        self.admin_secret = admin_secret

    # --- Company CRUD ---

    async def register_company(
        self,
        name: str,
        issuer_id: int | None = None,
        eth_address: str | None = None,
        public_key_hex: str | None = None,
        auto_generate: bool = True,
    ) -> tuple[dict, str | None]:
        """Register a new company. Returns (company_record, optional_private_key)."""
        private_key_hex: str | None = None

        if auto_generate and not eth_address and not public_key_hex:
            private_key_hex, public_key_hex, eth_address = generate_keypair()
        elif public_key_hex and not eth_address:
            eth_address = public_key_to_address(public_key_hex)
        elif not public_key_hex or not eth_address:
            raise ValueError("Provide both public_key_hex and eth_address, or set auto_generate")

        if issuer_id is None:
            issuer_id = await self.company_repo.next_issuer_id()

        existing = await self.company_repo.get_by_address(eth_address)
        if existing:
            raise ValueError(f"Address already registered: {eth_address}")

        company = await self.company_repo.create(
            name=name,
            issuer_id=issuer_id,
            eth_address=eth_address,
            public_key_hex=public_key_hex,
        )
        return company, private_key_hex

    async def list_companies(self) -> list[dict]:
        return await self.company_repo.list_all()

    async def find_company(self, issuer_id: int) -> dict | None:
        return await self.company_repo.get_by_issuer(issuer_id)

    # --- Verification ---

    async def verify(self, data_hash: str, signature_hex: str, issuer_id: int) -> dict:
        """Verify the signature recovers to the company's registered address.

        Returns the company dict on success. Raises SignatureMismatchError otherwise.
        """
        company = await self.company_repo.get_by_issuer(issuer_id)
        if not company:
            raise PermissionError(f"Unknown issuer_id: {issuer_id}")

        if not verify_signature(data_hash, signature_hex, company["eth_address"]):
            recovered = ""
            try:
                recovered = recover_address(data_hash, signature_hex)
            except Exception:
                pass
            raise SignatureMismatchError(
                f"Signature does not match registered address. expected={company['eth_address']} recovered={recovered}"
            )

        return company

    def admin_secret_matches(self, candidate: str | None) -> bool:
        if not candidate or not self.admin_secret:
            return False
        return candidate == self.admin_secret
