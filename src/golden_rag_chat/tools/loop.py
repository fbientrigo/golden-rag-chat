"""Provider-neutral internal tool loop helpers.

M1 deliberately uses a tiny JSON action protocol instead of provider-specific
function-calling APIs. That keeps OpenRouter, Bedrock Converse, mock and future
providers behind the existing LLMProvider contract. Native provider tool calling
can replace this transport later without changing the deterministic tools.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from golden_rag_chat.llm.base import ChatMessage
from golden_rag_chat.retrieval.base import RetrievedSource


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


def tool_instructions(definitions: list[dict[str, Any]]) -> ChatMessage:
    """Return a system message describing the internal action protocol."""
    rendered = json.dumps(definitions, ensure_ascii=False, separators=(",", ":"))
    return ChatMessage(
        role="system",
        content=(
            "INTERNAL TOOLS are available for grounded data queries. "
            "For exploratory conversation or when you need more information from the user, "
            "reply normally and ask a concise follow-up question. "
            "When you need one tool, reply ONLY with valid JSON in this exact envelope: "
            '{"tool_call":{"name":"TOOL_NAME","arguments":{...}}}. '
            "Do not wrap it in markdown and do not expose the internal protocol to the user. "
            "After a tool result is provided, answer naturally using only supported evidence. "
            "Never invent job counts, percentages, skills, programs, salaries, or sources. "
            f"Available tools: {rendered}"
        ),
    )


def parse_tool_call(text: str) -> ToolCallRequest | None:
    """Parse only an explicit whole-message tool call; ordinary conversation is untouched."""
    stripped = text.strip()
    if not stripped.startswith("{"):
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or set(payload) != {"tool_call"}:
        return None
    raw_call = payload["tool_call"]
    if not isinstance(raw_call, dict):
        return None
    try:
        return ToolCallRequest.model_validate(raw_call)
    except ValueError:
        return None


def tool_result_message(*, execution: Any, sources: list[RetrievedSource]) -> ChatMessage:
    """Feed a structured result back to the model without exposing it to the user."""
    result_json = json.dumps(
        execution.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    evidence_lines = []
    for index, source in enumerate(sources, start=1):
        evidence_lines.append(
            f"[S{index}] {source.title}\n"
            f"URI: {source.uri}\n"
            f"TYPE: {source.source_type}\n"
            f"TEXT: {source.text}"
        )
    evidence = "\n\n".join(evidence_lines) if evidence_lines else "(no evidence returned)"
    return ChatMessage(
        role="user",
        content=(
            "INTERNAL TOOL RESULT (trusted structured data; do not quote this wrapper):\n"
            f"{result_json}\n\n"
            "UPDATED EVIDENCE:\n"
            f"{evidence}\n\n"
            "Continue the conversation naturally. If the tool returned no usable evidence, "
            "say so or ask a follow-up instead of guessing."
        ),
    )


def merge_sources(
    existing: list[RetrievedSource],
    execution: Any,
) -> list[RetrievedSource]:
    """Add tool provenance as normal citation sources, deduplicated by source id."""
    merged = list(existing)
    seen = {source.source_id for source in merged}
    for evidence in execution.result.evidence:
        if evidence.source_id in seen:
            continue
        merged.append(
            RetrievedSource(
                source_id=evidence.source_id,
                source_type=evidence.source_type,
                title=evidence.title,
                uri=evidence.uri,
                text=evidence.excerpt,
                metadata=dict(evidence.metadata),
            )
        )
        seen.add(evidence.source_id)
    return merged
