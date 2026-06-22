# golden-rag-chat

A small, reusable **Golden-Data RAG chatbot backend**. One stable HTTP service
serves multiple domains over curated *golden data*:

- **Apolo** — AI career/job matching (graduate profiles, labor-market data, role
  families, skill gaps, salary/geography).
- **Agriculture** (SbnAI / SevenEye-like) — agronomic advisory (farm state,
  crops, weather/frost/humidity/fungal risk, agronomic reports).

Both are the same abstract problem: *user state + curated golden data → retrieve
evidence → ground an LLM answer → return it with citations.* The core is
domain-neutral; everything project- or vendor-specific lives behind a provider
interface.

> **Design principle: Bedrock-first, but not Bedrock-locked.** Bedrock Converse,
> Knowledge Bases, and RetrieveAndGenerate are each *one* implementation of a
> provider Protocol — swappable for OpenRouter, Ollama, or local retrieval. The
> default configuration runs **fully offline** with mock providers.

This repo owns **only the chatbot API and contracts**. It does **not** scrape,
clean, train, or regenerate golden data — that is produced by upstream pipelines
and consumed here read-only. No frontend framework lives here.

## Quickstart

Requires Python ≥ 3.11 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                              # create .venv and install deps + dev tools
uv run ruff check .                  # lint
uv run pytest                        # run the offline test suite
uv run uvicorn golden_rag_chat.api.main:app --reload   # serve on :8000
```

All tests pass with **no network, no AWS, no model downloads**.

### Try the API

```bash
curl localhost:8000/health
curl localhost:8000/capabilities

curl -s localhost:8000/chat -H 'content-type: application/json' -d '{
  "domain": "apolo",
  "user_id": "demo-user",
  "question": "What skills am I missing for data engineering roles?",
  "context": {"target_role_family": "Data & Analytics Engineering"},
  "options": {"retrieval_backend": "local", "llm_backend": "mock", "rag_backend": "local_pipeline"}
}'
```

## API

| Method | Path             | Purpose                                            |
| ------ | ---------------- | -------------------------------------------------- |
| GET    | `/health`        | Liveness.                                          |
| GET    | `/capabilities`  | Advertised domains and backends.                   |
| POST   | `/chat`          | Grounded answer with citations + diagnostics.      |

Full request/response shapes: [`docs/api_contract.md`](docs/api_contract.md).

## Architecture at a glance

```
client ──HTTP──▶ FastAPI (/chat)
                   │
                   ▼
              ChatService ──▶ ProviderFactory ──▶ RAGProvider
                   │                                  │
         UserStateProvider                            ▼
                                       RetrievalProvider + LLMProvider
                                                      │
                                         GoldenDataSource (read-only)
```

- **Retrieval** (`RetrievalProvider`): `mock`, `local` (keyword over JSONL),
  `bedrock_kb` *(skeleton)*.
- **LLM** (`LLMProvider`): `mock`, `openrouter` *(skeleton)*, `bedrock_converse`
  *(skeleton)*, `ollama` *(skeleton)*.
- **RAG** (`RAGProvider`): `local_pipeline`, `bedrock_retrieve_and_generate`
  *(skeleton)*.
- **User state** (`UserStateProvider`): in-memory, `dynamodb`/`supabase`
  *(skeletons)*.
- **Domains** (`DomainAdapter`): `apolo`, `agriculture` — all domain-specific
  prompt/persona/state-rendering logic lives here, not in the core.

More: [`docs/architecture.md`](docs/architecture.md),
[`docs/data_contracts.md`](docs/data_contracts.md),
[`docs/deployment.md`](docs/deployment.md), and the ADRs in
[`docs/adr/`](docs/adr/).

## Enabling more backends

The capability registry in `config.py` lists every backend name; the
`IMPLEMENTED_*` sets gate which ones are wired. Today: `mock` + `local`
retrieval, `mock` LLM, `local_pipeline` RAG. Requesting a registered-but-disabled
backend returns `501 provider_not_configured`; an unknown name returns
`400 unsupported_backend`. To enable one, implement its provider, add it to the
factory and the `IMPLEMENTED_*` set, and supply config via `GRC_*` env vars.

Cloud/heavy deps are optional extras: `uv pip install -e '.[bedrock]'` (boto3),
`'.[parquet]'` (pyarrow).

## Milestones

- **M0** specs/contracts/ADRs — done.
- **M1** mock vertical slice (`/health`, `/capabilities`, `/chat`, mock
  providers, in-memory state) — done.
- **M2** local JSONL keyword retrieval — done (no embeddings).
- **M3** OpenRouter LLM — skeleton (testable payload builder).
- **M4** Bedrock Converse / KB / RetrieveAndGenerate — skeletons.
- **M5** deployment — documented, not provisioned.

## Security

API keys and AWS credentials stay server-side and are never returned by the API
or exposed to the frontend. Ollama is never exposed publicly. User state is
isolated per `(domain, user_id)`. RAG answers include sources; with insufficient
evidence the assistant says so rather than fabricating.
