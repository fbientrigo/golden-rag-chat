"""Dependency wiring for the API.

Builds the object graph once (cached) and exposes FastAPI dependency callables.
Swapping a provider for production is a change *here* only — routes and the
service stay untouched.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from golden_rag_chat.chat.service import ChatService, ProviderFactory
from golden_rag_chat.config import SUPPORTED_DOMAINS, Settings, get_settings
from golden_rag_chat.domains import DomainRegistry, default_registry
from golden_rag_chat.golden_data.local_jsonl import LocalJsonlGoldenData
from golden_rag_chat.logging import get_logger
from golden_rag_chat.user_state.base import UserState
from golden_rag_chat.user_state.memory import InMemoryUserStateProvider

logger = get_logger(__name__)


def _seed_user_states(base_dir: Path) -> list[UserState]:
    """Best-effort: load ``<base_dir>/<domain>/user_state.json`` for each domain."""
    seeds: list[UserState] = []
    for domain in SUPPORTED_DOMAINS:
        path = base_dir / domain / "user_state.json"
        if not path.exists():
            continue
        try:
            seeds.append(UserState.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        except Exception as exc:  # noqa: BLE001
            logger.warning("could not seed user state from %s: %s", path, exc)
    return seeds


@lru_cache
def get_domain_registry() -> DomainRegistry:
    return default_registry()


@lru_cache
def get_chat_service() -> ChatService:
    settings: Settings = get_settings()
    golden_data = LocalJsonlGoldenData(settings.golden_data_dir)
    user_state_provider = InMemoryUserStateProvider(seed=_seed_user_states(settings.golden_data_dir))
    factory = ProviderFactory(
        settings=settings,
        domains=get_domain_registry(),
        golden_data=golden_data,
    )
    return ChatService(
        settings=settings,
        factory=factory,
        user_state_provider=user_state_provider,
    )
