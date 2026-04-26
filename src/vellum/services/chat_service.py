"""ChatService — orchestrates LLM provider + watermark application."""

from __future__ import annotations

from vellum.models.chat import ChatRequest, ChatResponse, ModelInfo, ModelsResponse
from vellum.providers import GenerateRequest, ProviderRouter
from vellum.services.watermark_service import WatermarkService


class ChatService:
    def __init__(
        self,
        provider_router: ProviderRouter,
        watermark_service: WatermarkService,
        fixture_mode: bool = False,
    ) -> None:
        self.router = provider_router
        self.watermark = watermark_service
        self.fixture_mode = fixture_mode

    def list_models(self) -> ModelsResponse:
        models = self.router.list_models()
        return ModelsResponse(
            google=[ModelInfo(**m) for m in models.get("google", [])],
            minimax=[ModelInfo(**m) for m in models.get("minimax", [])],
            bedrock=[ModelInfo(**m) for m in models.get("bedrock", [])],
        )

    async def generate(self, request: ChatRequest) -> ChatResponse:
        provider = "fixture" if self.fixture_mode else (request.provider or self.router.settings.default_provider.value)
        model = request.model or ("fixture-default" if provider == "fixture" else self.router.settings.default_model)
        gen_req = GenerateRequest(
            model=model,
            messages=[m.model_dump() for m in request.messages],
            system=request.system,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )
        result = await self.router.generate(provider, gen_req)
        if result.error:
            return ChatResponse(
                error=result.error,
                model=result.model,
                provider=result.provider,
            )

        raw_text = result.text
        raw_thinking = result.thinking
        watermarked_text = raw_text
        watermarked_thinking = raw_thinking
        applied = False
        if request.watermark and raw_text:
            watermarked_text = self.watermark.apply(raw_text, request.wm_params)
            applied = watermarked_text != raw_text
        if request.watermark and raw_thinking:
            watermarked_thinking = self.watermark.apply(raw_thinking, request.wm_params)
            applied = applied or watermarked_thinking != raw_thinking

        return ChatResponse(
            text=watermarked_text,
            raw_text=raw_text,
            thinking=watermarked_thinking,
            raw_thinking=raw_thinking,
            watermarked=applied,
            model=result.model,
            provider=result.provider,
            usage=result.usage,
        )
