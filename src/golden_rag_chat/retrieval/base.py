"""Retrieval contract.

A ``RetrievedSource`` is the *internal* evidence object returned by retrieval and
fed to the LLM. It carries the full chunk ``text``. The public, citation-facing
``Source`` (in ``api.schemas``) is derived from it and exposes only a short
``excerpt``.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from golden_rag_chat.user_state.base import UserState


class RetrievedSource(BaseModel):
    """One piece of evidence retrieved for a query (internal representation)."""

    source_id: str
    source_type: str
    title: str
    uri: str
    text: str
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class RetrievalProvider(Protocol):
    """Retrieves evidence for a question within a domain."""

    async def retrieve(
        self,
        *,
        domain: str,
        question: str,
        user_state: UserState | None,
        context: dict[str, Any],
        max_sources: int,
    ) -> list[RetrievedSource]: ...
