# 0003 — Provider architecture

- Status: Accepted
- Date: 2026-01

## Context

We must serve two domains and several interchangeable backends (retrieval, LLM,
combined RAG, user state) while keeping the codebase small, testable, and free of
domain- or vendor-specific assumptions in the core.

## Decision

Every external concern is a **Protocol** with multiple implementations, selected at
runtime by a `ProviderFactory` from names in a central capability registry
(`config.py`):

- `RetrievalProvider` — `mock`, `local`, `bedrock_kb`.
- `LLMProvider` — `mock`, `openrouter`, `bedrock_converse`, `ollama`.
- `RAGProvider` — `local_pipeline`, `bedrock_retrieve_and_generate`.
- `UserStateProvider` — in-memory, `dynamodb`, `supabase`.
- `GoldenDataSource` — `local_jsonl`, `local_parquet`, (future cloud).

Domains are a parallel strategy (`DomainAdapter`) holding all domain-specific text.
The registry distinguishes *registered* names (advertised by `/capabilities`) from
*enabled* names (`IMPLEMENTED_*`): unknown → `400 unsupported_backend`,
registered-but-disabled → `501 provider_not_configured`. Tests run entirely on the
mock/local implementations, with pure helpers (e.g. OpenRouter payload builder,
Converse message mapping) unit-tested without network.

## Consequences

- New domain = one adapter + fixtures; new backend = one provider + a registry/
  factory entry. The core, the service, and the routes do not change.
- The contract is explicit and discoverable via `/capabilities` and clear errors.
- Cost: some boilerplate (Protocols, factory, skeletons). Acceptable for the
  flexibility and testability gained.
- Risk: registry and factory can drift from reality; the `IMPLEMENTED_*` gate plus
  tests keep advertised-vs-working honest.
