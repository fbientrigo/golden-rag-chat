# Data contracts

Two generic models carry all domains. Domain specifics live in open `metadata` /
`profile` dicts so the core never needs domain knowledge. The chatbot **reads**
these; it never produces or mutates golden data.

## `GoldenChunk`

The unit of evidence. Validated on load; unknown **top-level** fields are rejected
(`extra="forbid"`), but `metadata` is free-form.

```json
{
  "chunk_id": "string",
  "domain": "apolo | agriculture",
  "text": "string",
  "source_type": "career_profile | job_market_summary | skill_gap | farm_state | crop_risk_report | weather_summary | agronomic_report",
  "title": "string",
  "uri": "string",
  "metadata": { "tier": "gold", "version": "string", "created_at": "ISO-8601" }
}
```

Common `metadata` keys: `tier` (always `gold`), `version`, `created_at`, plus
domain keys.

**Apolo metadata**

```json
{ "career_id": "uchile-ingcivil", "institution": "Universidad de Chile",
  "role_family": "Data & Analytics Engineering", "country": "Chile", "region": "RM",
  "salary_band": "optional", "centroid_id": "optional" }
```

**Agriculture metadata**

```json
{ "farm_id": "demo-farm", "region": "Coquimbo", "crop": "grape",
  "risk_type": "frost | humidity | fungal | irrigation", "season": "2026" }
```

## `UserState`

Per `(domain, user_id)`. Never shared across domains.

```json
{
  "user_id": "string",
  "domain": "apolo | agriculture",
  "profile": {},
  "preferences": {},
  "current_context": {},
  "chat_summary": "optional string",
  "updated_at": "ISO-8601"
}
```

**Apolo example**

```json
{ "user_id": "demo-user", "domain": "apolo",
  "profile": { "selected_career": "uchile-ingcivil", "known_skills": ["Python", "statistics"],
               "target_roles": ["Data Analyst", "Data Engineer"] },
  "preferences": { "locations": ["Santiago", "Valparaíso"], "remote_ok": true },
  "current_context": { "selected_role_family": "Data & Analytics Engineering" } }
```

**Agriculture example**

```json
{ "user_id": "demo-farm-user", "domain": "agriculture",
  "profile": { "farm_id": "farm-001", "region": "Coquimbo", "crops": ["grape", "avocado"] },
  "preferences": { "risk_focus": ["frost", "fungal"] },
  "current_context": { "selected_crop": "grape", "recent_symptom": "leaf spots after humid week" } }
```

## On-disk layout (local sources)

```
<golden_data_dir>/
  apolo/
    golden_chunks.jsonl      # one GoldenChunk JSON object per line
    user_state.json          # optional seed for the in-memory provider
    careers.json             # optional domain reference data
  agriculture/
    golden_chunks.jsonl
    user_state.json
    farms.json
```

`golden_data_dir` is `GRC_GOLDEN_DATA_DIR` (defaults to `tests/fixtures` so a
fresh checkout works). The Parquet source expects `golden_chunks.parquet` with
columns matching `GoldenChunk` fields.

## Validation rules

- Every chunk must parse into `GoldenChunk`; invalid lines are logged and skipped
  (a bad line never crashes retrieval).
- `tier` is expected to be `gold`. Non-gold data should not be served.
- Domain in the file path should match `domain` in each record.
- Retrieval tags each returned source's `metadata.domain` so clients can trust the
  provenance.
