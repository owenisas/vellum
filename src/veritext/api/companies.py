from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from veritext.auth.jwt import AuthClaims
from veritext.models.company import (
    CompanyResponse,
    CreateCompanyRequest,
    KeyHistoryEntry,
    RotateKeyRequest,
    RotateKeyResponse,
)
from .deps import get_claims, require_scopes


router = APIRouter(prefix="/api", tags=["companies"])


@router.post("/companies", response_model=CompanyResponse)
async def create_company(
    request: Request,
    body: CreateCompanyRequest,
    claims: Annotated[AuthClaims, Depends(get_claims)],
) -> CompanyResponse:
    settings = request.app.state.settings
    if settings.auth0_enabled():
        if "company:create" not in claims.scopes:
            raise HTTPException(status_code=403, detail="missing scope company:create")
    elif settings.demo_mode.value == "live":
        # Demo mode: admin_secret optional. Public demos should not require a secret.
        pass
    else:
        if body.admin_secret != settings.registry_admin_secret:
            raise HTTPException(status_code=403, detail="invalid admin_secret")

    repo = request.app.state.company_repo
    cid = await repo.create(
        name=body.name,
        issuer_id=body.issuer_id,
        eth_address=body.eth_address,
        public_key_hex=body.public_key_hex,
    )
    company = await repo.get_by_issuer(body.issuer_id)
    assert company is not None
    return _company_response(company, [])


@router.get("/companies", response_model=list[CompanyResponse])
async def list_companies(request: Request) -> list[CompanyResponse]:
    repo = request.app.state.company_repo
    key_repo = request.app.state.key_repo
    out: list[CompanyResponse] = []
    for c in await repo.list_all():
        keys = await key_repo.list_for_issuer(c["issuer_id"])
        out.append(_company_response(c, keys))
    return out


@router.post("/companies/{issuer_id}/rotate-key", response_model=RotateKeyResponse)
async def rotate_key(
    request: Request,
    issuer_id: int,
    body: RotateKeyRequest,
    _claims: Annotated[AuthClaims, Depends(require_scopes("company:rotate_key"))],
) -> RotateKeyResponse:
    repo = request.app.state.key_repo
    company_repo = request.app.state.company_repo
    if not await company_repo.get_by_issuer(issuer_id):
        raise HTTPException(status_code=404, detail=f"issuer {issuer_id} not found")
    old_id, new_id, grace = await repo.rotate(
        issuer_id=issuer_id,
        new_eth_address=body.new_eth_address,
        new_public_key_hex=body.new_public_key_hex,
        grace_period_days=body.grace_period_days,
    )
    return RotateKeyResponse(
        issuer_id=issuer_id,
        old_key_id=old_id,
        new_key_id=new_id,
        grace_until=grace,
    )


def _company_response(c: dict, keys: list) -> CompanyResponse:
    return CompanyResponse(
        id=c["id"],
        name=c["name"],
        issuer_id=c["issuer_id"],
        eth_address=c["eth_address"],
        public_key_hex=c["public_key_hex"],
        current_key_id=c.get("current_key_id", 1),
        key_history=[
            KeyHistoryEntry(
                key_id=k["key_id"],
                eth_address=k["eth_address"],
                public_key_hex=k["public_key_hex"],
                active_from=k["active_from"],
                active_until=k.get("active_until"),
            )
            for k in keys
        ],
        active=bool(c["active"]),
        created_at=c["created_at"],
    )
