"""Solana on-chain verification + balance endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from vellum.config import AppSettings, ChainBackendType
from vellum.models import SolanaBalanceResponse, SolanaVerifyResponse

from .deps import get_chain_backend, get_settings

router = APIRouter(prefix="/api/solana", tags=["solana"])


def _ensure_solana(settings: AppSettings) -> None:
    if settings.chain_backend != ChainBackendType.SOLANA:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solana backend not enabled (CHAIN_BACKEND != solana)",
        )


@router.get("/verify/{tx_signature}", response_model=SolanaVerifyResponse)
async def verify_on_chain(
    tx_signature: str,
    settings: AppSettings = Depends(get_settings),
    chain=Depends(get_chain_backend),
) -> SolanaVerifyResponse:
    _ensure_solana(settings)
    if not hasattr(chain, "verify_on_chain"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Solana client not available",
        )
    result = await chain.verify_on_chain(tx_signature)
    return SolanaVerifyResponse(**result)


@router.get("/balance", response_model=SolanaBalanceResponse)
async def balance(
    settings: AppSettings = Depends(get_settings),
    chain=Depends(get_chain_backend),
) -> SolanaBalanceResponse:
    _ensure_solana(settings)
    if not hasattr(chain, "get_balance"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Solana client not available",
        )
    address, lamports = await chain.get_balance()
    return SolanaBalanceResponse(
        address=address,
        cluster=settings.solana.solana_cluster,
        balance_lamports=lamports,
        balance_sol=lamports / 1_000_000_000,
    )
