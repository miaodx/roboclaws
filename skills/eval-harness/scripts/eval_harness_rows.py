from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

ROW_SCHEMA = "roboclaws_eval_harness_row_v1"
DEFAULT_WORLD = "molmospaces/val_0"
DEFAULT_BACKEND = "mujoco"
DEFAULT_SEED = "7"
DEFAULT_PROVIDER_PROFILE = "codex-env"


def candidate_rows(
    *, output_dir: Path, explicit_axes: dict[str, list[str]]
) -> list[dict[str, Any]]:
    provider_profiles = explicit_axes.get("provider_profile") or [DEFAULT_PROVIDER_PROFILE]
    codex_provider = provider_profiles[0]
    row_dir = output_dir / "rows"
    eval_output_root = output_dir / "evals"
    return [
        _row(
            row_id="route-trace-contract-tests",
            row_kind="deterministic_gate",
            command=[
                "./scripts/dev/run_pytest_standalone.sh",
                "-q",
                "tests/contract/dev_tools/test_task_agent_just_recipes.py",
            ],
            axes={"intent": "route-trace"},
            reason=(
                "Launch catalog, provider profile, or command-surface changes need "
                "route trace coverage."
            ),
            rule_ids=("launch_catalog",),
            requirements=("python_env",),
            expense="deterministic",
            row_dir=row_dir,
        ),
        _row(
            row_id="eval-unit-tests",
            row_kind="deterministic_gate",
            command=[
                "./scripts/dev/run_pytest_standalone.sh",
                "-q",
                "tests/unit/evals",
            ],
            axes={"intent": "eval-harness"},
            reason=(
                "Eval harness, suite, manifest, or regression-promotion changes need eval tests."
            ),
            rule_ids=("eval_harness",),
            requirements=("python_env",),
            expense="deterministic",
            row_dir=row_dir,
        ),
        _row(
            row_id="cleanup-contract-tests",
            row_kind="deterministic_gate",
            command=[
                "./scripts/dev/run_pytest_standalone.sh",
                "-q",
                "tests/unit/molmo_cleanup/test_molmo_cleanup_policy.py",
                "tests/unit/molmo_cleanup/test_molmo_cleanup_semantic_acceptability.py",
                "tests/unit/molmo_cleanup/test_molmo_semantic_cleanup_loop.py",
            ],
            axes={"intent": "cleanup", "agent_engine": "direct-runner"},
            reason=(
                "Cleanup, MCP, checker, and report changes need deterministic cleanup "
                "contract checks."
            ),
            rule_ids=("cleanup_skill", "mcp_checker"),
            requirements=("python_env",),
            expense="deterministic",
            row_dir=row_dir,
        ),
        _row(
            row_id="household-direct-world-oracle-product",
            row_kind="product_run",
            command=[
                "just",
                "run::surface",
                "surface=household-world",
                f"world={DEFAULT_WORLD}",
                f"backend={DEFAULT_BACKEND}",
                "preset=cleanup",
                "agent_engine=direct-runner",
                "evidence_lane=world-oracle-labels",
                f"seed={DEFAULT_SEED}",
                f"output_dir={row_dir / 'household-direct-world-oracle-product' / 'run'}",
            ],
            axes={
                "agent_engine": "direct-runner",
                "intent": "cleanup",
                "preset": "cleanup",
                "evidence_lane": "world-oracle-labels",
                "backend": DEFAULT_BACKEND,
                "world": DEFAULT_WORLD,
            },
            reason="MCP/server/checker changes need at least one public cleanup product route.",
            rule_ids=("mcp_checker",),
            requirements=("just", "python_env"),
            expense="local-sim",
            row_dir=row_dir,
        ),
        _row(
            row_id="open-ended-household-contract-tests",
            row_kind="deterministic_gate",
            command=[
                "./scripts/dev/run_pytest_standalone.sh",
                "-q",
                "tests/contract/dev_tools/test_task_agent_just_recipes.py::"
                "test_surface_prompt_omitted_intent_with_prompt_infers_open_ended",
                "tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::"
                "test_realworld_mcp_open_ended_intent_is_recorded_in_run_result",
                "tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py::"
                "test_checker_allows_open_ended_agent_view_with_no_visible_objects",
            ],
            axes={"intent": "open-ended"},
            reason=(
                "Open-ended, goal-contract, or completion-claim changes need a "
                "first-class open-ended launch and artifact contract gate."
            ),
            rule_ids=("open_ended",),
            requirements=("python_env",),
            expense="deterministic",
            row_dir=row_dir,
        ),
        _row(
            row_id="smoke-regression-eval-suite",
            row_kind="eval_suite",
            command=_eval_suite_command(
                suite="smoke_regression",
                budget="smoke",
                output_root=eval_output_root,
                stamp="smoke-regression-eval-suite",
            ),
            axes={"intent": "eval-suite", "suite": "smoke_regression"},
            reason="Eval harness or command-surface changes need the smoke regression suite.",
            rule_ids=("eval_harness", "launch_catalog"),
            requirements=("just", "python_env"),
            expense="deterministic",
            row_dir=row_dir,
        ),
        _row(
            row_id="map-build-consumer-eval-suite",
            row_kind="eval_suite",
            command=_eval_suite_command(
                suite="map_build_consumer",
                budget="smoke",
                output_root=eval_output_root,
                stamp="map-build-consumer-eval-suite",
            ),
            axes={"intent": "eval-suite", "suite": "map_build_consumer"},
            reason="Map-build, actionability, or open-ended changes need the map consumer suite.",
            rule_ids=("map_build", "open_ended"),
            requirements=("just", "python_env"),
            expense="deterministic",
            row_dir=row_dir,
        ),
        _row(
            row_id="cleanup-capability-eval-suite",
            row_kind="eval_suite",
            command=_eval_suite_command(
                suite="cleanup_capability",
                budget="smoke",
                output_root=eval_output_root,
                stamp="cleanup-capability-eval-suite",
            ),
            axes={"intent": "eval-suite", "suite": "cleanup_capability"},
            reason="Cleanup skill or MCP changes need the repeated cleanup capability suite.",
            rule_ids=("cleanup_skill", "mcp_checker"),
            requirements=("just", "python_env"),
            expense="deterministic",
            row_dir=row_dir,
        ),
        _row(
            row_id="codex-open-task-live-eval",
            row_kind="live_agent_eval",
            command=_eval_suite_command(
                suite="map_build_consumer",
                budget="smoke",
                output_root=eval_output_root,
                stamp="codex-open-task-live-eval",
                agent_engine="codex-cli",
                provider_profile=codex_provider,
                live_execution="run",
            ),
            axes={
                "agent_engine": "codex-cli",
                "provider_profile": codex_provider,
                "intent": "open-ended",
                "preset": "",
                "evidence_lane": "world-oracle-labels",
                "backend": DEFAULT_BACKEND,
                "world": DEFAULT_WORLD,
            },
            reason="Open-task launch changes need a representative live Codex eval row.",
            rule_ids=("open_ended",),
            requirements=("just", "python_env", "docker", "codex_provider"),
            expense="live-agent",
            row_dir=row_dir,
        ),
        _row(
            row_id="codex-cleanup-live-eval",
            row_kind="live_agent_eval",
            command=_eval_suite_command(
                suite="cleanup_capability",
                budget="smoke",
                output_root=eval_output_root,
                stamp="codex-cleanup-live-eval",
                agent_engine="codex-cli",
                provider_profile=codex_provider,
                live_execution="run",
            ),
            axes={
                "agent_engine": "codex-cli",
                "provider_profile": codex_provider,
                "intent": "cleanup",
                "preset": "cleanup",
                "evidence_lane": "world-oracle-labels",
                "backend": DEFAULT_BACKEND,
                "world": DEFAULT_WORLD,
            },
            reason="Cleanup skill or MCP changes need a representative live Codex eval row.",
            rule_ids=("cleanup_skill", "mcp_checker"),
            requirements=("just", "python_env", "docker", "codex_provider"),
            expense="live-agent",
            row_dir=row_dir,
        ),
        _row(
            row_id="codex-cleanup-camera-raw-fpv-live-product",
            row_kind="live_agent_eval",
            command=_cleanup_command(
                row_dir=row_dir,
                row_id="codex-cleanup-camera-raw-fpv-live-product",
                agent_engine="codex-cli",
                provider_profile=codex_provider,
                evidence_lane="camera-raw-fpv",
            ),
            axes={
                "agent_engine": "codex-cli",
                "provider_profile": codex_provider,
                "intent": "cleanup",
                "preset": "cleanup",
                "evidence_lane": "camera-raw-fpv",
                "backend": DEFAULT_BACKEND,
                "world": DEFAULT_WORLD,
            },
            reason="RAW-FPV changes need a live or direct RAW-FPV cleanup gate.",
            rule_ids=("raw_fpv",),
            requirements=("just", "python_env", "docker", "codex_provider"),
            expense="live-agent",
            row_dir=row_dir,
        ),
        _row(
            row_id="openai-agents-sdk-open-task-live-eval",
            row_kind="live_agent_eval",
            command=_eval_suite_command(
                suite="cleanup_capability",
                budget="smoke",
                output_root=eval_output_root,
                stamp="openai-agents-sdk-open-task-live-eval",
                agent_engine="openai-agents-sdk",
                provider_profile=codex_provider,
                live_execution="run",
            ),
            axes={
                "agent_engine": "openai-agents-sdk",
                "provider_profile": codex_provider,
                "intent": "open-ended",
                "preset": "",
                "evidence_lane": "world-oracle-labels",
                "backend": DEFAULT_BACKEND,
                "world": DEFAULT_WORLD,
            },
            reason=(
                "Agent SDK runner or prompt changes need a representative live-agent "
                "capability eval row."
            ),
            rule_ids=("agent_sdk", "open_ended"),
            requirements=("just", "python_env", "openai_agents_package", "codex_provider"),
            expense="live-agent",
            row_dir=row_dir,
        ),
        _row(
            row_id="direct-camera-grounded-sim-control",
            row_kind="product_run",
            command=_cleanup_command(
                row_dir=row_dir,
                row_id="direct-camera-grounded-sim-control",
                agent_engine="direct-runner",
                evidence_lane="camera-grounded-labels",
                camera_labeler="sim-projected-labels",
            ),
            axes={
                "agent_engine": "direct-runner",
                "intent": "cleanup",
                "preset": "cleanup",
                "evidence_lane": "camera-grounded-labels",
                "camera_labeler": "sim-projected-labels",
                "backend": DEFAULT_BACKEND,
                "world": DEFAULT_WORLD,
            },
            reason="Visual-grounding changes need a deterministic camera-grounded control gate.",
            rule_ids=("visual_grounding",),
            requirements=("just", "python_env"),
            expense="local-sim",
            row_dir=row_dir,
        ),
        _row(
            row_id="direct-camera-grounded-grounding-dino",
            row_kind="product_run",
            command=_cleanup_command(
                row_dir=row_dir,
                row_id="direct-camera-grounded-grounding-dino",
                agent_engine="direct-runner",
                evidence_lane="camera-grounded-labels",
                camera_labeler="grounding-dino",
            ),
            axes={
                "agent_engine": "direct-runner",
                "intent": "cleanup",
                "preset": "cleanup",
                "evidence_lane": "camera-grounded-labels",
                "camera_labeler": "grounding-dino",
                "backend": DEFAULT_BACKEND,
                "world": DEFAULT_WORLD,
            },
            reason="Visual-grounding changes need a real Grounding DINO camera-labeler gate.",
            rule_ids=("visual_grounding",),
            requirements=("just", "python_env", "dino_sidecar"),
            expense="dino",
            row_dir=row_dir,
        ),
        _row(
            row_id="direct-camera-raw-fpv",
            row_kind="product_run",
            command=_cleanup_command(
                row_dir=row_dir,
                row_id="direct-camera-raw-fpv",
                agent_engine="direct-runner",
                evidence_lane="camera-raw-fpv",
            ),
            axes={
                "agent_engine": "direct-runner",
                "intent": "cleanup",
                "preset": "cleanup",
                "evidence_lane": "camera-raw-fpv",
                "backend": DEFAULT_BACKEND,
                "world": DEFAULT_WORLD,
            },
            reason="RAW-FPV changes need a direct RAW-FPV product gate.",
            rule_ids=("raw_fpv",),
            requirements=("just", "python_env"),
            expense="local-sim",
            row_dir=row_dir,
        ),
        _row(
            row_id="direct-map-build-world-oracle",
            row_kind="product_run",
            command=[
                "just",
                "run::surface",
                "surface=household-world",
                f"world={DEFAULT_WORLD}",
                f"backend={DEFAULT_BACKEND}",
                "preset=map-build",
                "agent_engine=direct-runner",
                "evidence_lane=world-oracle-labels",
                f"seed={DEFAULT_SEED}",
                "scenario_setup=baseline",
                f"output_dir={row_dir / 'direct-map-build-world-oracle' / 'run'}",
            ],
            axes={
                "agent_engine": "direct-runner",
                "intent": "map-build",
                "preset": "map-build",
                "evidence_lane": "world-oracle-labels",
                "backend": DEFAULT_BACKEND,
                "world": DEFAULT_WORLD,
            },
            reason="Map-build and actionability changes need a map-build lane gate.",
            rule_ids=("map_build",),
            requirements=("just", "python_env"),
            expense="local-sim",
            row_dir=row_dir,
        ),
        _row(
            row_id="direct-cleanup-runtime-prior-consumer",
            row_kind="product_run",
            command=[
                *_cleanup_command(
                    row_dir=row_dir,
                    row_id="direct-cleanup-runtime-prior-consumer",
                    agent_engine="direct-runner",
                    evidence_lane="world-oracle-labels",
                ),
                "runtime_map_prior=${direct-map-build-world-oracle:runtime_metric_map.json}",
            ],
            axes={
                "agent_engine": "direct-runner",
                "intent": "cleanup",
                "preset": "cleanup",
                "evidence_lane": "world-oracle-labels",
                "runtime_map_prior": "required",
                "backend": DEFAULT_BACKEND,
                "world": DEFAULT_WORLD,
            },
            reason="Map-build changes need a cleanup consumer gate with the runtime-map prior.",
            rule_ids=("map_build",),
            requirements=("just", "python_env", "runtime_map_prior"),
            expense="local-sim",
            row_dir=row_dir,
        ),
    ]


