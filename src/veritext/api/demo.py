"""Demo-mode endpoints — friction-free identity bootstrap for live demos.

These endpoints exist to make a public demo work in one click:
- /api/demo/identity:       describe the running mode
- /api/demo/auto-register:  allocate a fresh issuer_id + register a company
                            for a browser-generated wallet, no admin_secret needed
- /api/demo/sample-prompts: a curated list of prompts the demo UI can suggest

When `demo_mode != live` these endpoints respond 404 — they only exist for demos.
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/demo", tags=["demo"])


class AutoRegisterRequest(BaseModel):
    eth_address: str
    name: str | None = None


class AutoRegisterResponse(BaseModel):
    issuer_id: int
    name: str
    eth_address: str
    public_key_hex: str
    current_key_id: int = 1


@router.get("/identity")
async def demo_identity(request: Request) -> dict:
    settings = request.app.state.settings
    return {
        "auth0_enabled": settings.auth0_enabled(),
        "demo_mode": settings.demo_mode.value,
        "chain_backend": settings.chain_backend.value,
        "anchor_strategy": settings.anchor_strategy.value,
        "providers_available": _list_providers_available(request),
    }


@router.post("/auto-register", response_model=AutoRegisterResponse)
async def auto_register(request: Request, body: AutoRegisterRequest) -> AutoRegisterResponse:
    """Allocate a fresh 12-bit issuer_id and register a company.

    Requires *no* admin_secret. Only enabled in demo_mode=live.
    Idempotent on eth_address: returns the existing record if one already exists.
    """
    settings = request.app.state.settings
    if settings.demo_mode.value != "live":
        raise HTTPException(status_code=404, detail="demo endpoints disabled")

    repo = request.app.state.company_repo
    existing = await repo.get_by_address(body.eth_address)
    if existing:
        return AutoRegisterResponse(
            issuer_id=existing["issuer_id"],
            name=existing["name"],
            eth_address=existing["eth_address"],
            public_key_hex=existing["public_key_hex"],
            current_key_id=existing.get("current_key_id", 1),
        )

    # Allocate a fresh issuer_id in [100, 4095].
    used = {c["issuer_id"] for c in await repo.list_all()}
    for _ in range(100):
        candidate = secrets.randbelow(3996) + 100
        if candidate not in used:
            issuer_id = candidate
            break
    else:
        raise HTTPException(status_code=503, detail="issuer_id pool exhausted (4096 max)")

    name = body.name or f"Demo-{issuer_id:04d}"
    await repo.create(
        name=name,
        issuer_id=issuer_id,
        eth_address=body.eth_address,
        public_key_hex=body.eth_address,
    )
    return AutoRegisterResponse(
        issuer_id=issuer_id,
        name=name,
        eth_address=body.eth_address,
        public_key_hex=body.eth_address,
    )


@router.get("/sample-prompts")
async def sample_prompts() -> dict:
    return {
        "prompts": [
            "In one short paragraph, explain why text provenance matters for AI-generated content.",
            "Write a 3-sentence press release announcing a fictional product called 'CipherPad'.",
            "Compose a 4-line poem about cryptographic signatures.",
            "Summarize, in 2 sentences, the difference between a watermark and a digital signature.",
            "Draft a tweet (under 200 chars) warning about misinformation and deepfakes.",
        ]
    }


def _list_providers_available(request: Request) -> list[str]:
    """Return which providers are usable right now (have credentials)."""
    settings = request.app.state.settings
    out = ["fixture"]
    if settings.llm.google_api_key:
        out.append("google")
    return out
