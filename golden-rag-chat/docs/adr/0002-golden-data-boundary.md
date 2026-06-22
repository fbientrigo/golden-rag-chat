# 0002 — Golden-data boundary

- Status: Accepted
- Date: 2026-01

## Context

Golden data (graduate profiles, labor-market summaries, agronomic reports, weather
signals) is produced by separate upstream pipelines that scrape, clean, validate,
and version it. If the chatbot also tried to own ingestion, the two responsibilities
would entangle and the chatbot would become a monolith tied to data-engineering
concerns.

## Decision

The chatbot consumes golden data **read-only**. It does not scrape, clean, train,
embed, or regenerate it. The contract between the pipeline and the chatbot is the
`GoldenChunk` model plus the on-disk/remote layout. Access is via a
`GoldenDataSource` interface (`local_jsonl` now; S3 / KB export / DB later).

Invalid records are logged and skipped, never repaired in place — fixing data is
the pipeline's job.

## Consequences

- Clear ownership: pipelines own data quality; the chatbot owns retrieval +
  grounding + API.
- The chatbot can point at fixtures, a local export, or a cloud source without code
  changes.
- Upstream schema changes are absorbed in `metadata` (open dict) where possible;
  structural changes are a deliberate contract change to `GoldenChunk`.
- The chatbot must trust the `gold` tier; it does not re-validate data semantics,
  only structural shape.
