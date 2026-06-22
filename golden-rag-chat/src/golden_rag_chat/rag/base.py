"""Combined RAG contract.

A ``RAGProvider`` takes a full chat request (plus resolved user state) and returns
a complete, citation-bearing answer. There are two shapes of implementation:

- *composed* (``local_pipeline``): wires a ``RetrievalProvider`` + ``LLMProvider``
  and owns prompt building and source formatting.
- *managed* (``bedrock_retrieve_and_generate``): delegates retrieval + generation
  to a single external call (Bedrock RetrieveAndGenerate) and maps its citations
  back onto our ``Source`` schema.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from golden_rag_chat.api.schemas import ChatRequest, ChatResponse
from golden_rag_chat.user_state.base import UserState


@runtime_checkable
class RAGProvider(Protocol):
    async def answer(
        self,
        *,
        request: ChatRequest,
        user_state: UserState | None,
    ) -> ChatResponse: ...
