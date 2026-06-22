"""DynamoDB user-state provider (skeleton).

Suggested key design for per-(domain, user_id) isolation:
- Partition key ``pk`` = ``"{domain}#{user_id}"``
- Sort key ``sk``     = ``"state"``
Store the ``UserState`` JSON as item attributes. No AWS calls in the default tests.
"""

from __future__ import annotations

from typing import Any

from golden_rag_chat.errors import ProviderNotConfiguredError
from golden_rag_chat.user_state.base import UserState


class DynamoDBUserStateProvider:
    def __init__(self, *, table_name: str | None, region: str | None, client: Any = None):
        self._table_name = table_name
        self._region = region
        self._client = client

    def _ensure_client(self) -> Any:  # pragma: no cover - skeleton
        if self._client is not None:
            return self._client
        if not self._table_name:
            raise ProviderNotConfiguredError("DynamoDB table name is not configured.")
        try:
            import boto3  # noqa: PLC0415 - optional dependency
        except ImportError as exc:  # pragma: no cover
            raise ProviderNotConfiguredError("boto3 is required. Install the 'aws' extra.") from exc
        self._client = boto3.client("dynamodb", region_name=self._region)
        return self._client

    async def get_user_state(self, *, domain: str, user_id: str) -> UserState | None:  # pragma: no cover
        raise NotImplementedError("DynamoDBUserStateProvider is a skeleton.")

    async def update_user_state(self, *, state: UserState) -> None:  # pragma: no cover
        raise NotImplementedError("DynamoDBUserStateProvider is a skeleton.")
