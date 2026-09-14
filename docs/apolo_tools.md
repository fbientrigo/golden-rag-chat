# APOLO internal tools — M0 contract

The conversational layer may call exactly three deterministic APOLO tools:

- `search_programs(...)`
- `get_skill_alignment(...)`
- `get_labor_market(...)`

They live in `golden_rag_chat.tools.apolo.ApoloToolbox` and read the existing
`GoldenDataSource` only. They do not scrape, invoke Korax, modify the Skill Graph,
or regenerate upstream artifacts.

## Why this boundary

The chat backend should ask questions and decide *when* evidence is needed. The
upstream APOLO data pipeline remains the source of truth for programs, canonical
skills and labor-market aggregates. This keeps the chatbot replaceable and makes
every answer auditable.

## Required golden-data metadata

### Career profile

A `career_profile` chunk should provide, when available:

```json
{
  "program_id": "stable-id",
  "program_name": "Ingeniería Civil en Computación",
  "institution": "Universidad de Chile",
  "region": "RM",
  "interests": ["videojuegos", "software"],
  "skills": [
    {
      "skill_id": "programming",
      "label": "Programación",
      "aliases": ["programar", "scripts", "scripting"]
    }
  ]
}
```

`skills` may also be a list of canonical strings. A top-level
`skill_aliases` mapping is supported for compatibility. For production APOLO,
the preferred source is the canonical output derived upstream from
`apolo-skill-standard` / SkillResolver.

### Labor-market summary

A `job_market_summary` chunk should provide structured metrics:

```json
{
  "role_family": "Software Development",
  "region": "RM",
  "job_count": 438,
  "sample_size": 1462,
  "data_period": "2026-Q3",
  "top_skills": ["Programación", "Git", "SQL"]
}
```

The tool never parses numeric claims from `text`. If `job_count` or
`posting_count` is absent, it returns the evidence plus the warning
`job_count_not_available_in_structured_metadata`.

## Tool behavior

### `search_programs`

Ranks `career_profile` evidence by deterministic token overlap over program name,
profile text, declared interests, canonical skills and aliases. The raw
`ranking_score` is only an ordering signal. It must not be rendered to users as
an "affinity percentage".

### `get_skill_alignment`

Matches conversation text against canonical skill labels and aliases stored in
structured metadata. It does not invent a skill from prose. If the golden export
does not contain structured skills, the result explicitly warns
`structured_skills_missing_from_golden_data`.

### `get_labor_market`

Filters `job_market_summary` evidence by program, role family and region, and
returns only explicitly structured metrics.

## Debugging

`ApoloToolbox.execute(name, arguments)` returns a `ToolExecution` containing:

- tool name;
- exact structured arguments;
- structured result;
- evidence provenance;
- warnings.

This object is safe to expose in a future `debug=true` chat trace because it
contains no hidden chain-of-thought.

## M0 acceptance checks

Correct if the offline tests demonstrate:

1. "mods + scripts" ranks a computing program above an unrelated audiovisual one;
2. "scripts" and "arreglar bugs" resolve through explicit aliases to canonical skills;
3. a labor-market count is returned only when it exists in metadata;
4. a number present only in prose is never promoted to a metric;
5. the registry exposes exactly the three agreed tools.
