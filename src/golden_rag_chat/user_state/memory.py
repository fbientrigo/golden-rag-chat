"""In-memory user-state provider.

Default for development and tests. State is keyed by ``(domain, user_id)`` so the
same ``user_id`` in different domains never collides. Not durable — process
memory only.
"""

from __future__ import annotations

from golden_rag_chat.user_state.base import UserState


class InMemoryUserStateProvider:
    def __init__(self, seed: list[UserState] | None = None):
        self._store: dict[tuple[str, str], UserState] = {}
        for state in seed or []:
            self._store[(state.domain.value, state.user_id)] = state

    async def get_user_state(self, *, domain: str, user_id: str) -> UserState | None:
        return self._store.get((domain, user_id))

    async def update_user_state(self, *, state: UserState) -> None:
        self._store[(state.domain.value, state.user_id)] = state
