"""Deterministic tests for the three APOLO conversational tools."""

from __future__ import annotations

from golden_rag_chat.golden_data.contracts import GoldenChunk
from golden_rag_chat.tools.apolo import APOLO_TOOL_NAMES, ApoloToolbox


class _MemoryGoldenData:
    def __init__(self, chunks: list[GoldenChunk]):
        self._chunks = chunks

    def load_chunks(self, *, domain: str) -> list[GoldenChunk]:
        assert domain == "apolo"
        return self._chunks


def _chunk(
    chunk_id: str,
    source_type: str,
    title: str,
    text: str,
    metadata: dict,
) -> GoldenChunk:
    return GoldenChunk(
        chunk_id=chunk_id,
        domain="apolo",
        source_type=source_type,
        title=title,
        text=text,
        uri=f"golden://apolo/{chunk_id}",
        metadata=metadata,
    )


def _toolbox() -> ApoloToolbox:
    return ApoloToolbox(
        _MemoryGoldenData(
            [
                _chunk(
                    "program-computacion",
                    "career_profile",
                    "Ingeniería Civil en Computación",
                    "Programación, desarrollo de software y construcción de sistemas interactivos.",
                    {
                        "program_id": "uchile-computacion",
                        "program_name": "Ingeniería Civil en Computación",
                        "institution": "Universidad de Chile",
                        "region": "RM",
                        "interests": ["videojuegos", "mods", "software"],
                        "skills": [
                            {
                                "skill_id": "programming",
                                "label": "Programación",
                                "aliases": ["programar", "scripts", "scripting"],
                            },
                            {
                                "skill_id": "debugging",
                                "label": "Depuración de software",
                                "aliases": ["debugging", "bugs", "arreglar bugs"],
                            },
                        ],
                    },
                ),
                _chunk(
                    "program-audiovisual",
                    "career_profile",
                    "Cine y Televisión",
                    "Narrativa, guion, producción y realización audiovisual.",
                    {
                        "program_id": "uchile-cine",
                        "program_name": "Cine y Televisión",
                        "institution": "Universidad de Chile",
                        "region": "RM",
                        "interests": ["historias", "video", "guion"],
                        "skills": [{"skill_id": "storytelling", "label": "Narrativa audiovisual"}],
                    },
                ),
                _chunk(
                    "market-software",
                    "job_market_summary",
                    "Software development demand",
                    "Curated summary. The prose may mention 9999 jobs, but tools must not parse that number.",
                    {
                        "role_family": "Software Development",
                        "region": "RM",
                        "job_count": 438,
                        "sample_size": 1462,
                        "data_period": "2026-Q3",
                        "top_skills": ["Programación", "Git", "SQL"],
                        "skills": [
                            {
                                "skill_id": "programming",
                                "label": "Programación",
                                "aliases": ["scripts", "scripting", "programar"],
                            }
                        ],
                    },
                ),
                _chunk(
                    "market-no-count",
                    "job_market_summary",
                    "Game development qualitative summary",
                    "This source says 12345 openings in prose only.",
                    {
                        "role_family": "Game Development",
                        "region": "RM",
                    },
                ),
            ]
        )
    )


def test_search_programs_uses_explicit_evidence_not_affinity_percentages():
    result = _toolbox().search_programs(query="me gusta hacer mods y scripts")

    assert result.tool == "search_programs"
    assert result.items[0]["program_id"] == "uchile-computacion"
    assert "mods" in result.items[0]["matched_terms"]
    assert result.items[0]["ranking_score"] > 0
    assert "affinity" not in result.items[0]
    assert result.evidence[0].source_id == "program-computacion"


def test_skill_alignment_matches_canonical_aliases_from_conversation():
    result = _toolbox().get_skill_alignment(
        text="programo scripts y me gusta arreglar bugs cuando un mod falla"
    )

    skills = {item["skill_id"]: item for item in result.items}
    assert "programming" in skills
    assert "debugging" in skills
    assert "scripts" in skills["programming"]["matched_phrases"]
    assert "arreglar bugs" in skills["debugging"]["matched_phrases"]


def test_labor_market_returns_only_structured_counts():
    result = _toolbox().get_labor_market(role_family="Software Development", region="RM")

    assert result.items[0]["metrics"]["job_count"] == 438
    assert result.items[0]["metrics"]["sample_size"] == 1462
    assert "9999" not in str(result.items[0]["metrics"])
    assert result.warnings == []


def test_labor_market_refuses_to_promote_number_from_prose():
    result = _toolbox().get_labor_market(role_family="Game Development")

    assert result.items
    assert result.items[0]["metrics"] == {}
    assert "job_count_not_available_in_structured_metadata" in result.warnings
    assert "12345" in result.items[0]["summary"]


def test_registry_exposes_exactly_three_tools_and_debug_execution():
    toolbox = _toolbox()

    assert APOLO_TOOL_NAMES == (
        "search_programs",
        "get_skill_alignment",
        "get_labor_market",
    )
    assert [definition["name"] for definition in toolbox.definitions()] == list(APOLO_TOOL_NAMES)

    execution = toolbox.execute(
        "get_labor_market",
        {"role_family": "Software Development", "region": "RM"},
    )
    assert execution.name == "get_labor_market"
    assert execution.arguments["region"] == "RM"
    assert execution.result.items[0]["metrics"]["job_count"] == 438
