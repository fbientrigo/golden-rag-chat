"""Domain adapters.

The generic chat core must contain **no** Apolo- or agriculture-specific logic.
All of that lives behind a ``DomainAdapter``: the system persona, how user state
is summarized for the prompt, and how request context is rendered. Adding a third
domain later means writing one adapter and registering it — nothing in the core
changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from golden_rag_chat.user_state.base import UserState

# Grounding rules shared by every domain. They encode the project's safety rules:
# cite evidence, admit insufficiency, never fabricate from golden data.
GROUNDING_RULES = (
    "Ground every claim in the provided evidence sources, which come from curated "
    "golden data. Refer to sources by their [S#] label. If the evidence is "
    "insufficient to answer, say so plainly and do not guess. Never invent facts, "
    "numbers, or sources that are not present in the evidence."
)


class DomainAdapter(ABC):
    """Strategy object describing one business domain."""

    #: Stable identifier; must match a value in ``Domain``.
    name: str

    @abstractmethod
    def persona(self) -> str:
        """Domain-specific role/persona line for the system prompt."""

    def system_prompt(self) -> str:
        return f"{self.persona()}\n\n{GROUNDING_RULES}"

    @abstractmethod
    def render_user_state(self, user_state: UserState | None) -> str:
        """Human-readable summary of the user's state for the prompt."""

    def render_context(self, context: dict[str, Any]) -> str:
        """Render per-request context. Default: compact key/value lines."""
        if not context:
            return "(no additional context)"
        return "\n".join(f"- {k}: {v}" for k, v in sorted(context.items()))

    def insufficient_evidence_message(self) -> str:
        """Fallback answer when retrieval returns nothing."""
        return (
            "I don't have enough golden-data evidence to answer that yet. "
            "Try refining the question or selecting more context."
        )


class DomainRegistry:
    """Looks up adapters by name."""

    def __init__(self, adapters: list[DomainAdapter]):
        self._by_name: dict[str, DomainAdapter] = {a.name: a for a in adapters}

    def get(self, name: str) -> DomainAdapter | None:
        return self._by_name.get(name)

    def require(self, name: str) -> DomainAdapter:
        adapter = self._by_name.get(name)
        if adapter is None:
            from golden_rag_chat.errors import DomainNotFoundError

            raise DomainNotFoundError(f"No adapter registered for domain '{name}'.")
        return adapter

    def names(self) -> list[str]:
        return sorted(self._by_name)
