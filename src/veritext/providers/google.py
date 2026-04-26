"""Google (Gemma) provider via google-generativeai."""

from __future__ import annotations

from .base import GenerateRequest, GenerateResult


class GoogleProvider:
    name = "google"

    def __init__(self, api_key: str, *, genwatermark_enabled: bool = False) -> None:
        self._api_key = api_key
        self._genwatermark_enabled = genwatermark_enabled
        self._client = None

    async def is_available(self) -> bool:
        if not self._api_key:
            return False
        try:
            import google.generativeai as genai  # noqa: F401
        except ImportError:
            return False
        return True

    async def _ensure_client(self):
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=self._api_key)
            self._client = genai
        return self._client

    async def generate(self, request: GenerateRequest) -> GenerateResult:
        client = await self._ensure_client()
        model = client.GenerativeModel(request.model or "gemma-3-12b-it")
        # SynthID gen-time tilting would be wired here when accessible via the
        # SDK. Until then, generation is unmodified — the post-hoc Unicode tag
        # in `packages/watermark` remains the primary defense.
        resp = await model.generate_content_async(request.prompt)
        text = resp.text or ""
        return GenerateResult(
            text=text,
            model=request.model,
            provider="google",
            usage={
                "input_tokens": getattr(resp.usage_metadata, "prompt_token_count", 0)
                if hasattr(resp, "usage_metadata") else 0,
                "output_tokens": getattr(resp.usage_metadata, "candidates_token_count", 0)
                if hasattr(resp, "usage_metadata") else 0,
            },
        )

    async def list_models(self) -> list[dict]:
        if not await self.is_available():
            return []
        return [
            {"id": "gemma-3-12b-it", "name": "Gemma 3 12B Instruct", "provider": "google"},
            {"id": "gemma-3-27b-it", "name": "Gemma 3 27B Instruct", "provider": "google"},
        ]
