"""Google GenAI provider — Gemma 4 / Gemini families."""

from __future__ import annotations

import asyncio
import logging

from .base import GenerateRequest, GenerateResponse

logger = logging.getLogger(__name__)


GOOGLE_MODELS = [
    {"id": "gemma-4-31b-it", "name": "Gemma 4 31B (default)"},
    {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
    {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash"},
    {"id": "gemma-3-27b-it", "name": "Gemma 3 27B"},
]


class GoogleProvider:
    """Google GenAI SDK wrapper."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._genai = None

    def _ensure_client(self):
        if self._genai is None:
            try:
                import google.generativeai as genai  # type: ignore[import-not-found]

                genai.configure(api_key=self.api_key)
                self._genai = genai
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError("google-generativeai not installed") from exc
        return self._genai

    @property
    def provider_name(self) -> str:
        return "google"

    @property
    def available_models(self) -> list[dict[str, str]]:
        return [{**m, "provider": "google"} for m in GOOGLE_MODELS]

    @staticmethod
    def _convert_messages(messages: list[dict]) -> list[dict]:
        out: list[dict] = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "assistant":
                role = "model"
            content = msg.get("content")
            if isinstance(content, str):
                parts = [{"text": content}]
            elif isinstance(content, list):
                parts = [
                    {"text": (item.get("text", "") if isinstance(item, dict) else str(item))}
                    for item in content
                ]
            else:
                parts = [{"text": str(content) if content is not None else ""}]
            out.append({"role": role, "parts": parts})
        return out

    @staticmethod
    def _extract_parts(resp) -> tuple[str, str]:
        try:
            candidate = resp.candidates[0]  # type: ignore[index]
            text_parts: list[str] = []
            thinking_parts: list[str] = []
            for part in candidate.content.parts:
                if getattr(part, "thought", False):
                    thinking_parts.append(getattr(part, "text", ""))
                else:
                    text_parts.append(getattr(part, "text", ""))
            return "\n".join(thinking_parts), "\n".join(text_parts)
        except Exception:  # pragma: no cover
            return "", getattr(resp, "text", "") or ""

    @staticmethod
    def _extract_usage(resp) -> dict[str, int]:
        meta = getattr(resp, "usage_metadata", None)
        if not meta:
            return {"input_tokens": 0, "output_tokens": 0}
        return {
            "input_tokens": int(getattr(meta, "prompt_token_count", 0) or 0),
            "output_tokens": int(getattr(meta, "candidates_token_count", 0) or 0),
        }

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        try:
            genai = self._ensure_client()
        except RuntimeError as exc:
            return GenerateResponse(provider="google", model=request.model, error=str(exc))

        contents = self._convert_messages(request.messages)
        config = genai.types.GenerationConfig(
            max_output_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        def _call():
            model = genai.GenerativeModel(
                model_name=request.model,
                system_instruction=request.system,
            )
            return model.generate_content(contents, generation_config=config)

        try:
            resp = await asyncio.to_thread(_call)
        except Exception as exc:  # pragma: no cover
            logger.warning("google provider failure: %s", exc)
            return GenerateResponse(provider="google", model=request.model, error=str(exc))

        thinking, text = self._extract_parts(resp)
        usage = self._extract_usage(resp)
        return GenerateResponse(
            text=text,
            thinking=thinking,
            model=request.model,
            provider="google",
            usage=usage,
        )
