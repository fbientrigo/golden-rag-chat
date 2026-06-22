"""Tests for prompt construction across domains."""

from __future__ import annotations

from golden_rag_chat.chat.prompt_builder import build_messages
from golden_rag_chat.domains import default_registry
from golden_rag_chat.retrieval.base import RetrievedSource
from golden_rag_chat.user_state.base import UserState


def _sources() -> list[RetrievedSource]:
    return [
        RetrievedSource(
            source_id="s1",
            source_type="skill_gap",
            title="Gap A",
            uri="golden://a",
            text="evidence about SQL and Python",
            score=1.0,
        )
    ]


def test_prompt_builder_apolo_structure():
    domain = default_registry().require("apolo")
    state = UserState(
        user_id="u",
        domain="apolo",
        profile={"known_skills": ["Python"]},
        current_context={"selected_role_family": "Data & Analytics Engineering"},
    )
    messages = build_messages(
        domain=domain,
        question="What am I missing?",
        user_state=state,
        context={"career_id": "uchile-ingcivil"},
        sources=_sources(),
    )
    assert messages[0].role == "system"
    assert "Apolo" in messages[0].content
    assert "Ground every claim" in messages[0].content

    user = messages[1].content
    assert messages[1].role == "user"
    assert "QUESTION: What am I missing?" in user
    assert "[S1] Gap A" in user
    assert "Python" in user  # user-state rendered
    assert "career_id" in user  # context rendered


def test_prompt_builder_agriculture_persona():
    domain = default_registry().require("agriculture")
    messages = build_messages(
        domain=domain,
        question="Why leaf spots?",
        user_state=None,
        context={},
        sources=_sources(),
    )
    assert "agronomic" in messages[0].content.lower()
    assert "QUESTION: Why leaf spots?" in messages[1].content


def test_prompt_builder_marks_absent_evidence():
    domain = default_registry().require("apolo")
    messages = build_messages(
        domain=domain,
        question="q",
        user_state=None,
        context={},
        sources=[],
    )
    assert "(no evidence retrieved)" in messages[1].content
