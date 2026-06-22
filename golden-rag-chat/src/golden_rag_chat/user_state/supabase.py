"""Supabase / Postgres user-state provider (skeleton).

Suggested table ``user_state(domain text, user_id text, profile jsonb,
preferences jsonb, current_context jsonb, chat_summary text, updated_at
timestamptz, primary key (domain, user_id))``. Enforce row-level security so a
user can only read their own row. No network calls in the default tests.
"""

from __future__ import annotations

from golden_rag_chat.errors import ProviderNotConfiguredError
from golden_rag_chat.user_state.base import UserState


class SupabaseUserStateProvider:
    def __init__(self, *, url: str | None, service_key: str | None):
        self._url = url
        self._service_key = service_key

    def _ensure_config(self) -> None:  # pragma: no cover - skeleton
        if not self._url or not self._service_key:
            raise ProviderNotConfiguredError("Supabase URL / service key are not configured.")

    async def get_user_state(self, *, domain: str, user_id: str) -> UserState | None:  # pragma: no cover
        raise NotImplementedError("SupabaseUserStateProvider is a skeleton.")

    async def update_user_state(self, *, state: UserState) -> None:  # pragma: no cover
        raise NotImplementedError("SupabaseUserStateProvider is a skeleton.")
