"""Tests for the OpenRouter LLM provider (all offline — no real HTTP calls)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from golden_rag_chat.api.schemas import ChatOptions, ChatRequest
from golden_rag_chat.domains import default_registry
from golden_rag_chat.errors import ProviderNotConfiguredError
from golden_rag_chat.golden_data.contracts import Domain
from golden_rag_chat.llm.base import ChatMessage, GenerationOptions
from golden_rag_chat.llm.openrouter import OpenRouterLLM, build_payload
from golden_rag_chat.rag.local_pipeline import LocalRAGPipeline
from golden_rag_chat.retrieval.base import RetrievedSource
from golden_rag_chat.retrieval.mock import MockRetrievalProvider


def _messages() -> list[ChatMessage]:
    return [
        ChatMessage(role="system", content="You are a helpful assistant."),
        ChatMessage(role="user", content="QUESTION: What skills am I missing?"),
    ]


def _sources() -> list[RetrievedSource]:
    return [
        RetrievedSource(
            source_id="test-001",
            source_type="skill_gap",
            title="Test Source",
            uri="golden://test/001",
            text="Some evidence.",
            metadata={"domain": "apolo"},
        )
    ]


def _mock_client(response_json: dict) -> AsyncMock:
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = response_json
    client = AsyncMock(spec=httpx.AsyncClient)
    client.post = AsyncMock(return_value=resp)
    return client


# --- 1. build_payload ---


def test_openrouter_build_payload_maps_messages():
    payload = build_payload(
        model="openai/gpt-4o-mini",
        messages=_messages(),
        options=GenerationOptions(max_tokens=512),
    )
    assert payload["model"] == "openai/gpt-4o-mini"
    assert payload["messages"] == [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "QUESTION: What skills am I missing?"},
    ]
    assert payload["max_tokens"] == 512


# --- 2. successful HTTP call ---


async def test_openrouter_generate_success_with_mocked_http():
    provider = OpenRouterLLM(
        api_key=None,
        base_url="https://openrouter.ai/api/v1",
        model="openai/gpt-4o-mini",
        client=_mock_client({"choices": [{"message": {"content": "grounded answer"}}]}),
    )
    result = await provider.generate(
        messages=_messages(),
        sources=_sources(),
        options=GenerationOptions(),
    )
    assert result.text == "grounded answer"


# --- 3. missing API key ---


async def test_openrouter_generate_rejects_missing_api_key():
    provider = OpenRouterLLM(
        api_key=None,
        base_url="https://openrouter.ai/api/v1",
        model="openai/gpt-4o-mini",
        # no client injected → must raise
    )
    with pytest.raises(ProviderNotConfiguredError, match="GRC_OPENROUTER_API_KEY"):
        await provider.generate(
            messages=_messages(),
            sources=_sources(),
            options=GenerationOptions(),
        )


# --- 4. end-to-end through LocalRAGPipeline ---


async def test_chat_with_openrouter_backend_pipeline_direct():
    llm = OpenRouterLLM(
        api_key=None,
        base_url="https://openrouter.ai/api/v1",
        model="openai/gpt-4o-mini",
        client=_mock_client({"choices": [{"message": {"content": "grounded answer"}}]}),
    )
    pipeline = LocalRAGPipeline(
        retrieval=MockRetrievalProvider(),
        llm=llm,
        domains=default_registry(),
        retrieval_backend="mock",
        llm_backend="openrouter",
    )
    request = ChatRequest(
        domain=Domain.APOLO,
        user_id="test-user",
        question="What skills am I missing for data engineering?",
        context={"career_id": "uchile-ingcivil", "target_role_family": "Data & Analytics Engineering"},
        options=ChatOptions(
            retrieval_backend="mock",
            llm_backend="openrouter",
            rag_backend="local_pipeline",
            max_sources=5,
        ),
    )
    response = await pipeline.answer(request=request, user_state=None)
    assert response.answer == "grounded answer"
    assert response.sources
    assert response.diagnostics.llm_backend == "openrouter"


# --- 5. non-2xx HTTP response maps to a clean domain error ---


async def test_openrouter_http_error_maps_cleanly():
    mock_response = MagicMock()
    mock_response.status_code = 401

    resp = MagicMock()
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized", request=MagicMock(), response=mock_response
    )

    client = AsyncMock(spec=httpx.AsyncClient)
    client.post = AsyncMock(return_value=resp)

    provider = OpenRouterLLM(
        api_key=None,
        base_url="https://openrouter.ai/api/v1",
        model="openai/gpt-4o-mini",
        client=client,
    )
    with pytest.raises(ProviderNotConfiguredError, match="401"):
        await provider.generate(
            messages=_messages(),
            sources=_sources(),
            options=GenerationOptions(),
        )


# --- 6. openrouter is now enabled; ollama still returns 501 ---


def test_chat_openrouter_no_longer_returns_501(client):
    """openrouter is enabled — a missing key should reach generate() and raise 501,
    not be rejected by the capability registry."""
    resp = client.post(
        "/chat",
        json={
            "domain": "apolo",
            "user_id": "u",
            "question": "test",
            "options": {
                "retrieval_backend": "mock",
                "llm_backend": "openrouter",
                "rag_backend": "local_pipeline",
            },
        },
    )
    # No GRC_OPENROUTER_API_KEY in test env → ProviderNotConfiguredError → 501
    assert resp.status_code == 501
    assert resp.json()["error"] == "provider_not_configured"
