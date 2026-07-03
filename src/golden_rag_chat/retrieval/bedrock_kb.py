"""Bedrock Knowledge Bases retrieval provider (skeleton).

Wraps the Knowledge Bases ``Retrieve`` API (retrieval only — generation is handled
elsewhere) behind our ``RetrievalProvider`` interface. No AWS calls happen in the
default test suite.

Verified against AWS docs (June 2026):
- Client: ``bedrock-agent-runtime``.
- Operation: ``retrieve(knowledgeBaseId=..., retrievalQuery={"text": ...},
  retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": N,
  "filter": {...}}})``.
- Result rows live under ``retrievalResults[]`` with ``content.text``,
  ``location`` (S3/Confluence/custom/…), ``score``, and ``metadata``.

To finish: install the ``bedrock`` extra, construct a boto3 client (lazily), map
``retrievalResults`` -> ``RetrievedSource``, and translate ``context`` into a
metadata ``filter``. Keep credentials in the server environment / instance role.
"""

from __future__ import annotations

import asyncio
from typing import Any

from golden_rag_chat.errors import ProviderNotConfiguredError
from golden_rag_chat.retrieval.base import RetrievedSource
from golden_rag_chat.user_state.base import UserState


def location_uri(location: dict[str, Any]) -> str:
    """Pull a URI out of a Bedrock ``location`` block, whatever its type."""
    if not location:
        return ""
    # Each location type nests a {"uri": ...} or {"url": ...} under its own key.
    for value in location.values():
        if isinstance(value, dict):
            uri = value.get("uri") or value.get("url")
            if uri:
                return str(uri)
    return str(location.get("type", ""))


def from_retrieval_results(results: list[dict[str, Any]], *, domain: str) -> list[RetrievedSource]:
    """Map Bedrock KB ``retrievalResults`` onto our RetrievedSource list (pure)."""
    sources: list[RetrievedSource] = []
    for i, row in enumerate(results):
        metadata = dict(row.get("metadata", {}))
        metadata.setdefault("domain", domain)
        uri = location_uri(row.get("location", {}))
        sources.append(
            RetrievedSource(
                source_id=str(metadata.get("source_id") or uri or f"{domain}-kb-{i}"),
                source_type=str(metadata.get("source_type", "kb_result")),
                title=str(metadata.get("title") or uri or f"KB result {i + 1}"),
                uri=uri,
                text=row.get("content", {}).get("text", ""),
                score=row.get("score"),
                metadata=metadata,
            )
        )
    return sources


class BedrockKnowledgeBaseRetrieval:
    def __init__(self, *, knowledge_base_id: str | None, region: str | None, client: Any = None):
        self._kb_id = knowledge_base_id
        self._region = region
        self._client = client  # inject a fake in tests if ever exercised

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._kb_id:
            raise ProviderNotConfiguredError("GRC_BEDROCK_KNOWLEDGE_BASE_ID is not set.")
        try:
            import boto3  # noqa: PLC0415 - optional dependency
        except ImportError as exc:  # pragma: no cover
            raise ProviderNotConfiguredError(
                "boto3 is required for the bedrock_kb backend. Install the 'bedrock' extra."
            ) from exc
        self._client = boto3.client("bedrock-agent-runtime", region_name=self._region)
        return self._client

    async def retrieve(
        self,
        *,
        domain: str,
        question: str,
        user_state: UserState | None,
        context: dict[str, Any],
        max_sources: int,
    ) -> list[RetrievedSource]:
        client = self._ensure_client()
        # ponytail: no metadata filter yet — add vectorSearchConfiguration["filter"]
        # from context once a real KB metadata schema exists.
        config = {"vectorSearchConfiguration": {"numberOfResults": max_sources}}
        # ponytail: boto3 is sync; to_thread keeps the async event loop free
        data = await asyncio.to_thread(
            client.retrieve,
            knowledgeBaseId=self._kb_id,
            retrievalQuery={"text": question},
            retrievalConfiguration=config,
        )
        results = from_retrieval_results(data.get("retrievalResults", []), domain=domain)
        return results[:max_sources]
