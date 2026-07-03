# Status

## Current milestone

M2 complete (local JSONL retrieval + mock vertical slice). M3/M4 provider
adapters (OpenRouter, Bedrock) are implemented and unit-tested but not yet
smoke-tested against real vendor APIs.

## Status legend

- `skeleton` — interface/stub only, not functional.
- `adapter_offline_ready` — implemented and unit-tested against mocked
  responses; not yet exercised against the real vendor.
- `provider_smoke_tested` — has made at least one successful real call
  against the vendor's API in a controlled test.
- `production_ready` — ready for local/test/demo use. Does not imply a
  hosted deployment exists.

## Implemented adapters

| Component | Backend | Status |
| --- | --- | --- |
| LLM | `mock` | `production_ready` |
| LLM | `openrouter` | `adapter_offline_ready` |
| LLM | `bedrock_converse` | `adapter_offline_ready` |
| LLM | `ollama` | `skeleton` |
| Retrieval | `mock` | `production_ready` |
| Retrieval | `local` | `production_ready` |
| Retrieval | `bedrock_kb` | `adapter_offline_ready` |
| RAG | `local_pipeline` | `production_ready` |
| RAG | `bedrock_retrieve_and_generate` | `adapter_offline_ready` |
| User state | in-memory | `production_ready` |
| User state | `dynamodb` / `supabase` | `skeleton` |
| Deployment | — | documented, not provisioned |

## Not smoke-tested against real providers

- OpenRouter (`openrouter_api_key` unset in CI; tests cover payload
  construction and response parsing against fixtures only).
- Bedrock Converse, Knowledge Bases, RetrieveAndGenerate (tests mock the
  boto3 client; no real AWS calls have been made from this repo).

## Known gaps

- No embeddings-based retrieval — `local` retrieval is keyword matching over
  JSONL.
- Persistent user state (`dynamodb`, `supabase`) is unimplemented.
- Ollama LLM backend is unimplemented.
- No deployment infrastructure (containers, IaC, CI/CD) exists yet.
- No frontend.

## Next recommended milestone

Smoke-test the OpenRouter adapter against the real API with a throwaway key,
behind a manual/opt-in test marker — this validates the adapter layer end to
end before investing in Bedrock credentials and AWS test infrastructure.
