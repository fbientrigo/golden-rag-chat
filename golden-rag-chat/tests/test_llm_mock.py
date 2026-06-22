"""Tests for the deterministic mock LLM provider."""

from __future__ import annotations

from golden_rag_chat.llm.base import ChatMessage, GenerationOptions
from golden_rag_chat.llm.mock import MockLLMProvider
from golden_rag_chat.retrieval.base import RetrievedSource


def _source(i: int) -> RetrievedSource:
    return RetrievedSource(
        source_id=f"s{i}",
        source_type="skill_gap",
        title=f"Title {i}",
        uri=f"golden://x/{i}",
        text=f"evidence number {i}",
        score=1.0,
    )


async def test_mock_llm_grounds_in_sources():
    llm = MockLLMProvider()
    messages = [
        ChatMessage(role="system", content="system prompt"),
        ChatMessage(role="user", content="QUESTION: hello"),
    ]
    sources = [_source(1), _source(2)]
    resp = await llm.generate(messages=messages, sources=sources, options=GenerationOptions())
    assert "2 source" in resp.text
    assert "Title 1" in resp.text and "Title 2" in resp.text
    assert resp.model == "mock-llm-v1"
    assert resp.usage["num_sources"] == 2


async def test_mock_llm_refuses_without_sources():
    llm = MockLLMProvider()
    resp = await llm.generate(
        messages=[ChatMessage(role="user", content="QUESTION: anything")],
        sources=[],
        options=GenerationOptions(),
    )
    assert "enough" in resp.text.lower()
    assert resp.usage["num_sources"] == 0


async def test_mock_llm_is_deterministic():
    llm = MockLLMProvider()
    messages = [ChatMessage(role="user", content="QUESTION: hi")]
    sources = [_source(1)]
    a = await llm.generate(messages=messages, sources=sources, options=GenerationOptions())
    b = await llm.generate(messages=messages, sources=sources, options=GenerationOptions())
    assert a.text == b.text
