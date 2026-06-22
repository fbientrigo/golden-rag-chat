# Deployment

Design-only for M5: paths and trade-offs, not provisioned infrastructure. No
Terraform yet (add when requested).

## Local

```bash
uv sync
uv run uvicorn golden_rag_chat.api.main:app --host 0.0.0.0 --port 8000
```

Docker (sketch): a slim Python base, `uv sync --no-dev`, run uvicorn. A Compose
file can add the API plus, later, a local Ollama container (kept on a private
network — never published).

## Configuration (env vars, prefix `GRC_`)

| Var                            | Purpose                                         |
| ------------------------------ | ----------------------------------------------- |
| `GRC_GOLDEN_DATA_DIR`          | Root of local golden data.                      |
| `GRC_DEFAULT_*_BACKEND`        | Default retrieval/llm/rag backend.              |
| `GRC_OPENROUTER_API_KEY`       | OpenRouter key (server-side only).              |
| `GRC_AWS_REGION`               | Region for Bedrock clients.                     |
| `GRC_BEDROCK_MODEL_ID`         | Converse / generation model (id or ARN).        |
| `GRC_BEDROCK_KNOWLEDGE_BASE_ID`| Knowledge Base id for KB / RetrieveAndGenerate. |

Secrets come from the platform's secret manager (SSM/Secrets Manager, container
secrets) — never committed, never returned by the API, never shipped to the
frontend.

## AWS-native path

| Concern    | Option                                                                       |
| ---------- | ---------------------------------------------------------------------------- |
| API        | App Runner or ECS Fargate (always-on container). Lambda only if **no** local model is hosted and cold-start/latency are acceptable. |
| Golden data| S3 (and/or a Bedrock Knowledge Base built from S3).                           |
| User state | DynamoDB (`pk = "{domain}#{user_id}"`) or Aurora/Supabase Postgres.          |
| Retrieval  | Bedrock Knowledge Bases (`Retrieve`).                                         |
| RAG        | Bedrock `RetrieveAndGenerate` (managed) **or** local pipeline + Converse.     |
| Model      | Bedrock Converse / RetrieveAndGenerate.                                       |

Because each maps to a provider interface, you can adopt them incrementally:
start `mock`/`local`, move user state to DynamoDB, then swap retrieval to KB, then
the LLM to Converse — one provider at a time, no core changes.

## Bedrock notes (verified against AWS docs, June 2026)

- **Converse / ConverseStream** (`bedrock-runtime`) is the recommended multi-turn
  interface across models. `system` is a separate list of `{ "text": ... }`
  blocks (not a message role); `messages` use `content: [{ "text": ... }]`;
  `inferenceConfig` carries `maxTokens`/`temperature`/`topP`; the response is a
  normalized envelope (`output.message.content[].text`, `stopReason`, `usage`).
- **Knowledge Bases** support managed RAG over private data with `Retrieve`
  (chunks only) and `RetrieveAndGenerate` (answer + citations), via
  `bedrock-agent-runtime`. `RetrieveAndGenerate` returns `output.text`,
  `citations[].retrievedReferences[]`, and a `sessionId` to continue the
  conversation. The older top-level `citation` member is **deprecated** — map
  `retrievedReferences` instead.
- **Vector store**: S3 Vectors is a native low-cost option (semantic search only;
  ~1 KB custom metadata / 35 keys per vector). OpenSearch Serverless, Aurora,
  Pinecone, etc. are also supported. Confirm the current region/model/store
  support before provisioning.
- **Guardrails** may not sanitize raw retrieved references, so we keep
  application-level source filtering when mapping references → `Source`.

> Model IDs, Knowledge Base APIs, regions, and vector-store options change — verify
> in the AWS console/docs at implementation time.

## IAM (least privilege, documented separately from code)

- Converse: `bedrock:InvokeModel` (and `bedrock:InvokeModelWithResponseStream`
  for streaming) on the specific model/inference-profile ARNs.
- Knowledge Bases: `bedrock:Retrieve` and/or `bedrock:RetrieveAndGenerate` on the
  KB ARN; the KB's own service role needs read access to the S3 data source and
  the vector store.
- DynamoDB: `GetItem`/`PutItem`/`UpdateItem` on the table ARN only.
- Scope every statement to specific resource ARNs; prefer instance/task roles over
  static keys. Keep vector stores/databases in a VPC with PrivateLink endpoints.

## Health & ops

`GET /health` for load-balancer checks; run ≥2 replicas. The service is stateless
per request, so scaling is horizontal. Watch p50/p95 latency of the chosen
LLM/RAG backend (the dominant cost) and retrieval result counts.
