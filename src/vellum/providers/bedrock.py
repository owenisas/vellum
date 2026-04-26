"""AWS Bedrock provider — Converse API."""

from __future__ import annotations

import asyncio
import logging

from .base import GenerateRequest, GenerateResponse

logger = logging.getLogger(__name__)


BEDROCK_MODELS = [
    {"id": "anthropic.claude-sonnet-4-6", "name": "Claude Sonnet 4.6"},
    {"id": "anthropic.claude-opus-4-6-v1", "name": "Claude Opus 4.6"},
    {"id": "anthropic.claude-3-5-sonnet-20241022-v2:0", "name": "Claude 3.5 Sonnet"},
    {"id": "deepseek.v3.2", "name": "DeepSeek V3.2"},
    {"id": "amazon.nova-pro-v1:0", "name": "Nova Pro"},
    {"id": "amazon.nova-lite-v1:0", "name": "Nova Lite"},
]


class BedrockProvider:
    """Available when boto3 is installed and AWS creds are configured."""

    def __init__(self, region: str = "us-east-1") -> None:
        self.region = region
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        try:
            import boto3  # type: ignore[import-not-found]

            self._client = boto3.client("bedrock-runtime", region_name=self.region)
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"bedrock client unavailable: {exc}") from exc
        return self._client

    @property
    def provider_name(self) -> str:
        return "bedrock"

    @property
    def available_models(self) -> list[dict[str, str]]:
        return [{**m, "provider": "bedrock"} for m in BEDROCK_MODELS]

    @staticmethod
    def _convert_messages(messages: list[dict]) -> list[dict]:
        out: list[dict] = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "system":
                continue
            content = msg.get("content")
            if isinstance(content, str):
                blocks = [{"text": content}]
            elif isinstance(content, list):
                blocks = [
                    {"text": (i.get("text", "") if isinstance(i, dict) else str(i))}
                    for i in content
                ]
            else:
                blocks = [{"text": str(content) if content else ""}]
            out.append({"role": role, "content": blocks})
        return out

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        try:
            client = self._ensure_client()
        except RuntimeError as exc:
            return GenerateResponse(provider="bedrock", model=request.model, error=str(exc))

        messages = self._convert_messages(request.messages)

        def _call():
            return client.converse(
                modelId=request.model,
                messages=messages,
                system=[{"text": request.system}] if request.system else [],
                inferenceConfig={
                    "maxTokens": request.max_tokens,
                    "temperature": request.temperature,
                },
            )

        try:
            resp = await asyncio.to_thread(_call)
        except Exception as exc:  # pragma: no cover
            logger.warning("bedrock provider failure: %s", exc)
            return GenerateResponse(provider="bedrock", model=request.model, error=str(exc))

        text = ""
        try:
            blocks = resp["output"]["message"]["content"]
            for b in blocks:
                if "text" in b:
                    text += b["text"]
        except (KeyError, TypeError):  # pragma: no cover
            pass

        usage = resp.get("usage", {}) or {}
        return GenerateResponse(
            text=text,
            thinking="",
            model=request.model,
            provider="bedrock",
            usage={
                "input_tokens": int(usage.get("inputTokens", 0) or 0),
                "output_tokens": int(usage.get("outputTokens", 0) or 0),
            },
        )
