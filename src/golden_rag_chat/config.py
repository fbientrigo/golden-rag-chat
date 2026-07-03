"""Application configuration and the capability registry.

`Settings` is environment-driven (12-factor). The capability lists below are the
single source of truth for which backend names exist; `/capabilities`, the
provider factories, and the docs all read from here so they cannot drift apart.

Secrets (API keys, AWS creds) live only in the server environment. They are
never returned by the API and never sent to the frontend.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICE_NAME = "golden-rag-chat"

# --- Capability registry -------------------------------------------------------
# Names advertised by GET /capabilities. "implemented" backends work today;
# the rest are wired as adapters/skeletons and raise a clear error until built.
SUPPORTED_DOMAINS: tuple[str, ...] = ("apolo", "agriculture")
RETRIEVAL_BACKENDS: tuple[str, ...] = ("mock", "local", "bedrock_kb")
LLM_BACKENDS: tuple[str, ...] = ("mock", "openrouter", "bedrock_converse", "ollama")
RAG_BACKENDS: tuple[str, ...] = ("local_pipeline", "bedrock_retrieve_and_generate")

IMPLEMENTED_RETRIEVAL_BACKENDS: frozenset[str] = frozenset({"mock", "local", "bedrock_kb"})
IMPLEMENTED_LLM_BACKENDS: frozenset[str] = frozenset({"mock", "openrouter", "bedrock_converse"})
IMPLEMENTED_RAG_BACKENDS: frozenset[str] = frozenset(
    {"local_pipeline", "bedrock_retrieve_and_generate"}
)


class Settings(BaseSettings):
    """Server configuration, read from environment variables (prefix ``GRC_``)."""

    model_config = SettingsConfigDict(env_prefix="GRC_", env_file=".env", extra="ignore")

    service_name: str = SERVICE_NAME

    # Defaults applied when a /chat request omits options.
    default_retrieval_backend: str = "mock"
    default_llm_backend: str = "mock"
    default_rag_backend: str = "local_pipeline"
    default_max_sources: int = 5

    # Local golden-data root: <golden_data_dir>/<domain>/golden_chunks.jsonl.
    # Defaults to the bundled fixtures so a fresh checkout serves /chat with the
    # `local` backend out of the box. Override in real deployments.
    golden_data_dir: Path = Path("tests/fixtures")

    # --- OpenRouter ---
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_site_url: str | None = None
    openrouter_app_name: str | None = None

    # --- Ollama (later) ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # --- Bedrock (M4 skeleton) ---
    aws_region: str | None = None
    bedrock_model_id: str | None = None  # e.g. an inference profile / model ARN
    bedrock_knowledge_base_id: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
