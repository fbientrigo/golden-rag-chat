"""Golden-data contracts.

Golden data is curated, validated, *stable* output from upstream pipelines. This
service only reads it. It must never scrape, clean, train, or regenerate it.

``GoldenChunk`` is the generic unit of evidence shared by every domain. Domain
specifics live entirely in ``metadata`` so the generic core stays domain-neutral.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Domain(StrEnum):
    """Supported business domains. String-valued so it serializes as plain text."""

    APOLO = "apolo"
    AGRICULTURE = "agriculture"


# Source types span both domains. Kept as a Literal (not per-domain enums) so the
# generic models never need to know which domain a value belongs to.
SourceType = Literal[
    "career_profile",
    "job_market_summary",
    "skill_gap",
    "farm_state",
    "crop_risk_report",
    "weather_summary",
    "agronomic_report",
]


class GoldenChunk(BaseModel):
    """A single curated piece of evidence.

    ``metadata`` is intentionally open (``extra="allow"`` on the dict values is not
    needed because it is a free-form dict). Domain-specific keys — ``career_id``,
    ``role_family``, ``farm_id``, ``crop``, ``risk_type`` … — go here.
    """

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    domain: Domain
    text: str
    source_type: SourceType
    title: str
    uri: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def tier(self) -> str:
        return str(self.metadata.get("tier", "gold"))
