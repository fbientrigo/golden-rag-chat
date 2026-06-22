"""Validate that fixtures honor the golden-data and user-state contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from golden_rag_chat.golden_data.contracts import GoldenChunk
from golden_rag_chat.user_state.base import UserState

DOMAINS = ("apolo", "agriculture")


@pytest.mark.parametrize("domain", DOMAINS)
def test_golden_chunks_validate(fixtures_dir, domain):
    path = fixtures_dir / domain / "golden_chunks.jsonl"
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines, f"no golden chunks for {domain}"
    for line in lines:
        chunk = GoldenChunk.model_validate_json(line)
        assert chunk.domain.value == domain
        assert chunk.tier == "gold"
        assert chunk.metadata.get("version")
        assert chunk.text and chunk.title and chunk.uri


@pytest.mark.parametrize("domain", DOMAINS)
def test_user_state_validates(fixtures_dir, domain):
    path = fixtures_dir / domain / "user_state.json"
    state = UserState.model_validate_json(path.read_text(encoding="utf-8"))
    assert state.domain.value == domain
    assert state.user_id


def test_golden_chunk_rejects_unknown_top_level_field():
    with pytest.raises(ValidationError):
        GoldenChunk.model_validate(
            {
                "chunk_id": "x",
                "domain": "apolo",
                "text": "t",
                "source_type": "skill_gap",
                "title": "t",
                "uri": "u",
                "metadata": {},
                "unexpected_field": "should fail",
            }
        )


def test_golden_chunk_rejects_unknown_domain():
    with pytest.raises(ValidationError):
        GoldenChunk.model_validate(
            {
                "chunk_id": "x",
                "domain": "not-a-domain",
                "text": "t",
                "source_type": "skill_gap",
                "title": "t",
                "uri": "u",
                "metadata": {},
            }
        )
