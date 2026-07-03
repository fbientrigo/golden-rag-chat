"""Mock LLM provider.

Deterministic, offline, and *grounded*: the generated text only references the
sources it was given (by [S#] label and title). With no sources it returns an
explicit insufficiency notice. This lets tests assert grounding behavior without
a network call.
"""

from __future__ import annotations

from golden_rag_chat.llm.base import ChatMessage, GenerationOptions, LLMResponse
from golden_rag_chat.retrieval.base import RetrievedSource

MODEL_NAME = "mock-llm-v1"


def _last_question(messages: list[ChatMessage]) -> str:
    for msg in reversed(messages):
        if msg.role == "user":
            for line in msg.content.splitlines():
                if line.startswith("QUESTION:"):
                    return line[len("QUESTION:") :].strip()
    return ""


class MockLLMProvider:
    async def generate(
        self,
        *,
        messages: list[ChatMessage],
        sources: list[RetrievedSource],
        options: GenerationOptions,
    ) -> LLMResponse:
        if not sources:
            return LLMResponse(
                text=(
                    "I don't have enough golden-data evidence to answer that yet, "
                    "so I can't give a grounded response."
                ),
                model=MODEL_NAME,
                usage={"prompt_messages": len(messages), "num_sources": 0},
            )

        citations = "; ".join(f"[S{i}] {s.title}" for i, s in enumerate(sources, start=1))
        question = _last_question(messages)
        question_clause = f' for "{question}"' if question else ""
        text = (
            f"Based on the current golden data{question_clause}, here is a grounded "
            f"summary drawn from {len(sources)} source(s): {citations}. "
            "See the cited sources for details."
        )
        return LLMResponse(
            text=text,
            model=MODEL_NAME,
            usage={"prompt_messages": len(messages), "num_sources": len(sources)},
        )
