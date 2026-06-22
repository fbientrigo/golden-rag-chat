# 0001 — Bedrock-first, but not Bedrock-locked

- Status: Accepted
- Date: 2026-01

## Context

Production will likely run on AWS Bedrock (Converse, Knowledge Bases,
RetrieveAndGenerate). But we also need a cheap token-based MVP (OpenRouter), local
inference later (Ollama), and a fully offline test path. Coupling business logic
directly to Bedrock would make all of that hard and lock us in.

## Decision

Treat Bedrock as **adapters behind interfaces**, not as the architecture:

- `BedrockConverseLLM` implements `LLMProvider`.
- `BedrockKnowledgeBaseRetrieval` implements `RetrievalProvider`.
- `BedrockRetrieveAndGenerate` implements `RAGProvider` (managed single call).

No core module imports `boto3`; it is an optional extra (`.[bedrock]`). The default
configuration uses mock/local providers and runs offline. Bedrock specifics
(client names, request/response shapes) were verified against current AWS docs and
are documented in `docs/deployment.md`.

## Consequences

- We can ship an MVP and run CI without any AWS account.
- Swapping or adding a model backend touches one provider + the factory, nothing
  else.
- Slight indirection cost: provider Protocols and a factory. Worth it.
- We must keep Bedrock request/response mappings (e.g. `system` blocks for
  Converse, `retrievedReferences` for RetrieveAndGenerate) current; the deprecated
  `citation` member is explicitly avoided.
