# LLM / Provider Wiki

State of the provider layer and how to extend it. Read this before adding or
debugging a backend. Last updated: M4 (2026-06-22).

## State at a glance

| Kind | Backend | Status | Implementation |
|------|---------|--------|----------------|
| LLM | `mock` | ✅ done | `llm/mock.py` — deterministic, grounded, offline |
| LLM | `openrouter` | ✅ done (M3) | `llm/openrouter.py` — httpx, injectable client |
| LLM | `bedrock_converse` | ✅ done (M4) | `llm/bedrock_converse.py` — boto3 `converse`, injectable client |
| LLM | `ollama` | 🔩 skeleton | `llm/ollama.py` |
| Retrieval | `mock` | ✅ done | `retrieval/mock.py` |
| Retrieval | `local` | ✅ done (M2) | `retrieval/local.py` — keyword over JSONL |
| Retrieval | `bedrock_kb` | ✅ done (M4) | `retrieval/bedrock_kb.py` — boto3 `retrieve` |
| RAG | `local_pipeline` | ✅ done | `rag/local_pipeline.py` — composes retrieval + LLM |
| RAG | `bedrock_retrieve_and_generate` | ✅ done (M4) | `rag/bedrock_retrieve_and_generate.py` — managed single call |

"Done" = wired into the factory, in the `IMPLEMENTED_*` registry, and covered by
offline tests. Skeletons raise `NotImplementedError` / `ProviderNotConfiguredError`.

Single source of truth for what's enabled: `IMPLEMENTED_*` frozensets in
`config.py`. `/capabilities` and the factory both read the registry — they can't
drift.

## The contracts

- `LLMProvider.generate(*, messages, sources, options) -> LLMResponse` — `llm/base.py`
- `RetrievalProvider.retrieve(*, domain, question, user_state, context, max_sources) -> list[RetrievedSource]` — `retrieval/base.py`
- `RAGProvider.answer(*, request, user_state) -> ChatResponse` — `rag/base.py`

Two implementation shapes for RAG: **composed** (`local_pipeline` wires a
retrieval + an LLM provider, owns prompt building + source formatting) and
**managed** (`bedrock_retrieve_and_generate` delegates retrieval+generation to one
external call and maps its citations back to our `Source` schema).

`RetrievedSource` (internal, full text) is distinct from `Source` (wire, excerpt
only). Never leak full text or secrets to the wire.

## The established pattern (follow it for every new backend)

Every real provider is built the same way, so tests stay fully offline:

1. **Pure mapper functions** at module level — request builder and response
   mapper. No I/O, unit-testable directly.
   - OpenRouter: `build_payload`
   - Bedrock Converse: `to_converse_messages`, `to_inference_config`, `from_converse_response`
   - Bedrock KB: `location_uri`, `from_retrieval_results`
   - Bedrock RAG: `from_rag_response`
2. **Injectable client** on the provider (`client=` ctor arg). Tests inject a
   mock; production passes `None` and the provider builds the real one.
   - httpx providers: inject `AsyncMock(spec=httpx.AsyncClient)`.
   - boto3 providers: `_ensure_client()` returns the injected client if present,
     else lazily imports boto3 + constructs it. Tests inject a `MagicMock`.
3. **Config guard** — missing key/id raises `ProviderNotConfiguredError` (→ 501).
4. **Factory branch** in `chat/service.py` (`build_llm` / `build_retrieval` /
   `build_rag`), reading settings from `config.py`.
5. **Enable** by adding the name to the matching `IMPLEMENTED_*` set.
6. **Tests** mirroring `tests/test_llm_openrouter.py` / `tests/test_llm_bedrock.py`.

### boto3 specifics

- boto3 is an **optional extra** (`pip install -e '.[bedrock]'`) — never installed
  in the default test env, so tests provably can't hit AWS.
- boto3 calls are **synchronous**. Each `async def` wraps the call in
  `asyncio.to_thread(client.method, …)` so the event loop isn't blocked for the
  multi-second model latency. A `MagicMock` works transparently under `to_thread`.
- `_ensure_client()` lazy-imports boto3 inside the method (`# noqa: PLC0415`), so
  importing the module never requires boto3.

## Error mapping (`errors.py` → `api/errors.py`)

| Situation | Exception | HTTP |
|-----------|-----------|------|
| Unknown backend name | `UnsupportedBackendError` | 400 `unsupported_backend` |
| Registered but disabled / missing config | `ProviderNotConfiguredError` | 501 `provider_not_configured` |
| Unknown domain | `DomainNotFoundError` | 400 `domain_not_found` |

"Enabled but unconfigured" (e.g. `bedrock_converse` with no `GRC_BEDROCK_MODEL_ID`)
reaches the provider and raises `ProviderNotConfiguredError` → 501. This is the
intended, consistent behavior — the registry accepts it; config is what's missing.

## Configuration (env, `GRC_` prefix — see `config.py`)

- OpenRouter: `GRC_OPENROUTER_API_KEY`, `GRC_OPENROUTER_MODEL`,
  `GRC_OPENROUTER_BASE_URL`, `GRC_OPENROUTER_SITE_URL`, `GRC_OPENROUTER_APP_NAME`
- Bedrock: `GRC_AWS_REGION`, `GRC_BEDROCK_MODEL_ID`, `GRC_BEDROCK_KNOWLEDGE_BASE_ID`
- Ollama (skeleton): `GRC_OLLAMA_BASE_URL`, `GRC_OLLAMA_MODEL`

Secrets live in server env only; never returned by the API, never logged, never
sent to the frontend.

## Known simplifications / upgrade paths (ponytail debt)

- **Bedrock KB metadata filter** — not implemented. `bedrock_kb` passes
  `numberOfResults` only; no `context` → `vectorSearchConfiguration["filter"]`
  translation yet (needs a real KB metadata schema). Marked with a `ponytail:`
  comment in `retrieval/bedrock_kb.py`.
- **No streaming** anywhere — `converse_stream` / `retrieve_and_generate_stream`
  and OpenRouter SSE are out of scope. The contract returns a full `LLMResponse` /
  `ChatResponse`.
- **No real-AWS / real-network integration tests** — the default suite is offline.
  A real smoke test belongs in a separate opt-in `[bedrock]` CI job.
- **Sync SDK + `to_thread`**, not an async AWS SDK (aioboto3 would be a new heavy
  dep for one call).

## Next milestone

M5 — deployment (`docs/deployment.md`). Optional: implement `ollama` (same
pattern, httpx, no auth) and add the opt-in Bedrock integration test.
