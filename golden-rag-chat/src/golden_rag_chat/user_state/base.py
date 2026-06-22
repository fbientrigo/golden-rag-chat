"""User-state contract and provider interface.

User state is per-(domain, user_id). It is *never* shared across domains: the
provider key is the pair, so an Apolo user and an agriculture user with the same
``user_id`` are distinct records.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from golden_rag_chat.golden_data.contracts import Domain


class UserState(BaseModel):
    """Generic user state. Domain specifics live in the free-form dict fields."""

    user_id: str
    domain: Domain
    profile: dict[str, Any] = Field(default_factory=dict)
    preferences: dict[str, Any] = Field(default_factory=dict)
    current_context: dict[str, Any] = Field(default_factory=dict)
    chat_summary: str | None = None
    updated_at: str | None = None


@runtime_checkable
class UserStateProvider(Protocol):
    """Read/write access to user state, keyed by (domain, user_id)."""

    async def get_user_state(self, *, domain: str, user_id: str) -> UserState | None: ...

    async def update_user_state(self, *, state: UserState) -> None: ...
