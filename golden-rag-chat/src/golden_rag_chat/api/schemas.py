"""HTTP wire schemas (request/response bodies).

These are the public contract. Internal types (``RetrievedSource``,
``ChatMessage`` …) are deliberately separate so we can change internals without
breaking clients. ``Source`` here is the citation-facing projection of an
internal ``RetrievedSource``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from golden_rag_chat.config import SERVICE_NAME
from golden_rag_chat.golden_data.contracts import Domain


class ChatOptions(BaseModel):
    """Per-request backend selection. Omitted fields fall back to server defaults."""

    retrieval_backend: str | None = None
    llm_backend: str | None = None
    rag_backend: str | None = None
    max_sources: int | None = Field(default=None, ge=1, le=50)


class ChatRequest(BaseModel):
    domain: Domain
    user_id: str
    session_id: str | None = None
    question: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    options: ChatOptions = Field(default_factory=ChatOptions)


class Source(BaseModel):
    """A citation returned to the client. Carries only an excerpt, not full text."""

    source_id: str
    source_type: str
    title: str
    uri: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    excerpt: str


class Diagnostics(BaseModel):
    domain: str
    retrieval_backend: str
    llm_backend: str
    rag_backend: str
    num_sources: int


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)
    diagnostics: Diagnostics


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = SERVICE_NAME


class CapabilitiesResponse(BaseModel):
    domains: list[str]
    retrieval_backends: list[str]
    llm_backends: list[str]
    rag_backends: list[str]


class ErrorResponse(BaseModel):
    error: str
    detail: str
