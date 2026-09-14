"""Local composed RAG pipeline: retrieve -> converse/tool -> generate -> cite."""

from __future__ import annotations

from golden_rag_chat.api.schemas import ChatRequest, ChatResponse, Diagnostics
from golden_rag_chat.chat.prompt_builder import build_messages
from golden_rag_chat.chat.source_formatter import to_wire_sources
from golden_rag_chat.domains.base import DomainRegistry
from golden_rag_chat.llm.base import ChatMessage, GenerationOptions, LLMProvider
from golden_rag_chat.retrieval.base import RetrievedSource, RetrievalProvider
from golden_rag_chat.tools.base import ToolRegistry
from golden_rag_chat.tools.loop import (
    merge_sources,
    parse_tool_call,
    tool_instructions,
    tool_result_message,
)
from golden_rag_chat.user_state.base import UserState

MAX_TOOL_ROUNDS = 3


class LocalRAGPipeline:
    def __init__(
        self,
        *,
        retrieval: RetrievalProvider,
        llm: LLMProvider,
        domains: DomainRegistry,
        retrieval_backend: str,
        llm_backend: str,
        tools: ToolRegistry | None = None,
    ):
        self._retrieval = retrieval
        self._llm = llm
        self._domains = domains
        self._tools = tools or ToolRegistry()
        self._retrieval_backend = retrieval_backend
        self._llm_backend = llm_backend

    def _response(
        self,
        *,
        request: ChatRequest,
        answer: str,
        sources: list[RetrievedSource],
        tool_trace: list[dict[str, object]],
        max_sources: int,
    ) -> ChatResponse:
        diagnostics = Diagnostics(
            domain=request.domain.value,
            retrieval_backend=self._retrieval_backend,
            llm_backend=self._llm_backend,
            rag_backend="local_pipeline",
            num_sources=len(sources),
        )
        return ChatResponse(
            answer=answer,
            sources=to_wire_sources(sources, max_sources=max_sources),
            diagnostics=diagnostics,
            tool_trace=tool_trace if request.options.debug else None,
        )

    async def answer(
        self,
        *,
        request: ChatRequest,
        user_state: UserState | None,
    ) -> ChatResponse:
        domain = self._domains.require(request.domain.value)
        max_sources = request.options.max_sources or 5

        sources = await self._retrieval.retrieve(
            domain=request.domain.value,
            question=request.question,
            user_state=user_state,
            context=request.context,
            max_sources=max_sources,
        )
        toolbox = self._tools.get(request.domain.value)

        # Domains without internal tools preserve the original fail-closed behavior.
        if not sources and toolbox is None:
            return self._response(
                request=request,
                answer=domain.insufficient_evidence_message(),
                sources=[],
                tool_trace=[],
                max_sources=max_sources,
            )

        messages = build_messages(
            domain=domain,
            question=request.question,
            user_state=user_state,
            context=request.context,
            sources=sources,
        )
        if toolbox is not None:
            messages.insert(1, tool_instructions(toolbox.definitions()))

        trace: list[dict[str, object]] = []
        current_sources = list(sources)

        for _ in range(MAX_TOOL_ROUNDS + 1):
            llm_response = await self._llm.generate(
                messages=messages,
                sources=current_sources,
                options=GenerationOptions(max_tokens=1024),
            )
            call = parse_tool_call(llm_response.text)

            if call is None or toolbox is None:
                return self._response(
                    request=request,
                    answer=llm_response.text,
                    sources=current_sources,
                    tool_trace=trace,
                    max_sources=max_sources,
                )

            if len(trace) >= MAX_TOOL_ROUNDS:
                return self._response(
                    request=request,
                    answer=(
                        "I couldn't complete the data lookup safely in this turn. "
                        "Please refine the question and try again."
                    ),
                    sources=current_sources,
                    tool_trace=trace,
                    max_sources=max_sources,
                )

            messages.append(ChatMessage(role="assistant", content=llm_response.text))
            try:
                execution = toolbox.execute(call.name, call.arguments)
            except (TypeError, ValueError):
                messages.append(
                    ChatMessage(
                        role="user",
                        content=(
                            "INTERNAL TOOL ERROR: the requested tool name or arguments were invalid. "
                            "Choose one available tool with valid arguments, or answer/ask a follow-up "
                            "without guessing."
                        ),
                    )
                )
                continue

            trace.append(execution.model_dump(mode="json"))
            current_sources = merge_sources(current_sources, execution)
            messages.append(tool_result_message(execution=execution, sources=current_sources))

        raise RuntimeError("unreachable tool-loop state")
