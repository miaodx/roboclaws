"""Surface spec declarations used by the launch catalog."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskSurfaceSpec:
    """Declarative execution-surface metadata.

    Specs describe runnable environments and capability surfaces. They do not
    import driver implementations, backend adapters, or MCP server code.
    """

    surface_id: str
    domain: str
    supported_drivers: tuple[str, ...]
    supported_intents: tuple[str, ...]
    default_intent: str
    supported_reports: tuple[str, ...]
    default_report: str | None
    default_profile: str | None
    supported_profiles: tuple[str, ...]
    default_backend: str
    mcp_server_id: str
    checker_base: str
    required_capabilities: tuple[str, ...]

    @property
    def name(self) -> str:
        """Compatibility accessor for older launch-plan readers."""

        return self.surface_id
