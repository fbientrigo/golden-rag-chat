# Architecture

## The shared problem

Apolo (career matching) and the agriculture advisor look like different products
but are the same pipeline:

```
user state  +  curated golden data  ──▶  retrieve evidence  ──▶  ground an LLM
                                                                      │
                                                  answer + citations ◀┘
```

So the core is written **once**, domain-neutral, and the differences (persona,
how user state reads, which metadata matters) are isolated behind a
`DomainAdapter`. Vendor differences (Bedrock vs OpenRouter vs Ollama vs local)
are isolated behind provider Protocols.

## Components

```
                         ┌─────────────────────────────────────────────┐
   client ──HTTP──▶ FastAPI app (api/main.py)                          │
                         │  /health  /capabilities  /chat               │
                         ▼                                              │
                   ChatService (chat/service.py)                        │
                    │   - resolve options vs defaults                   │
                    │   - load user state                              ─┼─▶ UserStateProvider
                    │   - build RAGProvider via ProviderFactory         │     (memory | dynamodb | supabase)
                    ▼                                                   │
                 RAGProvider (rag/)                                     │
          ┌─────────────────────────────┬───────────────────────────┐  │
          ▼                             ▼                           │  │
   LocalRAGPipeline            BedrockRetrieveAndGenerate           │  │
   (compose retrieval+llm)     (managed single call) [skeleton]     │  │
          │                                                         │  │
   ┌──────┴───────┐                                                 │  │
   ▼              ▼                                                 │  │
 RetrievalProvider  LLMProvider                                     │  │
 (mock|local|       (mock|openrouter|                               │  │
  bedrock_kb)        bedrock_converse|ollama)                       │  │
   │                                                                │  │
   ▼                                                                │  │
 GoldenDataSource (golden_data/) ── read-only ──────────────────────┘  │
 (local_jsonl | local_parquet | future: S3 / KB export)               │
                         └─────────────────────────────────────────────┘
   prompt_builder + source_formatter (chat/)   DomainAdapter (domains/)
```

### Layer responsibilities

- **api/** — HTTP only: validate, delegate, map errors to status codes. No logic.
- **chat/service.py** — orchestration: option resolution, user-state load,
  provider selection, delegation. Branches on **nothing** domain-specific and
  does not know which backend it built.
- **rag/** — combined retrieve+generate. `LocalRAGPipeline` composes a retrieval
  and an LLM provider; the Bedrock managed path is an alternative implementation.
- **retrieval/**, **llm/**, **user_state/**, **golden_data/** — provider
  Protocols + implementations. Each external concern is swappable in isolation.
- **domains/** — the only place with Apolo/agriculture-specific text.
- **config.py** — `Settings` (env) + the capability registry (single source of
  truth for backend names).

## Request flow (`POST /chat`)

1. FastAPI validates the body into `ChatRequest`.
2. `ChatService` fills unset options from `Settings` defaults and copies them back
   onto the request (so diagnostics report the *actual* backends used).
3. It loads `UserState` for `(domain, user_id)` (may be `None`).
4. `ProviderFactory.build_rag(...)` validates backend names against the registry
   (unknown → 400, registered-but-disabled → 501) and constructs the provider.
5. `LocalRAGPipeline.answer(...)`:
   - retrieves up to `max_sources` `RetrievedSource`s;
   - **if none**, returns the domain's insufficiency message with no sources
     (never calls the model — avoids fabrication);
   - else builds messages (`prompt_builder`), calls the LLM, and projects sources
     to citation `Source`s (`source_formatter`).
6. Returns `ChatResponse { answer, sources[], diagnostics }`.

## Key boundaries (and why)

- **Golden-data boundary** — this service only *reads* golden data. Ingestion,
  cleaning, embedding, and validation belong to upstream pipelines. See
  [ADR-0002](adr/0002-golden-data-boundary.md).
- **Bedrock as an adapter** — no core module imports boto3. Bedrock is three
  provider implementations. See
  [ADR-0001](adr/0001-bedrock-first-not-bedrock-locked.md) and
  [ADR-0003](adr/0003-provider-architecture.md).
- **Internal vs wire types** — `RetrievedSource` (full text, internal) is distinct
  from `Source` (excerpt, public) so internals can change without breaking
  clients.
- **No secrets cross the boundary** — keys/creds live in server env; the API never
  returns them; the frontend never holds them.

## Scale & reliability notes

The service is **stateless** per request (user state lives in an external
provider), so it scales horizontally behind a load balancer; run ≥2 replicas for
availability. Latency is dominated by the LLM/RAG backend, not this code. Local
keyword retrieval is in-memory per process and fine for small/medium golden-data
sets; large corpora should move to a vector backend (Bedrock KB / S3 Vectors /
OpenSearch) behind the same `RetrievalProvider` interface — no core change.

## What I'd revisit as it grows

- Add conversation history/memory (multi-turn) — currently single-turn; the
  `session_id` is carried but not yet used to thread context.
- Add a reranking step in `LocalRAGPipeline` (interface already allows it).
- Promote `IMPLEMENTED_*` gating to per-deployment config once more backends ship.
- Add request auth/rate-limiting once the contract stabilizes (intentionally out
  of M1 scope).
