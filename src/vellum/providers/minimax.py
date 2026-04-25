"""MiniMax provider — accessed via MiniMax's Anthropic-compatible API."""

from __future__ import annotations

import asyncio
import logging

from .base import GenerateRequest, GenerateResponse

logger = logging.getLogger(__name__)


MINIMAX_MODELS = [
    {"id": "MiniMax-M2.5", "name": "MiniMax M2.5"},
    {"id": "MiniMax-M2.5-highspeed", "name": "MiniMax M2.5 Highspeed"},
    {"id": "MiniMax-M2.1", "name": "MiniMax M2.1"},
    {"id": "MiniMax-M2.1-highspeed", "name": "MiniMax M2.1 Highspeed"},
    {"id": "MiniMax-M2", "name": "MiniMax M2"},
]


class MiniMaxProvider:
    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        try:
            from anthropic import Anthropic  # type: ignore[import-not-found]

            self._client = Anthropic(api_key=self.api_key, base_url=self.base_url)
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("anthropic SDK not installed") from exc
        return self._client

    @property
    def provider_name(self) -> str:
        return "minimax"

    @property
    def available_models(self) -> list[dict[str, str]]:
        return [{**m, "provider": "minimax"} for m in MINIMAX_MODELS]

    @staticmethod
    def _convert_messages(messages: list[dict]) -> list[dict]:
        out: list[dict] = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "system":
                continue  # system message is passed separately
            content = msg.get("content")
            if isinstance(content, str):
                out.append({"role": role, "content": content})
            elif isinstance(content, list):
                # Anthropic content blocks
                parts = [
                    {"type": "text", "text": (i.get("text", "") if isinstance(i, dict) else str(i))}
                    for i in content
                ]
                out.append({"role": role, "content": parts})
            else:
                out.append({"role": role, "content": str(content) if content else ""})
        return out

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        try:
            client = self._ensure_client()
        except RuntimeError as exc:
            return GenerateResponse(provider="minimax", model=request.model, error=str(exc))

        messages = self._convert_messages(request.messages)

        def _call():
            return client.messages.create(
                model=request.model,
                system=request.system,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )

        try:
            resp = await asyncio.to_thread(_call)
        except Exception as exc:  # pragma: no cover
            logger.warning("minimax provider failure: %s", exc)
            return GenerateResponse(provider="minimax", model=request.model, error=str(exc))

        text_parts: list[str] = []
        thinking_parts: list[str] = []
        for block in getattr(resp, "content", []) or []:
            block_type = getattr(block, "type", "")
            if block_type == "thinking":
                thinking_parts.append(getattr(block, "thinking", "") or "")
            elif block_type == "text":
                text_parts.append(getattr(block, "text", "") or "")

        usage = getattr(resp, "usage", None)
        usage_dict = {
            "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
            "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        } if usage else {"input_tokens": 0, "output_tokens": 0}

        return GenerateResponse(
            text="\n".join(text_parts).strip(),
            thinking="\n".join(thinking_parts).strip(),
            model=request.model,
            provider="minimax",
            usage=usage_dict,
        )
