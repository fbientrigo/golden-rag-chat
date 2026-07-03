"""Agriculture domain: agronomic advisory (SbnAI / SevenEye-like)."""

from __future__ import annotations

from golden_rag_chat.domains.base import DomainAdapter
from golden_rag_chat.user_state.base import UserState


class AgricultureDomain(DomainAdapter):
    name = "agriculture"

    def persona(self) -> str:
        return (
            "You are an agronomic advisory assistant. You help a farm user understand "
            "why some areas may be affected by frost, humidity, fungal or irrigation "
            "risk, what evidence supports that, and what reasonable adaptation or "
            "diagnostic steps follow — using only curated agronomic golden data. You "
            "are advisory only and do not replace an on-site agronomist."
        )

    def render_user_state(self, user_state: UserState | None) -> str:
        if user_state is None:
            return "(no saved farm profile)"
        p = user_state.profile
        prefs = user_state.preferences
        ctx = user_state.current_context
        lines = []
        if p.get("farm_id"):
            lines.append(f"- Farm: {p['farm_id']}")
        if p.get("region"):
            lines.append(f"- Region: {p['region']}")
        if p.get("crops"):
            lines.append(f"- Crops: {', '.join(p['crops'])}")
        if ctx.get("selected_crop"):
            lines.append(f"- Selected crop: {ctx['selected_crop']}")
        if ctx.get("recent_symptom"):
            lines.append(f"- Recent symptom: {ctx['recent_symptom']}")
        if prefs.get("risk_focus"):
            lines.append(f"- Risk focus: {', '.join(prefs['risk_focus'])}")
        return "\n".join(lines) if lines else "(profile present but empty)"
