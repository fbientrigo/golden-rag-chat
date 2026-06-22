"""Core application exceptions (no web-framework dependency).

Providers and the core raise these without knowing about HTTP. The API layer
(``api.errors``) maps them to status codes and JSON bodies.
"""

from __future__ import annotations


class GoldenRagError(Exception):
    """Base class for all application errors."""

    error_code = "internal_error"
    status_code = 500

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class UnsupportedBackendError(GoldenRagError):
    """Requested a backend name that does not exist in the capability registry."""

    error_code = "unsupported_backend"
    status_code = 400


class DomainNotFoundError(GoldenRagError):
    """Requested a domain with no registered adapter."""

    error_code = "domain_not_found"
    status_code = 400


class ProviderNotConfiguredError(GoldenRagError):
    """Backend exists in the registry but is a skeleton / missing configuration."""

    error_code = "provider_not_configured"
    status_code = 501
