"""Response listing endpoints (anchored LLM responses)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from vellum.models import ResponseRecord

from .deps import get_response_repo

router = APIRouter(prefix="/api/responses", tags=["responses"])


@router.get("", response_model=list[ResponseRecord])
async def list_responses(
    limit: int = 50,
    offset: int = 0,
    repo=Depends(get_response_repo),
) -> list[ResponseRecord]:
    rows = await repo.list_recent(limit=limit, offset=offset)
    return [ResponseRecord(**_row(r)) for r in rows]


@router.get("/latest", response_model=ResponseRecord)
async def latest(repo=Depends(get_response_repo)) -> ResponseRecord:
    row = await repo.latest()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No responses found"
        )
    return ResponseRecord(**_row(row))


def _row(r: dict) -> dict:
    return {
        "id": int(r["id"]),
        "sha256_hash": r["sha256_hash"],
        "issuer_id": int(r["issuer_id"]),
        "signature_hex": r["signature_hex"],
        "raw_text": r["raw_text"],
        "watermarked_text": r["watermarked_text"],
        "metadata": r.get("metadata", {}),
        "created_at": r.get("created_at", ""),
    }