def _cleanup_command(
    *,
    row_dir: Path,
    row_id: str,
    agent_engine: str,
    evidence_lane: str,
    provider_profile: str = "",
    camera_labeler: str = "",
) -> list[str]:
    command = [
        "just",
        "run::surface",
        "surface=household-world",
        f"world={DEFAULT_WORLD}",
        f"backend={DEFAULT_BACKEND}",
        "preset=cleanup",
        f"agent_engine={agent_engine}",
        f"evidence_lane={evidence_lane}",
        f"seed={DEFAULT_SEED}",
        "scenario_setup=relocate-cleanup-related-objects",
        "relocation_count=5",
        f"output_dir={row_dir / row_id / 'run'}",
    ]
    if provider_profile:
        command.append(f"provider_profile={provider_profile}")
    if camera_labeler:
        command.append(f"camera_labeler={camera_labeler}")
    return command


def _eval_suite_command(
    *,
    suite: str,
    budget: str,
    output_root: Path,
    stamp: str,
    agent_engine: str = "direct-runner",
    provider_profile: str = "",
    live_execution: str = "blocked",
) -> list[str]:
    command = [
        "just",
        "agent::eval",
        f"suite={suite}",
        f"budget={budget}",
        f"output_dir={output_root}",
        f"stamp={stamp}",
        f"agent_engine={agent_engine}",
    ]
    if provider_profile:
        command.append(f"provider_profile={provider_profile}")
    if agent_engine != "direct-runner":
        command.append(f"live_execution={live_execution}")
    return command


def _row(
    *,
    row_id: str,
    row_kind: str,
    command: list[str],
    axes: dict[str, str],
    reason: str,
    rule_ids: tuple[str, ...],
    requirements: tuple[str, ...],
    expense: str,
    row_dir: Path,
) -> dict[str, Any]:
    return {
        "schema": ROW_SCHEMA,
        "row_id": row_id,
        "row_kind": row_kind,
        "command": [str(item) for item in command],
        "command_display": shlex.join(str(item) for item in command),
        "axes": axes,
        "reason_selected": reason,
        "selection_rule_ids": list(rule_ids),
        "source_signals": [],
        "selected": False,
        "requirement": "required",
        "expense": expense,
        "requires": list(requirements),
        "status": "skipped_irrelevant",
        "blocker_category": "",
        "skip_reason": "no matching source signal or explicit override",
        "output_artifacts": [],
        "row_dir": str(row_dir / row_id),
    }
