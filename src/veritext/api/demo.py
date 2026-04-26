from __future__ import annotations

from fastapi import APIRouter, Request


router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/identity")
async def demo_identity(request: Request) -> dict:
    settings = request.app.state.settings
    return {
        "auth0_enabled": settings.auth0_enabled(),
        "demo_mode": settings.demo_mode.value,
        "chain_backend": settings.chain_backend.value,
        "anchor_strategy": settings.anchor_strategy.value,
    }
