"""Chat & watermark endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from vellum.auth.jwt import get_current_user
from vellum.auth.permissions import Scope, require_permission
from vellum.models.chat import (
    ApplyResponse,
    ChatRequest,
    ChatResponse,
    DetectResponse,
    ModelsResponse,
    StripRequest,
    StripResponse,
    TextRequest,
    WatermarkInfo,
)

from .deps import get_chat_service, get_watermark_service

router = APIRouter(prefix="/api", tags=["chat"])


@router.get("/models", response_model=ModelsResponse)
async def list_models(chat=Depends(get_chat_service)) -> ModelsResponse:
    return chat.list_models()


@router.post(
    "/chat",
    response_model=ChatResponse,
    dependencies=[Depends(require_permission(Scope.CHAT_INVOKE))],
)
async def chat(req: ChatRequest, svc=Depends(get_chat_service)) -> ChatResponse:
    return await svc.generate(req)


@router.post("/detect", response_model=DetectResponse)
async def detect(req: TextRequest, wm=Depends(get_watermark_service)) -> DetectResponse:
    result = wm.detect(req.text)
    return DetectResponse(
        text=req.text,
        watermark=WatermarkInfo(
            watermarked=result.watermarked,
            tag_count=result.tag_count,
            valid_count=result.valid_count,
            invalid_count=result.invalid_count,
            payloads=[p.to_dict() for p in result.payloads],
        ),
    )


@router.post(
    "/strip",
    response_model=StripResponse,
    dependencies=[Depends(get_current_user)],
)
async def strip(req: StripRequest, wm=Depends(get_watermark_service)) -> StripResponse:
    stripped = wm.strip(req.text)
    return StripResponse(
        text=req.text,
        stripped=stripped,
        removed=len(req.text) - len(stripped),
    )


@router.post(
    "/apply",
    response_model=ApplyResponse,
    dependencies=[Depends(get_current_user)],
)
async def apply_watermark(
    req: TextRequest, wm=Depends(get_watermark_service)
) -> ApplyResponse:
    watermarker = wm.watermarker_for(req.wm_params)
    watermarked = watermarker.apply(req.text)
    return ApplyResponse(
        text=req.text,
        watermarked=watermarked,
        payload_hex=f"0x{watermarker.payload64:016x}",
    )
