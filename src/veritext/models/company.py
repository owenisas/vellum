from __future__ import annotations

from pydantic import BaseModel, Field


class CreateCompanyRequest(BaseModel):
    name: str
    issuer_id: int
    eth_address: str
    public_key_hex: str
    admin_secret: str | None = None  # required when Auth0 disabled


class KeyHistoryEntry(BaseModel):
    key_id: int
    eth_address: str
    public_key_hex: str
    active_from: str  # ISO timestamp
    active_until: str | None = None


class CompanyResponse(BaseModel):
    id: int
    name: str
    issuer_id: int
    eth_address: str
    public_key_hex: str
    current_key_id: int
    key_history: list[KeyHistoryEntry] = Field(default_factory=list)
    active: bool
    created_at: str


class RotateKeyRequest(BaseModel):
    new_eth_address: str
    new_public_key_hex: str
    grace_period_days: int = 14


class RotateKeyResponse(BaseModel):
    issuer_id: int
    old_key_id: int
    new_key_id: int
    grace_until: str
