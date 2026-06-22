"""Pluggable business domains."""

from __future__ import annotations

from golden_rag_chat.domains.agriculture import AgricultureDomain
from golden_rag_chat.domains.apolo import ApoloDomain
from golden_rag_chat.domains.base import DomainAdapter, DomainRegistry

__all__ = ["AgricultureDomain", "ApoloDomain", "DomainAdapter", "DomainRegistry", "default_registry"]


def default_registry() -> DomainRegistry:
    """The registry of domains shipped with this service."""
    return DomainRegistry([ApoloDomain(), AgricultureDomain()])
