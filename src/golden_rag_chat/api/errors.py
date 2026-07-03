"""HTTP mapping for core exceptions.

The exception classes live in :mod:`golden_rag_chat.errors` (framework-free).
They are re-exported here for convenience and mapped to JSON responses.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from golden_rag_chat.api.schemas import ErrorResponse
from golden_rag_chat.errors import (
    DomainNotFoundError,
    GoldenRagError,
    ProviderNotConfiguredError,
    UnsupportedBackendError,
)

__all__ = [
    "DomainNotFoundError",
    "GoldenRagError",
    "ProviderNotConfiguredError",
    "UnsupportedBackendError",
    "register_exception_handlers",
]


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(GoldenRagError)
    async def _handle_golden_rag_error(_: Request, exc: GoldenRagError) -> JSONResponse:
        body = ErrorResponse(error=exc.error_code, detail=exc.detail)
        return JSONResponse(status_code=exc.status_code, content=body.model_dump())
