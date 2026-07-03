"""FastAPI application: routes for /health, /capabilities, /chat.

The routes are thin. They validate input (via Pydantic schemas), delegate to
``ChatService``, and let the registered exception handlers turn core errors into
JSON. No business or domain logic lives here.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI

from golden_rag_chat.api.dependencies import get_chat_service
from golden_rag_chat.api.errors import register_exception_handlers
from golden_rag_chat.api.schemas import (
    CapabilitiesResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
)
from golden_rag_chat.chat.service import ChatService
from golden_rag_chat.config import (
    LLM_BACKENDS,
    RAG_BACKENDS,
    RETRIEVAL_BACKENDS,
    SERVICE_NAME,
    SUPPORTED_DOMAINS,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Golden RAG Chat",
        version="0.1.0",
        summary="Reusable golden-data RAG chatbot backend (Bedrock-first, not Bedrock-locked).",
    )
    register_exception_handlers(app)

    @app.get("/health", response_model=HealthResponse, tags=["meta"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", service=SERVICE_NAME)

    @app.get("/capabilities", response_model=CapabilitiesResponse, tags=["meta"])
    async def capabilities() -> CapabilitiesResponse:
        return CapabilitiesResponse(
            domains=list(SUPPORTED_DOMAINS),
            retrieval_backends=list(RETRIEVAL_BACKENDS),
            llm_backends=list(LLM_BACKENDS),
            rag_backends=list(RAG_BACKENDS),
        )

    @app.post("/chat", response_model=ChatResponse, tags=["chat"])
    async def chat(
        request: ChatRequest,
        service: Annotated[ChatService, Depends(get_chat_service)],
    ) -> ChatResponse:
        return await service.handle(request)

    return app


app = create_app()
