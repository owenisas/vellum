"""Demo scenario + reset endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from vellum.auth.ecdsa import generate_keypair, hash_text, sign_hash
from vellum.auth.permissions import Scope, require_permission
from vellum.models import DemoScenarioResponse, ResetResponse
from vellum.models.chat import WatermarkInfo
from vellum.providers import GenerateRequest

from .deps import (
    get_chain_repo,
    get_chat_service,
    get_company_repo,
    get_response_repo,
    get_signing_service,
    get_watermark_service,
)

router = APIRouter(prefix="/api/demo", tags=["demo"])


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
