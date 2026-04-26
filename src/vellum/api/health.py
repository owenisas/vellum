"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from vellum.config import AppSettings, ChainBackendType
from vellum.models import HealthResponse

from .deps import get_anchor_service, get_settings

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
async def health(
    settings: AppSettings = Depends(get_settings),
    anchor=Depends(get_anchor_service),
) -> HealthResponse:
    chain_status = await anchor.chain_status()
    return HealthResponse(
        status="ok",
        demo_mode=settings.demo_mode.value,
        chain_backend=settings.chain_backend.value,
        solana_cluster=(
            settings.solana.solana_cluster
            if settings.chain_backend == ChainBackendType.SOLANA
            else None
        ),
        auth0_enabled=settings.auth.enabled,
        google_api_key_configured=bool(settings.llm.google_api_key),
        minimax_api_key_configured=bool(settings.llm.minimax_api_key),
        chain={
            "length": chain_status["length"],
            "valid": chain_status["valid"],
            "message": chain_status["message"],
        },
    )
