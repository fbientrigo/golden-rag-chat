"""Offline tests for the bounded APOLO conversational tool loop."""

from __future__ import annotations

from golden_rag_chat.api.schemas import ChatOptions, ChatRequest
from golden_rag_chat.domains import default_registry
from golden_rag_chat.golden_data.contracts import Domain, GoldenChunk
from golden_rag_chat.llm.base import ChatMessage, GenerationOptions, LLMResponse
from golden_rag_chat.rag.local_pipeline import LocalRAGPipeline
from golden_rag_chat.retrieval.base import RetrievedSource
from golden_rag_chat.tools.apolo import ApoloToolbox
from golden_rag_chat.tools.base import ToolRegistry
from golden_rag_chat.tools.loop import parse_tool_call


class _MemoryGoldenData:
    def __init__(self, chunks: list[GoldenChunk]):
        self._chunks = chunks

    def load_chunks(self, *, domain: str) -> list[GoldenChunk]:
        assert domain == "apolo"
        return self._chunks


class _EmptyRetrieval:
    async def retrieve(
        self,
        *,
        domain: str,
        question: str,
        user_state,
        context: dict,
        max_sources: int,
    ) -> list[RetrievedSource]:
        return []


class _SequentialLLM:
    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.calls: list[dict] = []

    async def generate(
        self,
        *,
        messages: list[ChatMessage],
        sources: list[RetrievedSource],
        options: GenerationOptions,
    ) -> LLMResponse:
        self.calls.append(
            {
                "messages": [message.model_copy() for message in messages],
                "source_ids": [source.source_id for source in sources],
            }
        )
        return LLMResponse(text=self._responses[len(self.calls) - 1], model="fake")


def _toolbox() -> ApoloToolbox:
    chunk = GoldenChunk(
        chunk_id="program-computacion",
        domain="apolo",
        source_type="career_profile",
        title="Ingeniería Civil en Computación",
        text="Programa con formación en programación y desarrollo de software.",
        uri="golden://apolo/program-computacion",
        metadata={
            "program_id": "uchile-computacion",
            "program_name": "Ingeniería Civil en Computación",
            "institution": "Universidad de Chile",
            "skills": [
                {
                    "skill_id": "skill_programming",
                    "canonical_name": "Programación",
                    "aliases": ["scripts", "programar"],
                }
            ],
        },
    )
    return ApoloToolbox(_MemoryGoldenData([chunk]))


def _request(*, debug: bool) -> ChatRequest:
    return ChatRequest(
        domain=Domain.APOLO,
        user_id="student-1",
        question="Me gusta hacer scripts para mods",
        options=ChatOptions(
            retrieval_backend="local",
            llm_backend="fake",
            rag_backend="local_pipeline",
            max_sources=5,
            debug=debug,
        ),
    )


async def test_apolo_can_call_tool_without_initial_retrieval_evidence():
    llm = _SequentialLLM(
        [
            (
                '{"tool_call":{"name":"get_skill_alignment",'
                '"arguments":{"text":"Me gusta hacer scripts para mods"}}}'
            ),
            "Lo de hacer scripts sí tiene una coincidencia explícita con programación.",
        ]
    )
    pipeline = LocalRAGPipeline(
        retrieval=_EmptyRetrieval(),
        llm=llm,
        domains=default_registry(),
        retrieval_backend="local",
        llm_backend="fake",
        tools=ToolRegistry({"apolo": _toolbox()}),
    )

    response = await pipeline.answer(request=_request(debug=True), user_state=None)

    assert len(llm.calls) == 2
    assert llm.calls[0]["source_ids"] == []
    assert llm.calls[1]["source_ids"] == ["program-computacion"]
    assert response.answer.startswith("Lo de hacer scripts")
    assert response.diagnostics.num_sources == 1
    assert response.sources[0].source_id == "program-computacion"
    assert response.tool_trace is not None
    assert response.tool_trace[0]["name"] == "get_skill_alignment"
    assert response.tool_trace[0]["arguments"]["text"] == "Me gusta hacer scripts para mods"


async def test_tool_trace_is_hidden_when_debug_is_false():
    llm = _SequentialLLM(
        [
            (
                '{"tool_call":{"name":"get_skill_alignment",'
                '"arguments":{"text":"scripts"}}}'
            ),
            "Encontré una coincidencia explícita.",
        ]
    )
    pipeline = LocalRAGPipeline(
        retrieval=_EmptyRetrieval(),
        llm=llm,
        domains=default_registry(),
        retrieval_backend="local",
        llm_backend="fake",
        tools=ToolRegistry({"apolo": _toolbox()}),
    )

    response = await pipeline.answer(request=_request(debug=False), user_state=None)

    assert response.tool_trace is None
    assert response.sources


def test_parse_tool_call_does_not_capture_normal_conversation():
    assert parse_tool_call("¿Qué parte de hacer mods te entretiene más?") is None
    assert parse_tool_call('{"answer":"normal JSON, not a tool call"}') is None


def test_parse_tool_call_accepts_only_explicit_envelope():
    call = parse_tool_call(
        '{"tool_call":{"name":"search_programs","arguments":{"query":"mods"}}}'
    )

    assert call is not None
    assert call.name == "search_programs"
    assert call.arguments == {"query": "mods"}
