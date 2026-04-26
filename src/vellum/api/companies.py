"""Company CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from vellum.auth.jwt import Identity, get_current_user, get_optional_user
from vellum.auth.permissions import Scope, require_permission
from vellum.config import AppSettings
from vellum.models import CompanyResponse, CreateCompanyRequest, CreateCompanyResponse

from .deps import get_company_repo, get_settings, get_signing_service

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.post("", response_model=CreateCompanyResponse)
async def create_company(
    req: CreateCompanyRequest,
    settings: AppSettings = Depends(get_settings),
    identity: Identity | None = Depends(get_optional_user),
    signing=Depends(get_signing_service),
) -> CreateCompanyResponse:
    """Register a new company.

    When Auth0 is enabled, requires `company:create` scope.
    When Auth0 is disabled, accepts an `admin_secret` body field as a fallback.
    """
    if settings.auth.enabled:
        if identity is None or Scope.COMPANY_CREATE not in identity.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing required permission: company:create",
            )
    else:
        # Demo mode: allow either no auth (DEMO_IDENTITY has all perms) OR admin_secret
        if not identity or Scope.COMPANY_CREATE not in identity.permissions:
            if not signing.admin_secret_matches(req.admin_secret):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="admin_secret required",
                )

    try:
        company, private_key = await signing.register_company(
            name=req.name,
            issuer_id=req.issuer_id,
            eth_address=req.eth_address,
            public_key_hex=req.public_key_hex,
            auto_generate=req.auto_generate,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return CreateCompanyResponse(
        id=int(company["id"]),
        name=company["name"],
        issuer_id=int(company["issuer_id"]),
        eth_address=company["eth_address"],
        public_key_hex=company["public_key_hex"],
        active=bool(company.get("active", True)),
        created_at=company.get("created_at"),
        private_key_hex=private_key,
        note=(
            "Save the private_key_hex now — it is not stored on the server."
            if private_key
            else None
        ),
    )


@router.get(
    "",
    response_model=list[CompanyResponse],
    dependencies=[Depends(get_current_user)],
)
async def list_companies(repo=Depends(get_company_repo)) -> list[CompanyResponse]:
    rows = await repo.list_all()
    return [
        CompanyResponse(
            id=int(r["id"]),
            name=r["name"],
            issuer_id=int(r["issuer_id"]),
            eth_address=r["eth_address"],
            public_key_hex=r["public_key_hex"],
            active=bool(r.get("active", True)),
            created_at=r.get("created_at"),
        )
        for r in rows
    ]
