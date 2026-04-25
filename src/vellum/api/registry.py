"""Anchor / verify / proof endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from vellum.auth.permissions import Scope, require_permission
from vellum.models import (
    AnchorRequest,
    AnchorResponse,
    ProofByTextRequest,
    ProofResponse,
    ProofSpecResponse,
    VerifyRequest,
    VerifyResponse,
)
from vellum.services.signing_service import SignatureMismatchError

from .deps import get_anchor_service

router = APIRouter(prefix="/api", tags=["registry"])


@router.post(
    "/anchor",
    response_model=AnchorResponse,
    dependencies=[Depends(require_permission(Scope.ANCHOR_CREATE))],
)
async def anchor(req: AnchorRequest, svc=Depends(get_anchor_service)) -> AnchorResponse:
    try:
        return await svc.anchor(req)
    except SignatureMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/verify", response_model=VerifyResponse)
async def verify(req: VerifyRequest, svc=Depends(get_anchor_service)) -> VerifyResponse:
    return await svc.verify(req.text)


@router.post("/proof/text", response_model=ProofResponse)
async def proof_by_text(
    req: ProofByTextRequest, svc=Depends(get_anchor_service)
) -> ProofResponse:
    return await svc.proof_by_text(req.text)


@router.get("/proof/tx/{tx_hash}", response_model=ProofResponse)
async def proof_by_tx(tx_hash: str, svc=Depends(get_anchor_service)) -> ProofResponse:
    return await svc.proof_by_tx(tx_hash)


@router.get("/proof/spec", response_model=ProofSpecResponse)
async def proof_spec() -> ProofSpecResponse:
    return ProofSpecResponse()
