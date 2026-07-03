"""LLM contract.

The LLM provider is given an already-built message list *and* the structured
sources. Most providers only need ``messages`` (the prompt builder has already
formatted the evidence into them), but combined/managed backends may want the
structured ``sources`` too, so both are passed.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from golden_rag_chat.retrieval.base import RetrievedSource

Role = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    role: Role
    content: str


class GenerationOptions(BaseModel):
    model: str | None = None
    temperature: float = 0.2
    max_tokens: int = 1024
    extra: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    text: str
    model: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] | None = None


@runtime_checkable
class LLMProvider(Protocol):
    """Generates an answer from a prompt and the supporting sources."""

    async def generate(
        self,
        *,
        messages: list[ChatMessage],
        sources: list[RetrievedSource],
        options: GenerationOptions,
    ) -> LLMResponse: ...
