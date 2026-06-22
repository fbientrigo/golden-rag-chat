"""OpenRouter (OpenAI-compatible) LLM provider.

The request *construction* is implemented as a pure function (``build_payload``)
so it can be unit-tested without a network call. The HTTP client is injectable
so tests never hit the real API.

API keys come from the server environment only — never the frontend.
"""

from __future__ import annotations

from typing import Any

import httpx

from golden_rag_chat.errors import ProviderNotConfiguredError
from golden_rag_chat.llm.base import ChatMessage, GenerationOptions, LLMResponse
from golden_rag_chat.retrieval.base import RetrievedSource


def build_payload(
    *, model: str, messages: list[ChatMessage], options: GenerationOptions
) -> dict[str, Any]:
    """Build an OpenAI-compatible chat-completions payload (pure, testable)."""
    return {
        "model": options.model or model,
        "messages": [{"role": m.role, "content": m.content} for m in messages],
        "temperature": options.temperature,
        "max_tokens": options.max_tokens,
        **options.extra,
    }


class OpenRouterLLM:
    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        model: str,
        client: httpx.AsyncClient | None = None,
        site_url: str | None = None,
        app_name: str | None = None,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client = client  # ponytail: inject a mock transport in tests
        self._site_url = site_url
        self._app_name = app_name

    async def generate(
        self,
        *,
        messages: list[ChatMessage],
        sources: list[RetrievedSource],
        options: GenerationOptions,
    ) -> LLMResponse:
        if not self._api_key and self._client is None:
            raise ProviderNotConfiguredError("GRC_OPENROUTER_API_KEY is not set.")

        payload = build_payload(model=self._model, messages=messages, options=options)
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self._site_url:
            headers["HTTP-Referer"] = self._site_url
        if self._app_name:
            headers["X-Title"] = self._app_name

        client = self._client or httpx.AsyncClient(timeout=30.0)
        try:
            resp = await client.post(
                f"{self._base_url}/chat/completions", json=payload, headers=headers
            )
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise ProviderNotConfiguredError(
                    f"OpenRouter returned HTTP {e.response.status_code}"
                ) from e
            data = resp.json()
        finally:
            if self._client is None:
                await client.aclose()

        choice = data["choices"][0]["message"]["content"]
        return LLMResponse(
            text=choice,
            model=data.get("model", self._model),
            usage=data.get("usage", {}),
            raw=data,
        )
