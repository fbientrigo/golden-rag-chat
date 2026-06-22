# API contract

Base URL: the deployed service root. All bodies are JSON. The API is versionless
for now (M1); breaking changes will be versioned once the contract stabilizes.

## `GET /health`

Liveness probe.

```json
{ "status": "ok", "service": "golden-rag-chat" }
```

## `GET /capabilities`

Advertises supported domains and backend names. Names listed here may be
*registered but not yet enabled* in a given build (see the error model).

```json
{
  "domains": ["apolo", "agriculture"],
  "retrieval_backends": ["mock", "local", "bedrock_kb"],
  "llm_backends": ["mock", "openrouter", "bedrock_converse", "ollama"],
  "rag_backends": ["local_pipeline", "bedrock_retrieve_and_generate"]
}
```

## `POST /chat`

### Request

| Field         | Type           | Required | Notes                                              |
| ------------- | -------------- | -------- | -------------------------------------------------- |
| `domain`      | enum           | yes      | `apolo` \| `agriculture`.                          |
| `user_id`     | string         | yes      | Used with `domain` to load user state.             |
| `session_id`  | string         | no       | Carried for future multi-turn threading.           |
| `question`    | string         | yes      | Non-empty.                                         |
| `context`     | object         | no       | Free-form; values boost retrieval and feed prompt. |
| `options`     | object         | no       | Backend selection (below); unset → server default. |

`options`:

| Field               | Type   | Default (server)   | Notes                                  |
| ------------------- | ------ | ------------------ | -------------------------------------- |
| `retrieval_backend` | string | `mock`             | One of `retrieval_backends`.           |
| `llm_backend`       | string | `mock`             | One of `llm_backends`.                 |
| `rag_backend`       | string | `local_pipeline`   | One of `rag_backends`.                 |
| `max_sources`       | int    | `5`                | 1–50.                                  |

```json
{
  "domain": "apolo",
  "user_id": "demo-user",
  "session_id": "demo-session",
  "question": "What skills am I missing for data engineering roles?",
  "context": { "career_id": "uchile-ingcivil", "target_role_family": "Data & Analytics Engineering" },
  "options": { "retrieval_backend": "local", "llm_backend": "mock", "rag_backend": "local_pipeline", "max_sources": 5 }
}
```

### Response `200`

```json
{
  "answer": "Based on the current golden data ...",
  "sources": [
    {
      "source_id": "apolo-skill-gap-001",
      "source_type": "skill_gap",
      "title": "Data & Analytics Engineering skill gap summary",
      "uri": "golden://apolo/skill_gap/001",
      "metadata": { "domain": "apolo", "role_family": "Data & Analytics Engineering", "tier": "gold" },
      "excerpt": "The most frequent missing skills are SQL, Python, ETL, cloud, and dashboarding..."
    }
  ],
  "diagnostics": {
    "domain": "apolo",
    "retrieval_backend": "local",
    "llm_backend": "mock",
    "rag_backend": "local_pipeline",
    "num_sources": 1
  }
}
```

Guarantees:

- `sources` reflects the evidence actually used; `[S#]` labels in `answer`
  correspond to source order.
- **Insufficient evidence** → `200` with `sources: []` and an answer that says so
  (the service does not fabricate). `diagnostics.num_sources` is `0`.

### Error model

Errors return a JSON body:

```json
{ "error": "unsupported_backend", "detail": "Unknown retrieval backend 'foo'. Supported: mock, local, bedrock_kb." }
```

| Status | `error`                   | When                                                        |
| ------ | ------------------------- | ----------------------------------------------------------- |
| 400    | `unsupported_backend`     | A backend name not in the capability registry.              |
| 400    | `domain_not_found`        | A domain with no registered adapter.                        |
| 422    | (FastAPI validation)      | Malformed body (missing/empty `question`, bad enum, …).     |
| 501    | `provider_not_configured` | A registered backend that is not enabled / missing config.  |
| 500    | `internal_error`          | Unexpected server error.                                    |
