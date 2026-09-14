"""Generic contracts for internal conversational tools."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ToolBox(Protocol):
    """Read-only tool collection for one domain."""

    def definitions(self) -> list[dict[str, Any]]: ...

    def execute(self, name: str, arguments: dict[str, Any]) -> Any: ...


class ToolRegistry:
    """Domain -> toolbox lookup without leaking domain logic into the chat core."""

    def __init__(self, toolboxes: dict[str, ToolBox] | None = None):
        self._toolboxes = dict(toolboxes or {})

    def get(self, domain: str) -> ToolBox | None:
        return self._toolboxes.get(domain)

    def names(self) -> list[str]:
        return sorted(self._toolboxes)
