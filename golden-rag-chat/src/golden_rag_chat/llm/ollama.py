"""Ollama / llama.cpp local LLM provider (later milestone, skeleton).

For local GPU/CPU inference. Security rule: Ollama must never be exposed publicly;
the FastAPI service calls it over a private/loopback address.

Ollama exposes an OpenAI-compatible endpoint at ``{base_url}/v1/chat/completions``
as well as a native ``/api/chat``. The payload builder is reused from the
OpenRouter provider since the OpenAI-compatible shape is identical.
"""

from __future__ import annotations

import httpx

from golden_rag_chat.llm.base import ChatMessage, GenerationOptions, LLMResponse
from golden_rag_chat.llm.openrouter import build_payload
from golden_rag_chat.retrieval.base import RetrievedSource


class OllamaLLM:
    def __init__(self, *, base_url: str, model: str, client: httpx.AsyncClient | None = None):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client = client

    async def generate(
        self,
        *,
        messages: list[ChatMessage],
        sources: list[RetrievedSource],
        options: GenerationOptions,
    ) -> LLMResponse:  # pragma: no cover - skeleton
        # Reference implementation sketch (kept un-executed to avoid network in tests):
        #   payload = build_payload(model=self._model, messages=messages, options=options)
        #   client = self._client or httpx.AsyncClient(base_url=self._base_url, timeout=120.0)
        #   resp = await client.post("/v1/chat/completions", json=payload)
        #   ...
        _ = build_payload  # keep the import meaningful for implementers
        raise NotImplementedError(
            "OllamaLLM.generate is a skeleton. Point it at a private Ollama endpoint "
            "and reuse build_payload for the OpenAI-compatible request."
        )
