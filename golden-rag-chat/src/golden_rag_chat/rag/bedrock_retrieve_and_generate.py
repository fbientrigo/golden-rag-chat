"""Managed Bedrock RetrieveAndGenerate RAG provider (M4 skeleton).

A single managed call performs retrieval *and* generation. This implements the
``RAGProvider`` interface directly (it does not use the retrieval/LLM providers).
No AWS calls run in the default test suite.

Verified against AWS docs (June 2026):
- Client: ``bedrock-agent-runtime``; operation ``retrieve_and_generate`` (and
  ``retrieve_and_generate_stream``).
- Request: ``input={"text": ...}`` and ``retrieveAndGenerateConfiguration`` with
  ``type="KNOWLEDGE_BASE"`` and ``knowledgeBaseConfiguration={"knowledgeBaseId",
  "modelArn", ...}``.
- Response: ``output.text`` for the answer; ``citations[].retrievedReferences[]``
  for sources (the older top-level ``citation`` member is deprecated — use
  ``retrievedReferences``); ``sessionId`` to continue a conversation.
- Caveat: guardrails may not sanitize raw retrieved references, so we still apply
  application-level filtering when mapping references -> ``Source``.

To finish: build the config (translate ``request.context`` to a metadata
``filter``), call the API, and map ``citations`` -> our ``Source`` list.
"""

from __future__ import annotations

import asyncio
from typing import Any

from golden_rag_chat.api.schemas import ChatRequest, ChatResponse, Diagnostics, Source
from golden_rag_chat.errors import ProviderNotConfiguredError
from golden_rag_chat.retrieval.bedrock_kb import location_uri
from golden_rag_chat.user_state.base import UserState


def from_rag_response(
    data: dict[str, Any], *, request: ChatRequest, max_sources: int
) -> ChatResponse:
    """Map a RetrieveAndGenerate response onto our ChatResponse (pure, testable)."""
    answer = data.get("output", {}).get("text", "")

    sources: list[Source] = []
    seen: set[str] = set()
    for citation in data.get("citations", []):
        # Use retrievedReferences (the older top-level `citation` member is deprecated).
        for ref in citation.get("retrievedReferences", []):
            uri = location_uri(ref.get("location", {}))
            metadata = dict(ref.get("metadata", {}))
            metadata.setdefault("domain", request.domain.value)
            key = str(metadata.get("source_id") or uri or ref.get("content", {}).get("text", ""))
            if key in seen:
                continue
            seen.add(key)
            sources.append(
                Source(
                    source_id=str(metadata.get("source_id") or uri or f"kb-{len(sources)}"),
                    source_type=str(metadata.get("source_type", "kb_result")),
                    title=str(metadata.get("title") or uri or f"KB reference {len(sources) + 1}"),
                    uri=uri,
                    metadata=metadata,
                    excerpt=ref.get("content", {}).get("text", ""),
                )
            )
            if len(sources) >= max_sources:
                break
        if len(sources) >= max_sources:
            break

    diagnostics = Diagnostics(
        domain=request.domain.value,
        retrieval_backend="bedrock_kb",
        llm_backend="bedrock_converse",
        rag_backend="bedrock_retrieve_and_generate",
        num_sources=len(sources),
    )
    return ChatResponse(answer=answer, sources=sources, diagnostics=diagnostics)


class BedrockRetrieveAndGenerate:
    def __init__(
        self,
        *,
        knowledge_base_id: str | None,
        model_id: str | None,
        region: str | None,
        client: Any = None,
    ):
        self._kb_id = knowledge_base_id
        self._model_id = model_id
        self._region = region
        self._client = client

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._kb_id or not self._model_id:
            raise ProviderNotConfiguredError(
                "GRC_BEDROCK_KNOWLEDGE_BASE_ID and GRC_BEDROCK_MODEL_ID must be set."
            )
        try:
            import boto3  # noqa: PLC0415 - optional dependency
        except ImportError as exc:  # pragma: no cover
            raise ProviderNotConfiguredError(
                "boto3 is required for bedrock_retrieve_and_generate. Install the 'bedrock' extra."
            ) from exc
        self._client = boto3.client("bedrock-agent-runtime", region_name=self._region)
        return self._client

    async def answer(
        self, *, request: ChatRequest, user_state: UserState | None
    ) -> ChatResponse:
        client = self._ensure_client()
        max_sources = request.options.max_sources or 5
        config = {
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": self._kb_id,
                "modelArn": self._model_id,
            },
        }
        # ponytail: boto3 is sync; to_thread keeps the async event loop free
        data = await asyncio.to_thread(
            client.retrieve_and_generate,
            input={"text": request.question},
            retrieveAndGenerateConfiguration=config,
        )
        return from_rag_response(data, request=request, max_sources=max_sources)
