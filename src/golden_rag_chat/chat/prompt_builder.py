"""Build the prompt (a list of ``ChatMessage``) from all inputs.

Layout:
- system : domain persona + shared grounding rules.
- user   : user-state summary, request context, the labelled evidence, then the
           question. Putting the question last keeps it salient.

This module is domain-agnostic: it asks the ``DomainAdapter`` to render the
domain-specific parts.
"""

from __future__ import annotations

from typing import Any

from golden_rag_chat.chat.source_formatter import format_sources_for_prompt
from golden_rag_chat.domains.base import DomainAdapter
from golden_rag_chat.llm.base import ChatMessage
from golden_rag_chat.retrieval.base import RetrievedSource
from golden_rag_chat.user_state.base import UserState


def build_messages(
    *,
    domain: DomainAdapter,
    question: str,
    user_state: UserState | None,
    context: dict[str, Any],
    sources: list[RetrievedSource],
) -> list[ChatMessage]:
    system = domain.system_prompt()

    user_block = "\n".join(
        [
            "USER STATE:",
            domain.render_user_state(user_state),
            "",
            "REQUEST CONTEXT:",
            domain.render_context(context),
            "",
            "EVIDENCE:",
            format_sources_for_prompt(sources),
            "",
            f"QUESTION: {question}",
        ]
    )

    return [
        ChatMessage(role="system", content=system),
        ChatMessage(role="user", content=user_block),
    ]
