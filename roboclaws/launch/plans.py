"""Declarative launch plan types."""

from __future__ import annotations

from dataclasses import dataclass

from roboclaws.launch.goals import GoalContract


@dataclass(frozen=True)
class LaunchPlan:
    """Resolved public surface/intent route before execution.

    The launch plan names the canonical axes first, then the lower command that
    the current implementation should execute. The command intentionally still
    points at ``just agent::run`` in the first migration checkpoint; later
    slices can replace that target without changing the public facade.
    """

    argv: tuple[str, ...]
    surface: str
    intent: str
    lower_task: str
    driver: str
    evidence_mode: str
    profile: str | None
    report: str | None
    backend: str
    prompt_id: str
    checker_id: str
    mcp_server_id: str
    required_capabilities: tuple[str, ...]
    required_artifacts: tuple[str, ...]
    goal_contract: GoalContract
    evaluation_id: str
    evaluation_hard_gates: tuple[str, ...]
    evaluation_intent_gates: tuple[str, ...]
    completion_claim_required: bool
    supported_reports: tuple[str, ...]
    supported_profiles: tuple[str, ...]
    overrides: tuple[str, ...]

    @property
    def task(self) -> str:
        """Compatibility name for the lower task dispatcher target."""

        return self.lower_task

    @property
    def mode(self) -> str:
        """Compatibility name for the resolved report/profile slot."""

        return self.evidence_mode
