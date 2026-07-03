"""Provider selection and the top-level chat service.

``ProviderFactory`` turns backend *names* into provider instances, enforcing the
capability registry:
- unknown name              -> ``UnsupportedBackendError`` (HTTP 400)
- known but not enabled here -> ``ProviderNotConfiguredError`` (HTTP 501)

``ChatService`` resolves request options against server defaults, loads user
state, builds the right ``RAGProvider``, and delegates. It holds **no**
domain-specific logic and does not branch on which backend is in use.
"""

from __future__ import annotations

from golden_rag_chat.api.schemas import ChatOptions, ChatRequest, ChatResponse
from golden_rag_chat.config import (
    IMPLEMENTED_LLM_BACKENDS,
    IMPLEMENTED_RAG_BACKENDS,
    IMPLEMENTED_RETRIEVAL_BACKENDS,
    LLM_BACKENDS,
    RAG_BACKENDS,
    RETRIEVAL_BACKENDS,
    Settings,
)
from golden_rag_chat.domains.base import DomainRegistry
from golden_rag_chat.errors import ProviderNotConfiguredError, UnsupportedBackendError
from golden_rag_chat.golden_data.loader import GoldenDataSource
from golden_rag_chat.llm.base import LLMProvider
from golden_rag_chat.llm.bedrock_converse import BedrockConverseLLM
from golden_rag_chat.llm.mock import MockLLMProvider
from golden_rag_chat.llm.openrouter import OpenRouterLLM
from golden_rag_chat.rag.base import RAGProvider
from golden_rag_chat.rag.bedrock_retrieve_and_generate import BedrockRetrieveAndGenerate
from golden_rag_chat.rag.local_pipeline import LocalRAGPipeline
from golden_rag_chat.retrieval.base import RetrievalProvider
from golden_rag_chat.retrieval.bedrock_kb import BedrockKnowledgeBaseRetrieval
from golden_rag_chat.retrieval.local import LocalRetrievalProvider
from golden_rag_chat.retrieval.mock import MockRetrievalProvider
from golden_rag_chat.user_state.base import UserState, UserStateProvider


def _check(name: str, *, registry: tuple[str, ...], implemented: frozenset[str], kind: str) -> None:
    if name not in registry:
        raise UnsupportedBackendError(
            f"Unknown {kind} backend '{name}'. Supported: {', '.join(registry)}."
        )
    if name not in implemented:
        raise ProviderNotConfiguredError(
            f"The {kind} backend '{name}' is registered but not enabled in this build."
        )


class ProviderFactory:
    def __init__(
        self,
        *,
        settings: Settings,
        domains: DomainRegistry,
        golden_data: GoldenDataSource,
    ):
        self._settings = settings
        self._domains = domains
        self._golden_data = golden_data

    def build_retrieval(self, name: str) -> RetrievalProvider:
        _check(name, registry=RETRIEVAL_BACKENDS, implemented=IMPLEMENTED_RETRIEVAL_BACKENDS, kind="retrieval")
        if name == "mock":
            return MockRetrievalProvider()
        if name == "local":
            return LocalRetrievalProvider(self._golden_data)
        if name == "bedrock_kb":
            s = self._settings
            return BedrockKnowledgeBaseRetrieval(
                knowledge_base_id=s.bedrock_knowledge_base_id,
                region=s.aws_region,
            )
        raise ProviderNotConfiguredError(f"retrieval backend '{name}' has no constructor.")

    def build_llm(self, name: str) -> LLMProvider:
        _check(name, registry=LLM_BACKENDS, implemented=IMPLEMENTED_LLM_BACKENDS, kind="llm")
        if name == "mock":
            return MockLLMProvider()
        if name == "openrouter":
            s = self._settings
            return OpenRouterLLM(
                api_key=s.openrouter_api_key,
                base_url=s.openrouter_base_url,
                model=s.openrouter_model,
                site_url=s.openrouter_site_url,
                app_name=s.openrouter_app_name,
            )
        if name == "bedrock_converse":
            s = self._settings
            return BedrockConverseLLM(
                model_id=s.bedrock_model_id,
                region=s.aws_region,
            )
        raise ProviderNotConfiguredError(f"llm backend '{name}' has no constructor.")

    def build_rag(self, *, rag_backend: str, retrieval_backend: str, llm_backend: str) -> RAGProvider:
        _check(rag_backend, registry=RAG_BACKENDS, implemented=IMPLEMENTED_RAG_BACKENDS, kind="rag")
        if rag_backend == "local_pipeline":
            return LocalRAGPipeline(
                retrieval=self.build_retrieval(retrieval_backend),
                llm=self.build_llm(llm_backend),
                domains=self._domains,
                retrieval_backend=retrieval_backend,
                llm_backend=llm_backend,
            )
        if rag_backend == "bedrock_retrieve_and_generate":
            s = self._settings
            return BedrockRetrieveAndGenerate(
                knowledge_base_id=s.bedrock_knowledge_base_id,
                model_id=s.bedrock_model_id,
                region=s.aws_region,
            )
        raise ProviderNotConfiguredError(f"rag backend '{rag_backend}' has no constructor.")


class ChatService:
    def __init__(
        self,
        *,
        settings: Settings,
        factory: ProviderFactory,
        user_state_provider: UserStateProvider,
    ):
        self._settings = settings
        self._factory = factory
        self._user_state = user_state_provider

    def _resolve_options(self, options: ChatOptions) -> ChatOptions:
        s = self._settings
        return ChatOptions(
            retrieval_backend=options.retrieval_backend or s.default_retrieval_backend,
            llm_backend=options.llm_backend or s.default_llm_backend,
            rag_backend=options.rag_backend or s.default_rag_backend,
            max_sources=options.max_sources or s.default_max_sources,
        )

    async def handle(self, request: ChatRequest) -> ChatResponse:
        resolved = self._resolve_options(request.options)
        request = request.model_copy(update={"options": resolved})

        user_state: UserState | None = await self._user_state.get_user_state(
            domain=request.domain.value, user_id=request.user_id
        )

        rag = self._factory.build_rag(
            rag_backend=resolved.rag_backend,
            retrieval_backend=resolved.retrieval_backend,
            llm_backend=resolved.llm_backend,
        )
        return await rag.answer(request=request, user_state=user_state)
