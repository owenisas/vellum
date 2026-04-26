"""Company CRUD models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateCompanyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    issuer_id: int | None = None
    eth_address: str | None = None
    public_key_hex: str | None = None
    admin_secret: str | None = None  # Optional fallback when Auth0 disabled

    # If True (default), the server may generate a fresh keypair when none is provided
    auto_generate: bool = True


class CompanyResponse(BaseModel):
    id: int
    name: str
    issuer_id: int
    eth_address: str
    public_key_hex: str
    active: bool = True
    created_at: str | None = None


class CreateCompanyResponse(CompanyResponse):
    """Returned only on creation. Includes private key when auto-generated."""

    private_key_hex: str | None = None
    note: str | None = None
