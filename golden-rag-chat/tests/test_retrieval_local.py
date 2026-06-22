"""Tests for local keyword retrieval over golden chunks."""

from __future__ import annotations

import pytest

from golden_rag_chat.golden_data.local_jsonl import LocalJsonlGoldenData
from golden_rag_chat.retrieval.local import LocalRetrievalProvider


@pytest.fixture()
def provider(fixtures_dir):
    return LocalRetrievalProvider(LocalJsonlGoldenData(fixtures_dir))


async def test_apolo_relevant_chunk_ranks_first(provider):
    sources = await provider.retrieve(
        domain="apolo",
        question="What skills am I missing for data engineering?",
        user_state=None,
        context={},
        max_sources=5,
    )
    assert sources
    assert sources[0].source_id == "apolo-skill-gap-001"
    assert all(s.metadata["domain"] == "apolo" for s in sources)


async def test_agriculture_relevant_chunk_ranks_first(provider):
    sources = await provider.retrieve(
        domain="agriculture",
        question="Why is my grape crop at fungal risk after a humid week with leaf spots?",
        user_state=None,
        context={},
        max_sources=5,
    )
    assert sources
    assert sources[0].source_id == "agri-crop-risk-001"


async def test_gibberish_returns_no_sources(provider):
    sources = await provider.retrieve(
        domain="apolo",
        question="zzzqqq nonexistent gibberish token",
        user_state=None,
        context={},
        max_sources=5,
    )
    assert sources == []


async def test_respects_max_sources(provider):
    sources = await provider.retrieve(
        domain="apolo",
        question="data engineering skills python sql cloud analytics",
        user_state=None,
        context={},
        max_sources=1,
    )
    assert len(sources) == 1


async def test_context_value_boosts_retrieval(provider):
    # The question alone would not match, but a context value matching chunk
    # metadata (role_family) should surface the chunk.
    sources = await provider.retrieve(
        domain="apolo",
        question="zzz",
        user_state=None,
        context={"role_family": "Data & Analytics Engineering"},
        max_sources=5,
    )
    assert any(s.source_id == "apolo-skill-gap-001" for s in sources)


async def test_domain_isolation(provider):
    # Querying apolo must never return agriculture chunks.
    sources = await provider.retrieve(
        domain="apolo",
        question="grape fungal humid frost leaf",
        user_state=None,
        context={},
        max_sources=5,
    )
    assert all(not s.source_id.startswith("agri-") for s in sources)
