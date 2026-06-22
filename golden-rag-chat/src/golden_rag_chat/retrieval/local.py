"""Local keyword retrieval over golden chunks.

A deliberately simple, dependency-free baseline: tokenize the question (plus any
string values in the request context), score each chunk by token-overlap with its
title + text, give a small boost when context values match the chunk's metadata,
drop zero-score chunks, and return the top ``max_sources``.

No embeddings required (per the M2 plan). A vector backend can later implement the
same ``RetrievalProvider`` interface without touching the rest of the system.
"""

from __future__ import annotations

import re
from typing import Any

from golden_rag_chat.golden_data.contracts import GoldenChunk
from golden_rag_chat.golden_data.loader import GoldenDataSource
from golden_rag_chat.retrieval.base import RetrievedSource
from golden_rag_chat.user_state.base import UserState

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Common words that should not drive retrieval.
_STOPWORDS = frozenset(
    """a an and are as at be by for from how i in is it of on or that the to what
    which who why with you your am my me are do does my our""".split()
)


def _tokenize(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS and len(t) > 1}


def _context_terms(context: dict[str, Any]) -> set[str]:
    terms: set[str] = set()
    for value in context.values():
        if isinstance(value, str):
            terms |= _tokenize(value)
    return terms


class LocalRetrievalProvider:
    def __init__(self, source: GoldenDataSource):
        self._source = source

    def _score(self, chunk: GoldenChunk, query_terms: set[str], context: dict[str, Any]) -> float:
        haystack = _tokenize(f"{chunk.title} {chunk.text}")
        overlap = len(query_terms & haystack)
        score = float(overlap)

        # Boost when a context value matches a metadata value (e.g. role_family, crop).
        meta_values = {str(v).lower() for v in chunk.metadata.values()}
        for value in context.values():
            if isinstance(value, str) and value.lower() in meta_values:
                score += 2.0
        return score

    async def retrieve(
        self,
        *,
        domain: str,
        question: str,
        user_state: UserState | None,
        context: dict[str, Any],
        max_sources: int,
    ) -> list[RetrievedSource]:
        query_terms = _tokenize(question) | _context_terms(context)
        chunks = self._source.load_chunks(domain=domain)

        scored: list[tuple[float, GoldenChunk]] = []
        for chunk in chunks:
            score = self._score(chunk, query_terms, context)
            if score > 0:
                scored.append((score, chunk))

        # Sort by score desc, then chunk_id for deterministic ties.
        scored.sort(key=lambda pair: (-pair[0], pair[1].chunk_id))

        results: list[RetrievedSource] = []
        for score, chunk in scored[:max_sources]:
            results.append(
                RetrievedSource(
                    source_id=chunk.chunk_id,
                    source_type=chunk.source_type,
                    title=chunk.title,
                    uri=chunk.uri,
                    text=chunk.text,
                    score=score,
                    metadata={**chunk.metadata, "domain": chunk.domain.value},
                )
            )
        return results
