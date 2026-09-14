"""Deterministic APOLO tools over read-only golden data.

These tools are deliberately model-agnostic. They expose structured, grounded
queries that a conversational model can call later without coupling the chat
service to upstream extraction or taxonomy pipelines.

Important boundaries:
- this module never scrapes, runs Korax, mutates the Skill Graph, or regenerates data;
- skills are matched only from structured metadata (canonical names + aliases);
- labor-market numbers are returned only from structured metadata, never parsed
  from prose;
- every item carries source provenance for debugging and user-facing grounding.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any, Literal

from pydantic import BaseModel, Field

from golden_rag_chat.golden_data.contracts import GoldenChunk
from golden_rag_chat.golden_data.loader import GoldenDataSource

APOLO_TOOL_NAMES = (
    "search_programs",
    "get_skill_alignment",
    "get_labor_market",
)

_STOPWORDS = frozenset(
    {
        "a",
        "al",
        "algo",
        "con",
        "de",
        "del",
        "el",
        "en",
        "hacer",
        "la",
        "las",
        "lo",
        "los",
        "me",
        "mi",
        "para",
        "por",
        "que",
        "se",
        "un",
        "una",
        "y",
        "the",
        "to",
        "of",
        "and",
        "for",
        "in",
    }
)


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9+#.]+", _normalize(value))
        if len(token) >= 2 and token not in _STOPWORDS
    }


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [str(v) for v in value.values() if isinstance(v, (str, int, float))]
    if isinstance(value, Iterable):
        return [str(v) for v in value if isinstance(v, (str, int, float))]
    return []


def _same_filter(actual: Any, expected: str | None) -> bool:
    if expected is None:
        return True
    if actual is None:
        return False
    return _normalize(str(actual)) == _normalize(expected)


def _chunk_program_id(chunk: GoldenChunk) -> str:
    md = chunk.metadata
    return str(md.get("program_id") or md.get("career_id") or chunk.chunk_id)


def _chunk_program_name(chunk: GoldenChunk) -> str:
    md = chunk.metadata
    return str(md.get("program_name") or md.get("career_name") or chunk.title)


def _structured_skill_records(chunk: GoldenChunk) -> list[dict[str, Any]]:
    """Return canonical skill records from metadata without inferring from prose."""
    md = chunk.metadata
    aliases_map = md.get("skill_aliases")
    aliases_map = aliases_map if isinstance(aliases_map, Mapping) else {}

    raw_skills = md.get("skills")
    if raw_skills is None:
        raw_skills = md.get("competencies")
    if raw_skills is None:
        return []

    if isinstance(raw_skills, (str, Mapping)):
        raw_skills = [raw_skills]
    if not isinstance(raw_skills, Iterable):
        return []

    records: list[dict[str, Any]] = []
    for raw in raw_skills:
        if isinstance(raw, str):
            label = raw
            skill_id = _normalize(raw).replace(" ", "_")
            aliases = _string_list(aliases_map.get(raw))
        elif isinstance(raw, Mapping):
            label = str(raw.get("label") or raw.get("name") or raw.get("skill") or "").strip()
            if not label:
                continue
            skill_id = str(raw.get("skill_id") or raw.get("id") or _normalize(label).replace(" ", "_"))
            aliases = _string_list(raw.get("aliases"))
            aliases.extend(_string_list(aliases_map.get(label)))
        else:
            continue

        records.append(
            {
                "skill_id": skill_id,
                "skill": label,
                "aliases": sorted({alias for alias in aliases if alias}),
            }
        )
    return records


class ToolEvidence(BaseModel):
    source_id: str
    source_type: str
    title: str
    uri: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    tool: str
    items: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[ToolEvidence] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ToolExecution(BaseModel):
    """Safe debug trace: tool name + arguments + structured result, no chain-of-thought."""

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: ToolResult


class ApoloToolbox:
    def __init__(self, golden_data: GoldenDataSource):
        self._golden_data = golden_data

    @staticmethod
    def definitions() -> list[dict[str, Any]]:
        """Provider-neutral schemas that adapters can map to native tool calling."""
        return [
            {
                "name": "search_programs",
                "description": (
                    "Find education programs whose curated profile matches interests or activities. "
                    "Use matched terms and evidence; do not present the internal score as an affinity percentage."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "institution": {"type": ["string", "null"]},
                        "region": {"type": ["string", "null"]},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "get_skill_alignment",
                "description": (
                    "Match phrases from the conversation to canonical skills and aliases stored in APOLO golden data."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "program_id": {"type": ["string", "null"]},
                        "role_family": {"type": ["string", "null"]},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 30},
                    },
                    "required": ["text"],
                },
            },
            {
                "name": "get_labor_market",
                "description": (
                    "Return structured labor-market evidence and available counts for a program or role family. "
                    "Numbers come only from metadata."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "program_id": {"type": ["string", "null"]},
                        "role_family": {"type": ["string", "null"]},
                        "region": {"type": ["string", "null"]},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                    },
                },
            },
        ]

    def _chunks(self) -> list[GoldenChunk]:
        return self._golden_data.load_chunks(domain="apolo")

    def search_programs(
        self,
        *,
        query: str,
        institution: str | None = None,
        region: str | None = None,
        limit: int = 5,
    ) -> ToolResult:
        limit = max(1, min(limit, 20))
        query_terms = _tokens(query)
        ranked: list[tuple[int, str, GoldenChunk, list[str]]] = []

        for chunk in self._chunks():
            if chunk.source_type != "career_profile":
                continue
            md = chunk.metadata
            if not _same_filter(md.get("institution"), institution):
                continue
            if not _same_filter(md.get("region"), region):
                continue

            skills = _structured_skill_records(chunk)
            searchable = " ".join(
                [
                    _chunk_program_name(chunk),
                    chunk.title,
                    chunk.text,
                    " ".join(record["skill"] for record in skills),
                    " ".join(alias for record in skills for alias in record["aliases"]),
                    " ".join(_string_list(md.get("interests"))),
                ]
            )
            matched = sorted(query_terms & _tokens(searchable))
            score = len(matched)
            if query_terms and score == 0:
                continue

            ranked.append((score, _chunk_program_name(chunk), chunk, matched))

        ranked.sort(key=lambda row: (-row[0], _normalize(row[1]), row[2].chunk_id))
        selected = ranked[:limit]

        items: list[dict[str, Any]] = []
        evidence: list[ToolEvidence] = []
        for score, name, chunk, matched in selected:
            md = chunk.metadata
            items.append(
                {
                    "program_id": _chunk_program_id(chunk),
                    "name": name,
                    "institution": md.get("institution"),
                    "region": md.get("region"),
                    "matched_terms": matched,
                    "ranking_score": score,
                    "evidence_source_id": chunk.chunk_id,
                }
            )
            evidence.append(
                ToolEvidence(
                    source_id=chunk.chunk_id,
                    source_type=chunk.source_type,
                    title=chunk.title,
                    uri=chunk.uri,
                    metadata=dict(md),
                )
            )

        warnings = []
        if not items:
            warnings.append("no_matching_program_evidence")
        return ToolResult(tool="search_programs", items=items, evidence=evidence, warnings=warnings)

    def get_skill_alignment(
        self,
        *,
        text: str,
        program_id: str | None = None,
        role_family: str | None = None,
        limit: int = 8,
    ) -> ToolResult:
        limit = max(1, min(limit, 30))
        normalized_text = _normalize(text)
        text_terms = _tokens(text)
        by_skill: dict[str, tuple[int, dict[str, Any], GoldenChunk]] = {}
        saw_structured_skills = False

        for chunk in self._chunks():
            md = chunk.metadata
            if program_id is not None and _chunk_program_id(chunk) != program_id:
                continue
            if not _same_filter(md.get("role_family"), role_family):
                continue

            records = _structured_skill_records(chunk)
            if records:
                saw_structured_skills = True

            for record in records:
                labels = [record["skill"], *record["aliases"]]
                matched_labels: list[str] = []
                score = 0
                for label in labels:
                    normalized_label = _normalize(label)
                    label_terms = _tokens(label)
                    if normalized_label and normalized_label in normalized_text:
                        score = max(score, 3 + len(label_terms))
                        matched_labels.append(label)
                    else:
                        overlap = text_terms & label_terms
                        if overlap:
                            score = max(score, len(overlap))
                            matched_labels.append(label)

                if score <= 0:
                    continue

                skill_id = str(record["skill_id"])
                item = {
                    "skill_id": skill_id,
                    "skill": record["skill"],
                    "matched_phrases": sorted(set(matched_labels)),
                    "program_id": _chunk_program_id(chunk)
                    if chunk.source_type == "career_profile"
                    else md.get("program_id") or md.get("career_id"),
                    "role_family": md.get("role_family"),
                    "evidence_source_id": chunk.chunk_id,
                }
                current = by_skill.get(skill_id)
                if current is None or score > current[0]:
                    by_skill[skill_id] = (score, item, chunk)

        ranked = sorted(
            by_skill.values(),
            key=lambda row: (-row[0], _normalize(str(row[1]["skill"])), row[2].chunk_id),
        )[:limit]

        items = []
        evidence = []
        for score, item, chunk in ranked:
            items.append({**item, "ranking_score": score})
            evidence.append(
                ToolEvidence(
                    source_id=chunk.chunk_id,
                    source_type=chunk.source_type,
                    title=chunk.title,
                    uri=chunk.uri,
                    metadata=dict(chunk.metadata),
                )
            )

        warnings = []
        if not saw_structured_skills:
            warnings.append("structured_skills_missing_from_golden_data")
        elif not items:
            warnings.append("no_skill_alias_match")
        return ToolResult(
            tool="get_skill_alignment",
            items=items,
            evidence=evidence,
            warnings=warnings,
        )

    def get_labor_market(
        self,
        *,
        program_id: str | None = None,
        role_family: str | None = None,
        region: str | None = None,
        limit: int = 10,
    ) -> ToolResult:
        limit = max(1, min(limit, 20))
        selected: list[GoldenChunk] = []

        for chunk in self._chunks():
            if chunk.source_type != "job_market_summary":
                continue
            md = chunk.metadata
            chunk_program_id = md.get("program_id") or md.get("career_id")
            if program_id is not None and str(chunk_program_id) != program_id:
                continue
            if not _same_filter(md.get("role_family"), role_family):
                continue
            if not _same_filter(md.get("region"), region):
                continue
            selected.append(chunk)

        selected.sort(key=lambda chunk: (_normalize(chunk.title), chunk.chunk_id))
        selected = selected[:limit]

        metric_keys = (
            "job_count",
            "posting_count",
            "sample_size",
            "data_period",
            "top_skills",
            "regions",
            "sectors",
            "experience",
            "salary_band",
            "coverage_warning",
        )

        items: list[dict[str, Any]] = []
        evidence: list[ToolEvidence] = []
        has_count = False
        for chunk in selected:
            md = chunk.metadata
            metrics = {key: md[key] for key in metric_keys if key in md}
            count = metrics.get("job_count", metrics.get("posting_count"))
            if isinstance(count, (int, float)) and not isinstance(count, bool):
                has_count = True

            items.append(
                {
                    "program_id": md.get("program_id") or md.get("career_id"),
                    "role_family": md.get("role_family"),
                    "region": md.get("region"),
                    "metrics": metrics,
                    "summary": chunk.text,
                    "evidence_source_id": chunk.chunk_id,
                }
            )
            evidence.append(
                ToolEvidence(
                    source_id=chunk.chunk_id,
                    source_type=chunk.source_type,
                    title=chunk.title,
                    uri=chunk.uri,
                    metadata=dict(md),
                )
            )

        warnings = []
        if not items:
            warnings.append("no_matching_labor_market_evidence")
        elif not has_count:
            warnings.append("job_count_not_available_in_structured_metadata")

        return ToolResult(
            tool="get_labor_market",
            items=items,
            evidence=evidence,
            warnings=warnings,
        )

    def execute(self, name: Literal[
        "search_programs",
        "get_skill_alignment",
        "get_labor_market",
    ], arguments: dict[str, Any]) -> ToolExecution:
        if name == "search_programs":
            result = self.search_programs(**arguments)
        elif name == "get_skill_alignment":
            result = self.get_skill_alignment(**arguments)
        elif name == "get_labor_market":
            result = self.get_labor_market(**arguments)
        else:  # pragma: no cover - Literal prevents normal callers reaching this
            raise ValueError(f"unknown APOLO tool: {name}")
        return ToolExecution(name=name, arguments=dict(arguments), result=result)
