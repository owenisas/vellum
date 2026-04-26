"""ChatService — generate text + apply watermark."""

from __future__ import annotations

from veritext.providers import GenerateRequest, ProviderRouter
from veritext.models.chat import ChatRequest, ChatResponse, WatermarkParams

from .watermark_service import WatermarkService


class ChatService:
    def __init__(
        self,
        *,
        provider_router: ProviderRouter,
        watermark_service: WatermarkService,
        injection_mode: str = "whitespace",
    ) -> None:
        self._router = provider_router
        self._wm = watermark_service
        self._injection_mode = injection_mode

    async def generate(self, req: ChatRequest) -> ChatResponse:
        gen_req = GenerateRequest(prompt=req.prompt, model=req.model)
        try:
            res = await self._router.generate(provider=req.provider, request=gen_req)
        except Exception as exc:
            return ChatResponse(
                text="",
                raw_text="",
                watermarked=False,
                model=req.model,
                provider=req.provider,
                error=str(exc),
            )
        raw_text = res.text
        watermarked = False
        text = raw_text
        if req.watermark and raw_text:
            params = req.watermark_params or WatermarkParams()
            text = self._wm.apply(
                raw_text,
                issuer_id=params.issuer_id,
                model_id=params.model_id,
                model_version_id=params.model_version_id,
                key_id=params.key_id,
                repeat_interval_tokens=params.repeat_interval_tokens,
                injection_mode=self._injection_mode,
            )
            watermarked = text != raw_text
        return ChatResponse(
            text=text,
            raw_text=raw_text,
            watermarked=watermarked,
            model=res.model,
            provider=res.provider,
            usage=res.usage,
            thinking=res.thinking,
        )
