"""Intent declarations for public launch surfaces."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskIntentSpec:
    """Goal-type metadata inside one or more execution surfaces."""

    intent_id: str
    surface_ids: tuple[str, ...]
    supported_drivers: tuple[str, ...]
    lower_task: str
    prompt_id: str
    checker_id: str
    default_goal_scope: str
    done_readiness_policy: str
    checker_policy: str
    required_artifacts: tuple[str, ...]
    completion_claim_schema: str
    evaluation_policy: str
    required_capabilities: tuple[str, ...] = ()


GOAL_SCOPE_WHOLE_ROOM = "whole-room"
GOAL_SCOPE_PROMPT_SCOPED = "prompt-scoped"
GOAL_SCOPE_AGENT_DECLARED = "agent-declared"

TASK_INTENT_SPECS: dict[str, TaskIntentSpec] = {
    "cleanup": TaskIntentSpec(
        intent_id="cleanup",
        surface_ids=("household-world",),
        supported_drivers=("direct", "mcp-smoke", "codex", "claude", "openclaw"),
        lower_task="household-cleanup",
        prompt_id="household_cleanup",
        checker_id="cleanup_report",
        default_goal_scope=GOAL_SCOPE_WHOLE_ROOM,
        done_readiness_policy="cleanup_sweep_and_pending_candidates",
        checker_policy="cleanup_success",
        required_artifacts=("run_result.json", "report.html", "trace.jsonl", "goal_contract.json"),
        completion_claim_schema="roboclaws_agent_completion_claim_v1",
        evaluation_policy="cleanup",
        required_capabilities=(
            "household_world",
            "household_manipulation",
            "household_episode",
        ),
    ),
    "map-build": TaskIntentSpec(
        intent_id="map-build",
        surface_ids=("household-world",),
        supported_drivers=("direct", "codex"),
        lower_task="semantic-map-build",
        prompt_id="semantic_map_build",
        checker_id="runtime_metric_map",
        default_goal_scope=GOAL_SCOPE_WHOLE_ROOM,
        done_readiness_policy="map_sweep",
        checker_policy="runtime_metric_map",
        required_artifacts=(
            "run_result.json",
            "report.html",
            "trace.jsonl",
            "goal_contract.json",
            "runtime_metric_map.json",
        ),
        completion_claim_schema="roboclaws_agent_completion_claim_v1",
        evaluation_policy="map_build",
        required_capabilities=("household_world", "household_episode"),
    ),
    "open-ended": TaskIntentSpec(
        intent_id="open-ended",
        surface_ids=("household-world",),
        supported_drivers=("mcp-smoke", "codex", "claude"),
        lower_task="household-cleanup",
        prompt_id="household_open_ended",
        checker_id="open_ended_report",
        default_goal_scope=GOAL_SCOPE_AGENT_DECLARED,
        done_readiness_policy="agent_declared_goal",
        checker_policy="open_ended_advisory",
        required_artifacts=("run_result.json", "report.html", "trace.jsonl", "goal_contract.json"),
        completion_claim_schema="roboclaws_agent_completion_claim_v1",
        evaluation_policy="open_ended",
        required_capabilities=("household_world", "household_episode"),
    ),
    "navigate": TaskIntentSpec(
        intent_id="navigate",
        surface_ids=("ai2thor-world",),
        supported_drivers=("openclaw", "codex", "claude"),
        lower_task="ai2thor-nav",
        prompt_id="ai2thor_nav",
        checker_id="ai2thor_nav_report",
        default_goal_scope=GOAL_SCOPE_AGENT_DECLARED,
        done_readiness_policy="agent_declared_goal",
        checker_policy="navigation_report",
        required_artifacts=("run_result.json",),
        completion_claim_schema="roboclaws_agent_completion_claim_v1",
        evaluation_policy="navigation",
        required_capabilities=("navigation_world", "movement_actions"),
    ),
    "photo-capture": TaskIntentSpec(
        intent_id="photo-capture",
        surface_ids=("ai2thor-world",),
        supported_drivers=("openclaw", "codex", "claude"),
        lower_task="photo-chairs",
        prompt_id="photo_chairs",
        checker_id="photo_report",
        default_goal_scope=GOAL_SCOPE_AGENT_DECLARED,
        done_readiness_policy="agent_declared_goal",
        checker_policy="photo_report",
        required_artifacts=("run_result.json",),
        completion_claim_schema="roboclaws_agent_completion_claim_v1",
        evaluation_policy="photo_capture",
        required_capabilities=("navigation_world", "movement_actions", "photo_capture"),
    ),
    "territory": TaskIntentSpec(
        intent_id="territory",
        surface_ids=("ai2thor-games",),
        supported_drivers=("openclaw", "vlm", "script"),
        lower_task="territory",
        prompt_id="territory_game",
        checker_id="territory_report",
        default_goal_scope=GOAL_SCOPE_AGENT_DECLARED,
        done_readiness_policy="fixed_step_game",
        checker_policy="territory_report",
        required_artifacts=("report.html",),
        completion_claim_schema="roboclaws_agent_completion_claim_v1",
        evaluation_policy="game",
        required_capabilities=("navigation_world", "movement_actions", "game_score"),
    ),
    "coverage": TaskIntentSpec(
        intent_id="coverage",
        surface_ids=("ai2thor-games",),
        supported_drivers=("openclaw", "vlm", "script"),
        lower_task="coverage",
        prompt_id="coverage_game",
        checker_id="coverage_report",
        default_goal_scope=GOAL_SCOPE_AGENT_DECLARED,
        done_readiness_policy="fixed_step_game",
        checker_policy="coverage_report",
        required_artifacts=("report.html",),
        completion_claim_schema="roboclaws_agent_completion_claim_v1",
        evaluation_policy="game",
        required_capabilities=("navigation_world", "movement_actions", "coverage_score"),
    ),
    "planner-proof": TaskIntentSpec(
        intent_id="planner-proof",
        surface_ids=("planner-proof",),
        supported_drivers=("direct", "script", "mcp-smoke"),
        lower_task="molmo-planner-proof",
        prompt_id="molmo_planner_proof",
        checker_id="planner_proof_report",
        default_goal_scope=GOAL_SCOPE_AGENT_DECLARED,
        done_readiness_policy="planner_proof",
        checker_policy="planner_proof_report",
        required_artifacts=("report.html",),
        completion_claim_schema="roboclaws_agent_completion_claim_v1",
        evaluation_policy="planner_proof",
        required_capabilities=("planner_proof",),
    ),
}


def intent_spec(intent_id: str) -> TaskIntentSpec:
    """Return an intent spec by id."""

    return TASK_INTENT_SPECS[intent_id]
