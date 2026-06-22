"""Apolo domain: AI-powered job/career matching."""

from __future__ import annotations

from golden_rag_chat.domains.base import DomainAdapter
from golden_rag_chat.user_state.base import UserState


class ApoloDomain(DomainAdapter):
    name = "apolo"

    def persona(self) -> str:
        return (
            "You are Apolo, a career-matching assistant. You help a user understand "
            "their fit for role families, the skills they are missing, salary and "
            "geographic opportunities, and concrete next steps — using only curated "
            "labor-market and graduate-profile golden data."
        )

    def render_user_state(self, user_state: UserState | None) -> str:
        if user_state is None:
            return "(no saved profile)"
        p = user_state.profile
        prefs = user_state.preferences
        ctx = user_state.current_context
        lines = []
        if p.get("selected_career"):
            lines.append(f"- Selected career: {p['selected_career']}")
        if p.get("known_skills"):
            lines.append(f"- Known skills: {', '.join(p['known_skills'])}")
        if p.get("target_roles"):
            lines.append(f"- Target roles: {', '.join(p['target_roles'])}")
        if ctx.get("selected_role_family"):
            lines.append(f"- Selected role family: {ctx['selected_role_family']}")
        if prefs.get("locations"):
            lines.append(f"- Preferred locations: {', '.join(prefs['locations'])}")
        if "remote_ok" in prefs:
            lines.append(f"- Remote OK: {prefs['remote_ok']}")
        return "\n".join(lines) if lines else "(profile present but empty)"
