"""Mock retrieval provider.

Returns deterministic, domain-appropriate fake evidence with no I/O. Used by the
default test suite and as a smoke-test backend. It never touches golden data, so
it works regardless of configuration.
"""

from __future__ import annotations

from typing import Any

from golden_rag_chat.retrieval.base import RetrievedSource
from golden_rag_chat.user_state.base import UserState

# One canned source per domain. Enough for a client to exercise the full /chat
# round-trip and for tests to assert domain-correct attribution.
_CANNED: dict[str, RetrievedSource] = {
    "apolo": RetrievedSource(
        source_id="apolo-skill-gap-001",
        source_type="skill_gap",
        title="Data & Analytics Engineering skill gap summary",
        uri="golden://apolo/skill_gap/001",
        text=(
            "The most frequent missing skills for Data & Analytics Engineering are "
            "SQL, Python, ETL/orchestration, cloud fundamentals, and dashboarding."
        ),
        score=0.99,
        metadata={"domain": "apolo", "role_family": "Data & Analytics Engineering", "tier": "gold"},
    ),
    "agriculture": RetrievedSource(
        source_id="agri-crop-risk-001",
        source_type="crop_risk_report",
        title="Grape fungal-risk summary after humid period",
        uri="golden://agriculture/crop_risk/001",
        text=(
            "Sustained leaf wetness and high humidity raise the risk of fungal disease "
            "(e.g. powdery/downy mildew) in grapevines; scout for leaf spotting."
        ),
        score=0.99,
        metadata={"domain": "agriculture", "crop": "grape", "risk_type": "fungal", "tier": "gold"},
    ),
}


class MockRetrievalProvider:
    async def retrieve(
        self,
        *,
        domain: str,
        question: str,
        user_state: UserState | None,
        context: dict[str, Any],
        max_sources: int,
    ) -> list[RetrievedSource]:
        canned = _CANNED.get(domain)
        if canned is None:
            return []
        return [canned][:max_sources]
