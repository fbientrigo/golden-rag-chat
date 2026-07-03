"""Bedrock Converse LLM provider (M4 skeleton).

Maps our ``ChatMessage`` list onto the Bedrock Converse request shape. The mapping
helpers are pure and testable; the boto3 call is guarded and never runs in the
default test suite.

Verified against AWS docs (June 2026):
- Client: ``bedrock-runtime``; operations ``converse`` / ``converse_stream``.
- ``system`` is a separate list of ``{"text": ...}`` blocks (NOT a message role).
- ``messages`` is ``[{"role": "user"|"assistant", "content": [{"text": ...}]}]``.
- ``inferenceConfig`` carries ``maxTokens`` / ``temperature`` / ``topP``.
- Response: ``output.message.content[0].text``, plus ``stopReason`` and ``usage``.
"""

from __future__ import annotations

import asyncio
from typing import Any

from golden_rag_chat.errors import ProviderNotConfiguredError
from golden_rag_chat.llm.base import ChatMessage, GenerationOptions, LLMResponse
from golden_rag_chat.retrieval.base import RetrievedSource


def to_converse_messages(messages: list[ChatMessage]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Split our messages into Converse ``messages`` and ``system`` blocks (pure)."""
    system_blocks: list[dict[str, str]] = []
    converse_messages: list[dict[str, Any]] = []
    for m in messages:
        if m.role == "system":
            system_blocks.append({"text": m.content})
        else:
            converse_messages.append({"role": m.role, "content": [{"text": m.content}]})
    return converse_messages, system_blocks


def to_inference_config(options: GenerationOptions) -> dict[str, Any]:
    return {"maxTokens": options.max_tokens, "temperature": options.temperature}


def from_converse_response(data: dict[str, Any], *, fallback_model: str | None) -> LLMResponse:
    """Map a Bedrock Converse response onto our LLMResponse (pure, testable)."""
    text = data["output"]["message"]["content"][0]["text"]
    return LLMResponse(
        text=text,
        model=fallback_model,
        usage=data.get("usage", {}),
        raw=data,
    )


class BedrockConverseLLM:
    def __init__(self, *, model_id: str | None, region: str | None, client: Any = None):
        self._model_id = model_id
        self._region = region
        self._client = client

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._model_id:
            raise ProviderNotConfiguredError("GRC_BEDROCK_MODEL_ID is not set.")
        try:
            import boto3  # noqa: PLC0415 - optional dependency
        except ImportError as exc:  # pragma: no cover
            raise ProviderNotConfiguredError(
                "boto3 is required for the bedrock_converse backend. Install the 'bedrock' extra."
            ) from exc
        self._client = boto3.client("bedrock-runtime", region_name=self._region)
        return self._client

    async def generate(
        self,
        *,
        messages: list[ChatMessage],
        sources: list[RetrievedSource],
        options: GenerationOptions,
    ) -> LLMResponse:
        client = self._ensure_client()
        converse_messages, system_blocks = to_converse_messages(messages)
        # ponytail: boto3 is sync; to_thread keeps the async event loop free
        data = await asyncio.to_thread(
            client.converse,
            modelId=options.model or self._model_id,
            messages=converse_messages,
            system=system_blocks,
            inferenceConfig=to_inference_config(options),
        )
        return from_converse_response(data, fallback_model=options.model or self._model_id)
