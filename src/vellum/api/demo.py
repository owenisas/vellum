"""Demo scenario + reset endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from vellum.auth.ecdsa import (
    generate_keypair,
    hash_text,
    public_key_to_address,
    sign_hash,
)
from vellum.auth.permissions import Scope, require_permission
from vellum.config import AppSettings
from vellum.config.enums import ChainBackendType, DemoMode
from vellum.models import DemoScenarioResponse, ResetResponse
from vellum.models.chat import WatermarkInfo
from vellum.providers import GenerateRequest

from .deps import (
    get_chain_repo,
    get_chat_service,
    get_company_repo,
    get_response_repo,
    get_settings,
    get_signing_service,
    get_watermark_service,
)

router = APIRouter(prefix="/api/demo", tags=["demo"])


class DemoIdentityResponse(BaseModel):
    auth0_enabled: bool
    demo_mode: DemoMode
    chain_backend: ChainBackendType
    anchor_strategy: str = "per_response"
    providers_available: list[str] = Field(default_factory=list)


class AutoRegisterRequest(BaseModel):
    eth_address: str
    public_key_hex: str
    name: str | None = None


class AutoRegisterResponse(BaseModel):
    issuer_id: int
    name: str
    eth_address: str
    public_key_hex: str
    current_key_id: int = 1


@router.get("/identity", response_model=DemoIdentityResponse)
async def identity(
    settings: AppSettings = Depends(get_settings),
    chat=Depends(get_chat_service),
) -> DemoIdentityResponse:
    models = chat.list_models()
    providers = [
        provider
        for provider in ("google", "minimax", "bedrock")
        if getattr(models, provider, [])
    ]
    if "fixture" not in providers:
        providers.append("fixture")
    return DemoIdentityResponse(
        auth0_enabled=settings.auth.enabled,
        demo_mode=settings.demo_mode,
        chain_backend=settings.chain_backend,
        providers_available=providers,
    )


@router.post("/auto-register", response_model=AutoRegisterResponse)
async def auto_register(
    req: AutoRegisterRequest,
    settings: AppSettings = Depends(get_settings),
    company_repo=Depends(get_company_repo),
    signing=Depends(get_signing_service),
) -> AutoRegisterResponse:
    if settings.auth.enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo auto-registration is disabled when Auth0 is enabled.",
        )

    try:
        derived = public_key_to_address(req.public_key_hex)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if derived.lower() != req.eth_address.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="public_key_hex does not match eth_address",
        )

    existing = await company_repo.get_by_address(req.eth_address)
    if existing:
        return AutoRegisterResponse(
            issuer_id=int(existing["issuer_id"]),
            name=existing["name"],
            eth_address=existing["eth_address"],
            public_key_hex=existing["public_key_hex"],
        )

    try:
        company, _private_key = await signing.register_company(
            name=req.name or "Vellum Demo Co",
            eth_address=req.eth_address,
            public_key_hex=req.public_key_hex,
            auto_generate=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return AutoRegisterResponse(
        issuer_id=int(company["issuer_id"]),
        name=company["name"],
        eth_address=company["eth_address"],
        public_key_hex=company["public_key_hex"],
    )


@router.get("/sample-prompts")
async def sample_prompts() -> dict[str, list[str]]:
    return {
        "prompts": [
            "[demo prompt] Explain how content provenance works.",
            "[demo prompt] Explain why authenticated AI agent actions matter.",
            "[demo prompt] Explain how browser wallets prove provenance.",
        ]
    }


@router.get("/scenario", response_model=DemoScenarioResponse)
async def scenario(
    chat=Depends(get_chat_service),
    wm=Depends(get_watermark_service),
    signing=Depends(get_signing_service),
) -> DemoScenarioResponse:
    """Render an end-to-end demo: keypair → fixture text → watermark → ECDSA sign."""
    private_key, public_key, eth_address = generate_keypair()

    gen = await chat.router.generate(
        "fixture",
        GenerateRequest(
            model="fixture-default",
            messages=[
                {"role": "user", "content": "Show how Vellum proves AI text provenance."}
            ],
        ),
    )
    raw_text = gen.text
    watermarker = wm.watermarker_for(None)
    watermarked = watermarker.apply(raw_text)
    sha = hash_text(watermarked)
    sig = sign_hash(sha, private_key)
    detect_result = wm.detect(watermarked)

    return DemoScenarioResponse(
        company={
            "name": "Demo Co",
            "private_key_hex": private_key,
            "public_key_hex": public_key,
            "eth_address": eth_address,
        },
        text=raw_text,
        watermarked_text=watermarked,
        watermark=WatermarkInfo(
            watermarked=detect_result.watermarked,
            tag_count=detect_result.tag_count,
            valid_count=detect_result.valid_count,
            invalid_count=detect_result.invalid_count,
            payloads=[p.to_dict() for p in detect_result.payloads],
        ),
        signature_hex=sig,
        sha256_hash=sha,
        instructions=[
            "POST the watermarked text + signature + issuer_id to /api/anchor",
            "GET /api/verify with the same text to confirm provenance",
            "GET /api/proof/text to retrieve the proof bundle",
        ],
    )


@router.post(
    "/reset",
    response_model=ResetResponse,
    dependencies=[Depends(require_permission(Scope.ADMIN_RESET))],
)
async def reset(
    company_repo=Depends(get_company_repo),
    response_repo=Depends(get_response_repo),
    chain_repo=Depends(get_chain_repo),
) -> ResetResponse:
    deleted_companies = await company_repo.delete_all()
    deleted_responses = await response_repo.delete_all()
    deleted_blocks = await chain_repo.delete_all()
    return ResetResponse(
        status="ok",
        cleared={
            "companies": int(deleted_companies),
            "responses": int(deleted_responses),
            "chain_blocks": int(deleted_blocks),
        },
    )
