"""Convert retrieved evidence into (a) prompt text and (b) citation objects.

Two projections of the same ``RetrievedSource`` list:
- ``format_sources_for_prompt`` -> labelled evidence block the LLM can cite.
- ``to_wire_sources`` -> public ``Source`` objects with short excerpts.

Keeping both here ensures the [S#] labels the model sees line up with the order
of sources returned to the client.
"""

from __future__ import annotations

from golden_rag_chat.api.schemas import Source
from golden_rag_chat.retrieval.base import RetrievedSource

DEFAULT_EXCERPT_CHARS = 320


def _excerpt(text: str, limit: int = DEFAULT_EXCERPT_CHARS) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def format_sources_for_prompt(sources: list[RetrievedSource]) -> str:
    """Render evidence as ``[S1] Title (uri)\\n<text>`` blocks."""
    if not sources:
        return "(no evidence retrieved)"
    blocks = []
    for i, s in enumerate(sources, start=1):
        blocks.append(f"[S{i}] {s.title} ({s.uri})\n{s.text.strip()}")
    return "\n\n".join(blocks)


def to_wire_sources(sources: list[RetrievedSource], *, max_sources: int | None = None) -> list[Source]:
    """Project internal sources to public citation objects (excerpt only)."""
    selected = sources if max_sources is None else sources[:max_sources]
    return [
        Source(
            source_id=s.source_id,
            source_type=s.source_type,
            title=s.title,
            uri=s.uri,
            metadata=s.metadata,
            excerpt=_excerpt(s.text),
        )
        for s in selected
    ]
