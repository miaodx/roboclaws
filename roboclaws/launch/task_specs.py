"""Task spec declarations used by the launch catalog."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskSpec:
    """Declarative task metadata.

    Specs describe public task requirements and launch defaults. They do not
    import driver implementations, backend adapters, or MCP server code.
    """

    name: str
    domain: str
    supported_drivers: tuple[str, ...]
    supported_reports: tuple[str, ...]
    default_report: str | None
    default_profile: str | None
    supported_profiles: tuple[str, ...]
    default_backend: str
    prompt_id: str
    checker_id: str
    required_capabilities: tuple[str, ...]
