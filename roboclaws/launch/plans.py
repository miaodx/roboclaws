"""Declarative launch plan types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LaunchPlan:
    """Resolved public task route before execution.

    The launch plan names the public axes first, then the lower command that
    the current implementation should execute. The command intentionally still
    points at ``just agent::run`` in the first migration checkpoint; later
    slices can replace that target without changing the public facade.
    """

    argv: tuple[str, ...]
    task: str
    driver: str
    evidence_mode: str
    profile: str | None
    report: str | None
    backend: str
    prompt_id: str
    checker_id: str
    required_capabilities: tuple[str, ...]
    supported_reports: tuple[str, ...]
    supported_profiles: tuple[str, ...]
    overrides: tuple[str, ...]

    @property
    def mode(self) -> str:
        """Compatibility name for the resolved report/profile slot."""

        return self.evidence_mode
