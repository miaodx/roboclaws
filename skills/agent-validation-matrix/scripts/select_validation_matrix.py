#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    REPO_ROOT = Path(__file__).resolve().parents[3]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
else:
    REPO_ROOT = Path(__file__).resolve().parents[3]

MATRIX_SCHEMA = "agent_validation_matrix_v1"
GATE_SCHEMA = "agent_validation_gate_v1"
DEFAULT_WORLD = "molmospaces/val_0"
DEFAULT_BACKEND = "mujoco"
DEFAULT_SEED = "7"
DEFAULT_PROVIDER_PROFILE = "codex-env"
DEFAULT_OUTPUT_ROOT = Path("output/agent-validation-matrix")

SIGNAL_RULES: tuple[dict[str, Any], ...] = (
    {
        "id": "agent_sdk",
        "label": "Agent SDK",
        "patterns": (
            r"openai[_-]agents",
            r"agents/drivers/openai_agents_live\.py",
            r"run_live_openai_agents_cleanup\.py",
            r"agent_engine=.?openai-agents-sdk",
            r"Agent SDK",
        ),
    },
    {
        "id": "cleanup_skill",
        "label": "Cleanup skill or prompt",
        "patterns": (
            r"skills/molmo-realworld-cleanup/",
            r"household_cleanup",
            r"semantic_cleanup_loop",
            r"trace_preserving_cleanup",
            r"\bcleanup\b",
        ),
    },
    {
        "id": "open_ended",
        "label": "Open-ended household intent",
        "patterns": (
            r"open[-_]ended",
            r"goal_contract",
            r"task_intent",
            r"completion_claim",
            r"agent-declared",
        ),
    },
    {
        "id": "mcp_checker",
        "label": "MCP/server/checker contract",
        "patterns": (
            r"realworld_mcp_server",
            r"realworld_mcp_semantic_tools",
            r"realworld_contract",
            r"\bdone\b",
            r"checker",
            r"report contract",
        ),
    },
    {
        "id": "visual_grounding",
        "label": "Visual grounding or camera labeler",
        "patterns": (
            r"visual_grounding",
            r"camera_labeler",
            r"grounding[-_]dino",
            r"camera-grounded-labels",
            r"\bDINO\b",
        ),
    },
    {
        "id": "raw_fpv",
        "label": "RAW-FPV",
        "patterns": (
            r"raw[_-]fpv",
            r"camera-raw-fpv",
            r"RAW-FPV",
        ),
    },
    {
        "id": "map_build",
        "label": "Semantic map, runtime map, or actionability",
        "patterns": (
            r"semantic[-_]map",
            r"map-build",
            r"runtime_metric_map",
            r"runtime map",
            r"actionability",
            r"target_query",
            r"generated waypoint",
            r"waypoint",
        ),
    },
    {
        "id": "launch_catalog",
        "label": "Launch catalog or product route",
        "patterns": (
            r"roboclaws/launch/",
            r"just/",
            r"operator_console",
            r"provider_profile",
            r"run::surface",
            r"agent::harness",
        ),
    },
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select an adaptive Roboclaws agent-validation matrix.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--mode", choices=("recommend", "execute"), default="recommend")
    parser.add_argument("--budget", choices=("smoke", "focused", "full"), default="focused")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--since")
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument("--agent-engine", default="")
    parser.add_argument("--provider-profile", default="")
    parser.add_argument("--intent", default="")
    parser.add_argument("--preset", default="")
    parser.add_argument("--evidence-lane", default="")
    parser.add_argument("--camera-labeler", default="")
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    matrix = build_validation_matrix(
        mode=args.mode,
        budget=args.budget,
        plan=args.plan,
        since=args.since,
        changed_files=_split_csv_values(args.changed_file),
        agent_engine=_split_csv(args.agent_engine),
        provider_profile=_split_csv(args.provider_profile),
        intent=_split_csv(args.intent),
        preset=_split_csv(args.preset),
        evidence_lane=_split_csv(args.evidence_lane),
        camera_labeler=_split_csv(args.camera_labeler),
        output_dir=args.output_dir,
    )
    print(json.dumps(matrix, indent=2, sort_keys=True))
    return 0


def build_validation_matrix(
    *,
    mode: str = "recommend",
    budget: str = "focused",
    plan: Path | None = None,
    since: str | None = None,
    changed_files: Sequence[str] = (),
    agent_engine: Sequence[str] = (),
    provider_profile: Sequence[str] = (),
    intent: Sequence[str] = (),
    preset: Sequence[str] = (),
    evidence_lane: Sequence[str] = (),
    camera_labeler: Sequence[str] = (),
    output_dir: Path | None = None,
) -> dict[str, Any]:
    plan_text, plan_path = _read_plan(plan)
    if since:
        diff_files = _changed_files_from_git(since)
    elif plan is None and not changed_files:
        diff_files = _changed_files_from_worktree()
    else:
        diff_files = []
    all_changed_files = _dedupe([*diff_files, *changed_files])
    explicit_axes = {
        "agent_engine": _dedupe(agent_engine),
        "provider_profile": _dedupe(provider_profile),
        "intent": _dedupe(intent),
        "preset": _dedupe(preset),
        "evidence_lane": _dedupe(evidence_lane),
        "camera_labeler": _dedupe(camera_labeler),
    }
    signals = _detect_signals(
        plan_text=plan_text,
        changed_files=all_changed_files,
        explicit_axes=explicit_axes,
    )
    output_dir = output_dir or _default_output_dir()
    gates = _candidate_gates(output_dir=output_dir, explicit_axes=explicit_axes)
    _apply_selection_rules(gates, signals=signals, budget=budget, explicit_axes=explicit_axes)
    selected = [gate for gate in gates if gate["selected"]]
    return {
        "schema": MATRIX_SCHEMA,
        "generated_at": _utc_timestamp(),
        "mode": mode,
        "budget": budget,
        "plan": str(plan_path) if plan_path else "",
        "since": since or "",
        "changed_files": all_changed_files,
        "explicit_axes": explicit_axes,
        "signals": signals,
        "summary": {
            "gate_count": len(gates),
            "selected_gate_count": len(selected),
            "required_gate_count": sum(1 for gate in selected if gate["requirement"] == "required"),
            "budget_skipped_count": sum(
                1 for gate in gates if gate["status"] == "required_skipped_by_user_budget"
            ),
        },
        "output_dir": str(output_dir),
        "gates": gates,
    }


def _read_plan(plan: Path | None) -> tuple[str, Path | None]:
    if plan is None:
        return "", None
    plan_path = Path(plan)
    if not plan_path.is_absolute():
        plan_path = REPO_ROOT / plan_path
    return plan_path.read_text(encoding="utf-8"), plan_path.relative_to(REPO_ROOT)


def _changed_files_from_git(since: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", since, "--"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _changed_files_from_worktree() -> list[str]:
    paths: list[str] = []
    for args in (["git", "diff", "--name-only"], ["git", "diff", "--cached", "--name-only"]):
        result = subprocess.run(
            args,
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            paths.extend(line.strip() for line in result.stdout.splitlines() if line.strip())
    return _dedupe(paths)


def _detect_signals(
    *,
    plan_text: str,
    changed_files: Sequence[str],
    explicit_axes: dict[str, list[str]],
) -> list[dict[str, Any]]:
    haystacks = [plan_text, "\n".join(changed_files)]
    signals: list[dict[str, Any]] = []
    for rule in SIGNAL_RULES:
        matches: list[str] = []
        for pattern in rule["patterns"]:
            regex = re.compile(pattern, re.IGNORECASE)
            for haystack in haystacks:
                if regex.search(haystack):
                    matches.append(pattern)
                    break
        matched_files = [
            path
            for path in changed_files
            if any(re.search(pattern, path, re.IGNORECASE) for pattern in rule["patterns"])
        ]
        if matches or matched_files:
            signals.append(
                {
                    "id": rule["id"],
                    "label": rule["label"],
                    "matched_patterns": _dedupe(matches),
                    "matched_files": _dedupe(matched_files),
                    "source": "plan_or_diff",
                }
            )
    if "openai-agents-sdk" in explicit_axes.get("agent_engine", []):
        signals.append(_override_signal("agent_sdk", "agent_engine=openai-agents-sdk"))
    if "codex-cli" in explicit_axes.get("agent_engine", []):
        signals.append(_override_signal("cleanup_skill", "agent_engine=codex-cli"))
    if "open-ended" in explicit_axes.get("intent", []):
        signals.append(_override_signal("open_ended", "intent=open-ended"))
    if "cleanup" in explicit_axes.get("preset", []):
        signals.append(_override_signal("cleanup_skill", "preset=cleanup"))
    if "map-build" in explicit_axes.get("preset", []):
        signals.append(_override_signal("map_build", "preset=map-build"))
    if "camera-grounded-labels" in explicit_axes.get("evidence_lane", []):
        signals.append(_override_signal("visual_grounding", "evidence_lane=camera-grounded-labels"))
    if "camera-raw-fpv" in explicit_axes.get("evidence_lane", []):
        signals.append(_override_signal("raw_fpv", "evidence_lane=camera-raw-fpv"))
    if "grounding-dino" in explicit_axes.get("camera_labeler", []):
        signals.append(_override_signal("visual_grounding", "camera_labeler=grounding-dino"))
    return _merge_signals(signals)


def _candidate_gates(
    *, output_dir: Path, explicit_axes: dict[str, list[str]]
) -> list[dict[str, Any]]:
    provider_profiles = explicit_axes.get("provider_profile") or [DEFAULT_PROVIDER_PROFILE]
    codex_provider = provider_profiles[0]
    gate_dir = output_dir / "gates"
    return [
        _gate(
            gate_id="route-trace-contract-tests",
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
            gate_dir=gate_dir,
        ),
        _gate(
            gate_id="cleanup-contract-tests",
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
            gate_dir=gate_dir,
        ),
        _gate(
            gate_id="household-direct-world-oracle-product",
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
                f"output_dir={gate_dir / 'household-direct-world-oracle-product' / 'run'}",
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
            gate_dir=gate_dir,
        ),
        _gate(
            gate_id="open-ended-household-contract-tests",
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
            axes={
                "intent": "open-ended",
            },
            reason=(
                "Open-ended, goal-contract, or completion-claim changes need a "
                "first-class open-ended launch and artifact contract gate."
            ),
            rule_ids=("open_ended",),
            requirements=("python_env",),
            expense="deterministic",
            gate_dir=gate_dir,
        ),
        _gate(
            gate_id="codex-open-task-world-oracle",
            command=_open_task_command(
                gate_dir=gate_dir,
                gate_id="codex-open-task-world-oracle",
                agent_engine="codex-cli",
                provider_profile=codex_provider,
                evidence_lane="world-oracle-labels",
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
            reason="Open-task launch changes need a representative live Codex household gate.",
            rule_ids=("open_ended",),
            requirements=("just", "python_env", "docker", "codex_provider"),
            expense="live-agent",
            gate_dir=gate_dir,
        ),
        _gate(
            gate_id="codex-cleanup-world-oracle",
            command=_cleanup_command(
                gate_dir=gate_dir,
                gate_id="codex-cleanup-world-oracle",
                agent_engine="codex-cli",
                provider_profile=codex_provider,
                evidence_lane="world-oracle-labels",
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
            reason="Cleanup skill or MCP changes need a representative live Codex cleanup gate.",
            rule_ids=("cleanup_skill", "mcp_checker"),
            requirements=("just", "python_env", "docker", "codex_provider"),
            expense="live-agent",
            gate_dir=gate_dir,
        ),
        _gate(
            gate_id="codex-cleanup-camera-raw-fpv",
            command=_cleanup_command(
                gate_dir=gate_dir,
                gate_id="codex-cleanup-camera-raw-fpv",
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
            gate_dir=gate_dir,
        ),
        _gate(
            gate_id="openai-agents-sdk-open-task",
            command=_open_task_command(
                gate_dir=gate_dir,
                gate_id="openai-agents-sdk-open-task",
                agent_engine="openai-agents-sdk",
                provider_profile=codex_provider,
                evidence_lane="world-oracle-labels",
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
                "Agent SDK runner or prompt changes need a no-preset household open-task "
                "product gate."
            ),
            rule_ids=("agent_sdk", "open_ended"),
            requirements=("just", "python_env", "openai_agents_package", "codex_provider"),
            expense="live-agent",
            gate_dir=gate_dir,
        ),
        _gate(
            gate_id="direct-camera-grounded-sim-control",
            command=_cleanup_command(
                gate_dir=gate_dir,
                gate_id="direct-camera-grounded-sim-control",
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
            gate_dir=gate_dir,
        ),
        _gate(
            gate_id="direct-camera-grounded-grounding-dino",
            command=_cleanup_command(
                gate_dir=gate_dir,
                gate_id="direct-camera-grounded-grounding-dino",
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
            gate_dir=gate_dir,
        ),
        _gate(
            gate_id="direct-camera-raw-fpv",
            command=_cleanup_command(
                gate_dir=gate_dir,
                gate_id="direct-camera-raw-fpv",
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
            gate_dir=gate_dir,
        ),
        _gate(
            gate_id="direct-map-build-world-oracle",
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
                f"output_dir={gate_dir / 'direct-map-build-world-oracle' / 'run'}",
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
            gate_dir=gate_dir,
        ),
        _gate(
            gate_id="direct-cleanup-runtime-prior-consumer",
            command=[
                *_cleanup_command(
                    gate_dir=gate_dir,
                    gate_id="direct-cleanup-runtime-prior-consumer",
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
            gate_dir=gate_dir,
        ),
    ]


def _cleanup_command(
    *,
    gate_dir: Path,
    gate_id: str,
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
        f"output_dir={gate_dir / gate_id / 'run'}",
    ]
    if provider_profile:
        command.append(f"provider_profile={provider_profile}")
    if camera_labeler:
        command.append(f"camera_labeler={camera_labeler}")
    return command


def _open_task_command(
    *,
    gate_dir: Path,
    gate_id: str,
    agent_engine: str,
    evidence_lane: str,
    provider_profile: str = "",
) -> list[str]:
    command = [
        "just",
        "run::surface",
        "surface=household-world",
        f"world={DEFAULT_WORLD}",
        f"backend={DEFAULT_BACKEND}",
        f"agent_engine={agent_engine}",
        f"evidence_lane={evidence_lane}",
        f"seed={DEFAULT_SEED}",
        "scenario_setup=baseline",
        "prompt=我渴了，帮我找些解渴的东西",
        f"output_dir={gate_dir / gate_id / 'run'}",
    ]
    if provider_profile:
        command.append(f"provider_profile={provider_profile}")
    return command


def _gate(
    *,
    gate_id: str,
    command: list[str],
    axes: dict[str, str],
    reason: str,
    rule_ids: tuple[str, ...],
    requirements: tuple[str, ...],
    expense: str,
    gate_dir: Path,
) -> dict[str, Any]:
    return {
        "schema": GATE_SCHEMA,
        "gate_id": gate_id,
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
        "status": "recommended_skipped_irrelevant",
        "blocker_category": "",
        "skip_reason": "no matching source signal or explicit override",
        "output_artifacts": [],
        "gate_dir": str(gate_dir / gate_id),
    }


def _apply_selection_rules(
    gates: list[dict[str, Any]],
    *,
    signals: list[dict[str, Any]],
    budget: str,
    explicit_axes: dict[str, list[str]],
) -> None:
    signal_ids = {signal["id"] for signal in signals}
    signal_by_id = {signal["id"]: signal for signal in signals}
    for gate in gates:
        matching = [rule_id for rule_id in gate["selection_rule_ids"] if rule_id in signal_ids]
        if _explicitly_matches(gate, explicit_axes):
            matching.append("explicit_override")
        matching = _dedupe(matching)
        if not matching:
            continue
        gate["selected"] = True
        gate["source_signals"] = [
            signal_by_id[rule_id]
            for rule_id in matching
            if rule_id != "explicit_override" and rule_id in signal_by_id
        ]
        if "explicit_override" in matching:
            gate["source_signals"].append(
                {
                    "id": "explicit_override",
                    "label": "Explicit override",
                    "matched_patterns": [],
                    "matched_files": [],
                    "source": "user_override",
                }
            )
        gate["skip_reason"] = ""
        if budget == "smoke" and gate["expense"] != "deterministic":
            gate["status"] = "required_skipped_by_user_budget"
            gate["skip_reason"] = "budget=smoke runs deterministic confidence only"
        else:
            gate["status"] = "optional_not_run"


def _explicitly_matches(gate: dict[str, Any], explicit_axes: dict[str, list[str]]) -> bool:
    axes = gate["axes"]
    for key, requested_values in explicit_axes.items():
        if requested_values and axes.get(key) in requested_values:
            return True
    return False


def _override_signal(signal_id: str, value: str) -> dict[str, Any]:
    return {
        "id": signal_id,
        "label": f"Explicit {signal_id}",
        "matched_patterns": [value],
        "matched_files": [],
        "source": "user_override",
    }


def _merge_signals(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for signal in signals:
        current = merged.setdefault(
            signal["id"],
            {
                "id": signal["id"],
                "label": signal["label"],
                "matched_patterns": [],
                "matched_files": [],
                "source": signal["source"],
            },
        )
        current["matched_patterns"] = _dedupe(
            [*current["matched_patterns"], *signal.get("matched_patterns", [])]
        )
        current["matched_files"] = _dedupe(
            [*current["matched_files"], *signal.get("matched_files", [])]
        )
        if current["source"] != signal["source"]:
            current["source"] = "plan_or_diff_and_user_override"
    return list(merged.values())


def _split_csv(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _split_csv_values(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        result.extend(_split_csv(value))
    return result


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _utc_timestamp() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_output_dir() -> Path:
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_OUTPUT_ROOT / stamp


if __name__ == "__main__":
    raise SystemExit(main())
