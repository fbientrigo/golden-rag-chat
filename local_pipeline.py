"""Local composed RAG pipeline: retrieve -> prompt -> generate -> cite.

This is the reference ``RAGProvider``. It is intentionally provider-agnostic: it
holds *a* retrieval provider and *an* LLM provider, whatever they are. The
mock/local/Bedrock distinction is decided by the factory, not here.
"""

from __future__ import annotations

from golden_rag_chat.api.schemas import ChatRequest, ChatResponse, Diagnostics
from golden_rag_chat.chat.prompt_builder import build_messages
from golden_rag_chat.chat.source_formatter import to_wire_sources
from golden_rag_chat.domains.base import DomainRegistry
from golden_rag_chat.llm.base import GenerationOptions, LLMProvider
from golden_rag_chat.retrieval.base import RetrievalProvider
from golden_rag_chat.user_state.base import UserState


class LocalRAGPipeline:
    def __init__(
        self,
        *,
        retrieval: RetrievalProvider,
        llm: LLMProvider,
        domains: DomainRegistry,
        retrieval_backend: str,
        llm_backend: str,
    ):
        self._retrieval = retrieval
        self._llm = llm
        self._domains = domains
        # Recorded for diagnostics only; the pipeline does not branch on them.
        self._retrieval_backend = retrieval_backend
        self._llm_backend = llm_backend

    async def answer(self, *, request: ChatRequest, user_state: UserState | None) -> ChatResponse:
        domain = self._domains.require(request.domain.value)
        max_sources = request.options.max_sources or 5

        sources = await self._retrieval.retrieve(
            domain=request.domain.value,
            question=request.question,
            user_state=user_state,
            context=request.context,
            max_sources=max_sources,
        )

        diagnostics = Diagnostics(
            domain=request.domain.value,
            retrieval_backend=self._retrieval_backend,
            llm_backend=self._llm_backend,
            rag_backend="local_pipeline",
            num_sources=len(sources),
        )

        # Safety rule: with no evidence, return the domain's insufficiency message
        # rather than calling the model and risking a fabricated answer.
        if not sources:
            return ChatResponse(
                answer=domain.insufficient_evidence_message(),
                sources=[],
                diagnostics=diagnostics,
            )

        messages = build_messages(
            domain=domain,
            question=request.question,
            user_state=user_state,
            context=request.context,
            sources=sources,
        )
        llm_response = await self._llm.generate(
            messages=messages,
            sources=sources,
            options=GenerationOptions(max_tokens=1024),
        )

        return ChatResponse(
            answer=llm_response.text,
            sources=to_wire_sources(sources, max_sources=max_sources),
            diagnostics=diagnostics,
        )
