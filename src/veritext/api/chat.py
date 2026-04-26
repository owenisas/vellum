from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from veritext.auth.jwt import AuthClaims
from veritext.models.chat import (
    ApplyRequest,
    ApplyResponse,
    ChatRequest,
    ChatResponse,
    DetectRequest,
    DetectResponse,
    ModelEntry,
    ModelsResponse,
    StripRequest,
    StripResponse,
)
from .deps import get_claims, require_scopes


router = APIRouter(prefix="/api", tags=["chat"])


@router.get("/models", response_model=ModelsResponse)
async def list_models(request: Request) -> ModelsResponse:
    router_obj = request.app.state.provider_router
    models = await router_obj.list_all_models()
    return ModelsResponse(models=[ModelEntry(**m) for m in models])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    body: ChatRequest,
    _claims: Annotated[AuthClaims, Depends(require_scopes("chat:invoke"))],
) -> ChatResponse:
    chat_service = request.app.state.chat_service
    return await chat_service.generate(body)


@router.post("/apply", response_model=ApplyResponse)
async def apply_watermark(request: Request, body: ApplyRequest) -> ApplyResponse:
    wm_service = request.app.state.watermark_service
    params = body.watermark_params
    if params is None:
        text = body.text
    else:
        text = wm_service.apply(
            body.text,
            issuer_id=params.issuer_id,
            model_id=params.model_id,
            model_version_id=params.model_version_id,
            key_id=params.key_id,
            repeat_interval_tokens=params.repeat_interval_tokens,
        )
    return ApplyResponse(text=body.text, watermarked_text=text)


@router.post("/detect", response_model=DetectResponse)
async def detect_watermark(request: Request, body: DetectRequest) -> DetectResponse:
    wm_service = request.app.state.watermark_service
    res = wm_service.detect(body.text)
    return DetectResponse(
        watermarked=res.present,
        tag_count=res.unicode["tag_count"],
        valid_count=res.unicode["valid_count"],
        invalid_count=res.unicode["invalid_count"],
        payloads=res.payloads,
        statistical=res.statistical,
    )


@router.post("/strip", response_model=StripResponse)
async def strip_watermark(request: Request, body: StripRequest) -> StripResponse:
    wm_service = request.app.state.watermark_service
    res_before = wm_service.detect(body.text)
    stripped = wm_service.strip(body.text)
    return StripResponse(text=stripped, stripped_count=res_before.unicode["tag_count"])
