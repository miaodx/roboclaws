from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from roboclaws.agents.prompts.household_cleanup import (
    render_kickoff_prompt,
    render_semantic_map_build_prompt,
)
from roboclaws.devtools.commands import CommandError, resolve_surface_run
from roboclaws.launch import resolve_surface_launch
from roboclaws.launch.evaluation import (
    checker_flags_for_household_intent,
    household_intent_id_for_checker,
)
from roboclaws.launch.runners import export_env_from_overrides

REPO_ROOT = Path(__file__).resolve().parents[3]
JUSTFILE = REPO_ROOT / "justfile"
JUST_DIR = REPO_ROOT / "just"
AGENT_JUST = JUST_DIR / "agent.just"
CODE_JUST = JUST_DIR / "code.just"
OPENCLAW_JUST = JUST_DIR / "openclaw.just"
MOLMO_JUST = JUST_DIR / "molmo.just"
CODING_AGENT_ENV = REPO_ROOT / "scripts" / "dev" / "coding_agent_env.sh"
CODING_AGENT_DOCKER = REPO_ROOT / "scripts" / "dev" / "coding_agent_docker.sh"
LIVE_CODEX_RUNNER = REPO_ROOT / "scripts" / "molmo_cleanup" / "run_live_codex_cleanup.py"
LIVE_CLAUDE_RUNNER = REPO_ROOT / "scripts" / "molmo_cleanup" / "run_live_claude_cleanup.py"
LIVE_OPENAI_AGENTS_RUNNER = (
    REPO_ROOT / "scripts" / "molmo_cleanup" / "run_live_openai_agents_cleanup.py"
)
AGIBOT_MAP_BUILD_CODEX_RUNNER = (
    REPO_ROOT / "scripts" / "molmo_cleanup" / "run_live_codex_agibot_map_build.py"
)
HOUSEHOLD_AGENT_SERVER_MODULE = "roboclaws.cli.agent_server"
CODE_AGENT_ENV_VARS = (
    "ROBOCLAWS_CODE_AGENT_PROVIDER",
    "ROBOCLAWS_CODEX_PROVIDER",
    "ROBOCLAWS_CLAUDE_PROVIDER",
    "ROBOCLAWS_CODE_AGENT_MODEL",
    "ROBOCLAWS_CODEX_MODEL",
    "ROBOCLAWS_CLAUDE_MODEL",
    "ROBOCLAWS_CODEX_DISABLE_RESPONSES_WEBSOCKETS",
    "KIMI_API_KEY",
    "MIMO_TP_KEY",
    "OPENAI_API_KEY",
    "CODEX_BASE_URL",
    "CODEX_API_KEY",
    "XM_LLM_BASE_URL",
    "XM_LLM_API_KEY",
)


def just_bin() -> str:
    path = shutil.which("just")
    if path:
        return path
    local_path = Path.home() / ".local/bin" / "just"
    if local_path.exists():
        return str(local_path)
    pytest.skip("just binary is not available")


def just_summary() -> set[str]:
    result = subprocess.run(
        [just_bin(), "--summary"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return set(result.stdout.split())


def trace_task_run(*args: str) -> list[str]:
    return trace_surface_run(*surface_args_from_legacy_task_args(*args))


def trace_task_run_with_plan(*args: str) -> tuple[list[str], list[str]]:
    return trace_surface_run_with_plan(*surface_args_from_legacy_task_args(*args))


def trace_surface_run(*args: str) -> list[str]:
    binary = just_bin()
    env = os.environ.copy()
    env["ROBOCLAWS_JUST_TRACE"] = "1"
    env["PATH"] = f"{Path(binary).parent}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        [binary, "run::surface", *args],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().split("\t")


def trace_surface_run_with_plan(*args: str) -> tuple[list[str], list[str]]:
    binary = just_bin()
    env = os.environ.copy()
    env["ROBOCLAWS_JUST_TRACE"] = "1"
    env["PATH"] = f"{Path(binary).parent}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        [binary, "run::surface", *args],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().split("\t"), result.stderr.strip().split("\t")


def trace_agent_harness(*args: str) -> list[str]:
    binary = just_bin()
    env = os.environ.copy()
    env["ROBOCLAWS_JUST_TRACE"] = "1"
    env["PATH"] = f"{Path(binary).parent}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        [binary, "agent::harness", *args],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().split("\t")


def trace_agent_verify(*args: str) -> list[str]:
    binary = just_bin()
    env = os.environ.copy()
    env["ROBOCLAWS_JUST_TRACE"] = "1"
    env["PATH"] = f"{Path(binary).parent}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        [binary, "agent::verify", *args],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().split("\t")


def trace_agent_run(*args: str) -> list[str]:
    binary = just_bin()
    env = os.environ.copy()
    env["ROBOCLAWS_JUST_TRACE"] = "1"
    env["PATH"] = f"{Path(binary).parent}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        [binary, "agent::run", *args],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().split("\t")


def assert_task_run_fails(*args: str) -> str:
    return assert_surface_run_fails(*surface_args_from_legacy_task_args(*args))


def assert_agent_run_fails(*args: str) -> str:
    binary = just_bin()
    env = os.environ.copy()
    env["ROBOCLAWS_JUST_TRACE"] = "1"
    env["PATH"] = f"{Path(binary).parent}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        [binary, "agent::run", *args],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    return result.stderr


def assert_surface_run_fails(*args: str) -> str:
    binary = just_bin()
    env = os.environ.copy()
    env["ROBOCLAWS_JUST_TRACE"] = "1"
    env["PATH"] = f"{Path(binary).parent}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        [binary, "run::surface", *args],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    return result.stderr


def surface_args_from_legacy_task_args(*args: str) -> tuple[str, ...]:
    task = args[0] if args else ""
    driver = args[1] if len(args) > 1 else ""
    mode = args[2] if len(args) > 2 else ""
    overrides = list(args[3:])
    if mode and "=" in mode:
        overrides.insert(0, mode)
        mode = ""

    task_map = {
        "ai2thor-nav": ("surface=ai2thor-world", "intent=navigate"),
        "photo-chairs": ("surface=ai2thor-world", "intent=photo-capture"),
        "territory": ("surface=ai2thor-games", "intent=territory"),
        "coverage": ("surface=ai2thor-games", "intent=coverage"),
        "semantic-map-build": ("surface=household-world", "intent=map-build"),
        "household-cleanup": ("surface=household-world", "intent=cleanup"),
        "molmo-cleanup": ("surface=household-world", "intent=cleanup"),
        "molmo-planner-proof": ("surface=planner-proof", "intent=planner-proof"),
    }
    engine_map = {
        "codex": "agent_engine=codex-cli",
        "claude": "agent_engine=claude-code",
        "openai-agents-live": "agent_engine=openai-agents-sdk",
        "direct": "agent_engine=direct-runner",
        "mcp-smoke": "agent_engine=direct-runner",
        "openclaw": "agent_engine=openclaw-gateway",
        "vlm": "agent_engine=vlm-policy",
        "script": "agent_engine=script-runner",
    }
    normalized_overrides: list[str] = []
    for override in overrides:
        if override == "backend=molmospaces_subprocess":
            normalized_overrides.append("world=molmospaces/val_0")
            normalized_overrides.append("backend=mujoco")
        elif override == "backend=isaaclab_subprocess":
            normalized_overrides.append("world=molmospaces/val_0")
            normalized_overrides.append("backend=isaaclab")
        elif override == "backend=agibot_gdk":
            normalized_overrides.append("world=agibot-g2/map-12")
            normalized_overrides.append("backend=agibot-gdk")
        elif override == "backend=agibot_molmospaces_sim":
            normalized_overrides.append("world=agibot-g2/map-12")
            normalized_overrides.append("backend=agibot-gdk")
            normalized_overrides.append("backend_implementation=agibot_molmospaces_sim")
        elif override.startswith("environment_setup="):
            normalized_overrides.append(
                override.replace("environment_setup=", "scenario_setup=", 1)
            )
        else:
            normalized_overrides.append(override)

    surface_parts = list(task_map.get(task, (f"surface={task}",)))
    engine = engine_map.get(driver, f"agent_engine={driver}") if driver else ""
    result = [*surface_parts]
    if engine:
        result.append(engine)
    if mode:
        if surface_parts[0] in {"surface=household-world", "surface=planner-proof"}:
            result.append(f"evidence_lane={mode}")
        else:
            result.append(f"report={mode}")
    result.extend(normalized_overrides)
    return tuple(result)


def clean_code_agent_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in CODE_AGENT_ENV_VARS:
        env.pop(key, None)
    return env


def load_script_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_public_just_summary_is_small_facade() -> None:
    summary = just_summary()

    assert summary == {
        "run::surface",
        "agent::run",
        "agent::verify",
        "agent::harness",
        "agent::mcp",
        "agent::gateway",
        "console::run",
    }

    hidden_recipes = {
        "openclaw::run",
        "vlm::run",
        "molmo::cleanup",
        "harness::molmo-realworld-cleanup",
        "verify::mock",
        "code::codex",
        "task::territory",
        "agent::codex-nav",
    }
    assert summary.isdisjoint(hidden_recipes)


def test_molmo_codex_harness8_recipe_traces_to_runner(tmp_path: Path) -> None:
    binary = just_bin()
    env = os.environ.copy()
    env["PATH"] = f"{Path(binary).parent}{os.pathsep}{env.get('PATH', '')}"
    output_dir = tmp_path / "codex-harness8"
    result = subprocess.run(
        [
            binary,
            "molmo::codex-harness8",
            "dry-run",
            f"output_dir={output_dir}",
            "row=direct-world-public-labels",
            "provider_retry_attempts=2",
            "provider_retry_sleep_s=0",
            "parallelism=2",
            "base_port=18788",
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert f"codex harness8 manifest: {output_dir / 'codex_cleanup_harness8.json'}" in result.stdout
    manifest = json.loads((output_dir / "codex_cleanup_harness8.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "codex_cleanup_harness8_v1"
    assert manifest["parallelism"] == 2
    assert manifest["base_port"] == 18788
    assert len(manifest["rows"]) == 8
    assert {row["row_id"] for row in manifest["rows"]} == {
        "direct-world-oracle-labels",
        "direct-world-public-labels",
        "direct-camera-grounded-labels-grounding-dino",
        "direct-camera-raw-fpv",
        "dino-prior-world-oracle-labels",
        "dino-prior-world-public-labels",
        "dino-prior-camera-grounded-labels-grounding-dino",
        "dino-prior-camera-raw-fpv",
    }
    setup_command = manifest["setup_rows"][0]["command"]
    assert setup_command[:8] == [
        "just",
        "run::surface",
        "surface=household-world",
        "world=molmospaces/val_0",
        "backend=mujoco",
        "intent=map-build",
        "agent_engine=direct-runner",
        "evidence_lane=camera-grounded-labels",
    ]
    assert "scenario_setup=baseline" in setup_command
    assert "camera_labeler=grounding-dino" in setup_command
    direct_rows = {
        row["row_id"]: row
        for row in manifest["rows"]
        if row["row_id"] in {"direct-world-oracle-labels", "direct-world-public-labels"}
    }
    assert direct_rows["direct-world-oracle-labels"]["assigned_port"] == 18788
    assert direct_rows["direct-world-public-labels"]["assigned_port"] == 18790
    assert "port=18788" in direct_rows["direct-world-oracle-labels"]["command"]
    assert "port=18790" in direct_rows["direct-world-public-labels"]["command"]
    assert (
        direct_rows["direct-world-oracle-labels"]["env"]["ROBOCLAWS_MOLMO_MAX_VISUAL_BACKENDS"]
        == "2"
    )


def test_agent_harness_allows_codex_cleanup_harness8_target() -> None:
    route = trace_agent_harness(
        "codex-cleanup-harness8",
        "dry-run",
        "output_dir=/tmp/roboclaws-codex-harness8",
        "row=direct-world-oracle-labels",
        "parallelism=2",
    )

    assert route == [
        "just",
        "harness::codex-cleanup-harness8",
        "dry-run",
        "output_dir=/tmp/roboclaws-codex-harness8",
        "row=direct-world-oracle-labels",
        "parallelism=2",
    ]


def test_justfile_marks_implementation_modules_private() -> None:
    text = JUSTFILE.read_text(encoding="utf-8")

    for module in (
        "openclaw",
        "vlm",
        "chat",
        "appliance",
        "dev",
        "mcp",
        "code",
        "harness",
        "verify",
        "molmo",
    ):
        assert re.search(
            rf"^\[private\]\nmod {module}\s+'just/{module}\.just'$",
            text,
            re.MULTILINE,
        )

    assert re.search(r"^mod agent\s+'just/agent\.just'$", text, re.MULTILINE)
    assert re.search(r"^mod run\s+'just/run\.just'$", text, re.MULTILINE)


def test_agent_module_exposes_compact_dispatchers() -> None:
    text = AGENT_JUST.read_text(encoding="utf-8")

    expected_headers = (
        r"^run dispatch_target agent_engine mode=\"\" \*overrides:",
        r"^verify target=\"mock\" \*args:",
        r"^harness target \*args:",
        r"^mcp action=\"up\"",
        r"^gateway action=\"up\"",
    )
    for header in expected_headers:
        assert re.search(header, text, re.MULTILINE), f"missing recipe header: {header}"

    removed_combo_aliases = (
        "codex-nav",
        "claude-nav",
        "openclaw-territory",
        "vlm-coverage",
        "script-territory",
    )
    for alias in removed_combo_aliases:
        assert not re.search(rf"^{alias}\b", text, re.MULTILINE)


def test_agent_verify_routes_required_ci_gate_to_verify_module() -> None:
    route = trace_agent_verify("ci-required", "output_dir=output/custom-demo", "steps=3")

    assert route == [
        "just",
        "verify::ci-required",
        "output_dir=output/custom-demo",
        "steps=3",
    ]


def test_agent_harness_allows_molmo_codex_perf_target() -> None:
    agent_text = AGENT_JUST.read_text(encoding="utf-8")
    harness_text = (JUST_DIR / "harness.just").read_text(encoding="utf-8")

    assert "molmo-cleanup-codex-perf" in agent_text
    assert re.search(r"^molmo-cleanup-codex-perf \*overrides:", harness_text, re.MULTILINE)
    assert 'just molmo::cleanup "codex-live" "world-oracle-labels"' in harness_text
    assert '"skill" "$robot_views"' in harness_text


def test_agent_harness_allows_codex_cleanup_harness8() -> None:
    agent_text = AGENT_JUST.read_text(encoding="utf-8")
    harness_text = (JUST_DIR / "harness.just").read_text(encoding="utf-8")

    assert "codex-cleanup-harness8" in agent_text
    assert re.search(
        r"^codex-cleanup-harness8 mode=\"dry-run\" \*overrides:",
        harness_text,
        re.MULTILINE,
    )
    assert "just molmo::codex-harness8" in harness_text


def test_agent_harness_allows_molmo_visual_grounding_benchmark_target() -> None:
    agent_text = AGENT_JUST.read_text(encoding="utf-8")
    harness_text = (JUST_DIR / "harness.just").read_text(encoding="utf-8")

    assert "molmo-visual-grounding-benchmark" in agent_text
    assert re.search(r"^molmo-visual-grounding-benchmark \*overrides:", harness_text, re.MULTILINE)
    assert "run_visual_grounding_benchmark.py" in harness_text
    assert "check_visual_grounding_benchmark_result.py" in harness_text

    route = trace_agent_harness(
        "molmo-visual-grounding-benchmark",
        "pipeline=fake-http",
        "output_dir=/tmp/roboclaws-vg",
    )
    assert route == [
        "just",
        "harness::molmo-visual-grounding-benchmark",
        "pipeline=fake-http",
        "output_dir=/tmp/roboclaws-vg",
    ]


def test_task_module_is_removed_from_public_facade() -> None:
    summary = just_summary()
    assert "run::surface" in summary
    assert "task::run" not in summary
    assert "task::navigate" not in summary
    assert "task::cleanup-report" not in summary
    assert not (JUST_DIR / "task.just").exists()


def test_run_module_exposes_surface_publicly() -> None:
    text = (JUST_DIR / "run.just").read_text(encoding="utf-8")

    assert re.search(r"^surface \*overrides:", text, re.MULTILINE)
    assert "-m roboclaws.cli.main run surface" in text


def test_surface_prompt_mapping_household_cleanup_codex_world_labels_default() -> None:
    route = trace_surface_run(
        "surface=household-world",
        "agent_engine=codex-cli",
        "intent=cleanup",
    )

    assert route[:6] == [
        "just",
        "molmo::cleanup",
        "codex-live",
        "world-oracle-labels",
        "7",
        "output/household/household-cleanup/codex-report",
    ]


def test_surface_prompt_omitted_intent_with_prompt_infers_open_ended() -> None:
    route, plan_trace = trace_surface_run_with_plan(
        "surface=household-world",
        "agent_engine=codex-cli",
        "prompt=我渴了，帮我找些解渴的东西",
    )

    assert route[:6] == [
        "just",
        "molmo::cleanup",
        "codex-live",
        "world-oracle-labels",
        "7",
        "output/household/household-cleanup/codex-report",
    ]
    assert "我渴了，帮我找些解渴的东西" in route
    assert route[-1] == "custom"
    assert plan_trace[:5] == [
        "launch-plan",
        "surface=household-world",
        "world=molmospaces/val_0",
        "backend=mujoco",
        "intent=open-ended",
    ]
    assert "prompt=household_open_ended" in plan_trace
    assert "checker=open_ended_report" in plan_trace
    assert "goal=我渴了，帮我找些解渴的东西" in plan_trace


def test_surface_open_ended_supports_mcp_smoke_for_local_gate() -> None:
    plan = resolve_surface_launch(
        (
            "surface=household-world",
            "agent_engine=direct-runner",
            "intent=open-ended",
            "evidence_lane=smoke",
            "prompt=我渴了，帮我找些解渴的东西",
        )
    )
    env = export_env_from_overrides(plan.overrides)

    assert plan.surface == "household-world"
    assert plan.intent == "open-ended"
    assert plan.agent_engine == "direct-runner"
    assert plan.dispatch_runner == "mcp-smoke"
    assert plan.internal_runner_class == "smoke"
    assert plan.goal_contract.goal_scope == "agent-declared"
    assert env["ROBOCLAWS_TASK_INTENT"] == "open-ended"
    assert json.loads(env["ROBOCLAWS_GOAL_CONTRACT_JSON"])["intent"] == "open-ended"


def test_surface_cleanup_prompt_stays_cleanup_intent_when_explicit() -> None:
    plan = resolve_surface_launch(
        (
            "surface=household-world",
            "agent_engine=codex-cli",
            "intent=cleanup",
            "prompt=只收拾桌面上的杯子",
        )
    )

    assert plan.surface == "household-world"
    assert plan.intent == "cleanup"
    assert plan.prompt_id == "household_cleanup"
    assert plan.checker_id == "cleanup_report"
    assert plan.goal_contract.goal_scope == "prompt-scoped"
    assert plan.goal_contract.raw_prompt == "只收拾桌面上的杯子"
    assert "user-scoped request" in plan.goal_contract.normalized_goal


def test_surface_launch_plan_exposes_goal_contract_and_evaluation_policy() -> None:
    plan = resolve_surface_launch(
        (
            "surface=household-world",
            "agent_engine=codex-cli",
            "intent=map-build",
            "evidence_lane=world-oracle-labels",
        )
    )

    assert plan.surface == "household-world"
    assert plan.world == "molmospaces/val_0"
    assert plan.backend == "mujoco"
    assert plan.implementation_backend == "molmospaces_subprocess"
    assert plan.agent_engine == "codex-cli"
    assert plan.provider_profile == "codex-env"
    assert plan.intent == "map-build"
    assert plan.dispatch_target == "household-world.map-build"
    assert plan.goal_contract.schema == "roboclaws_goal_contract_v1"
    assert plan.goal_contract.surface == "household-world"
    assert plan.goal_contract.intent == "map-build"
    assert plan.goal_contract.goal_scope == "whole-room"
    assert "goal_contract.json" in plan.required_artifacts
    assert plan.evaluation_id == "map_build_v1"
    assert "goal_contract" in plan.evaluation_hard_gates
    assert "runtime_metric_map" in plan.evaluation_hard_gates
    assert plan.completion_claim_required is True
    assert any(item.startswith("goal_contract_json=") for item in plan.overrides)


def test_surface_launch_exports_goal_contract_to_lower_recipe_environment() -> None:
    plan = resolve_surface_launch(
        (
            "surface=household-world",
            "agent_engine=direct-runner",
            "intent=cleanup",
            "evidence_lane=smoke",
        )
    )
    env = export_env_from_overrides(plan.overrides)

    assert env["ROBOCLAWS_TASK_SURFACE"] == "household-world"
    assert env["ROBOCLAWS_TASK_INTENT"] == "cleanup"
    assert json.loads(env["ROBOCLAWS_GOAL_CONTRACT_JSON"])["intent"] == "cleanup"


def test_surface_launch_plan_keeps_explicit_non_household_report_axis() -> None:
    plan = resolve_surface_launch(
        (
            "surface=ai2thor-world",
            "agent_engine=openclaw-gateway",
            "intent=navigate",
        )
    )

    assert plan.surface == "ai2thor-world"
    assert plan.intent == "navigate"
    assert plan.dispatch_target == "ai2thor-world.navigate"
    assert plan.profile is None
    assert plan.report == "visual"
    assert plan.backend == "ai2thor"
    assert plan.goal_contract.surface == "ai2thor-world"
    assert plan.goal_contract.intent == "navigate"


def test_household_checker_flags_are_generated_from_intent_policy() -> None:
    cleanup_flags = checker_flags_for_household_intent(
        intent_id="cleanup",
        profile="world-oracle-labels",
        min_generated_mess_count="5",
    )
    open_flags = checker_flags_for_household_intent(
        intent_id="open-ended",
        profile="world-oracle-labels",
        min_generated_mess_count="5",
    )
    map_flags = checker_flags_for_household_intent(
        intent_id="map-build",
        profile="world-oracle-labels",
        min_generated_mess_count="5",
    )

    for flags in (cleanup_flags, open_flags, map_flags):
        assert "--require-goal-contract" in flags
        assert "--require-completion-claim" in flags
    assert "--require-clean-agent-run" in cleanup_flags
    assert "--allow-partial-cleanup" not in cleanup_flags
    assert "--require-clean-agent-run" not in open_flags
    assert "--allow-partial-cleanup" in open_flags
    assert "--require-runtime-metric-map" in map_flags
    assert "--allow-partial-cleanup" in map_flags


def test_prompt_mapping_household_cleanup_codex_world_labels_default() -> None:
    route = trace_task_run("household-cleanup", "codex")

    assert route[:6] == [
        "just",
        "molmo::cleanup",
        "codex-live",
        "world-oracle-labels",
        "7",
        "output/household/household-cleanup/codex-report",
    ]


def test_prompt_mapping_household_cleanup_codex_smoke_override() -> None:
    route = trace_task_run("household-cleanup", "codex", "smoke")

    assert route[:6] == [
        "just",
        "molmo::cleanup",
        "codex-live",
        "smoke",
        "7",
        "output/household/household-cleanup/codex-smoke",
    ]


def test_openai_agents_sdk_cleanup_route_stays_private_non_default() -> None:
    molmo_text = MOLMO_JUST.read_text(encoding="utf-8")

    assert "openai-agents-live" in molmo_text
    assert "run_live_openai_agents_cleanup.py" in molmo_text
    assert 'policy="openai_agents_agent"' in molmo_text
    assert "--agent-sdk-perf-profile" in molmo_text
    assert "ROBOCLAWS_OPENAI_AGENTS_PERF_PROFILE" in molmo_text
    assert "--context-soft-limit-tokens" in molmo_text
    assert "openai-agents-live" not in trace_task_run("household-cleanup", "codex")

    plan = resolve_surface_launch(
        (
            "surface=household-world",
            "agent_engine=openai-agents-sdk",
            "intent=cleanup",
            "evidence_lane=smoke",
        )
    )
    assert plan.agent_engine == "openai-agents-sdk"
    assert plan.dispatch_runner == "openai-agents-live"
    assert plan.internal_runner_class == "smoke"


def test_openai_agents_runner_script_uses_runtime_contract_and_checker() -> None:
    runner_text = LIVE_OPENAI_AGENTS_RUNNER.read_text(encoding="utf-8")

    assert "OpenAIAgentsLiveRuntime" in runner_text
    assert "LiveAgentRequest" in runner_text
    assert "household_cleanup_server_argv" in runner_text
    assert "CHECKER_SCRIPT" in runner_text
    assert "--require-clean-agent-run" in runner_text
    assert "run_result.json" in runner_text


def test_prompt_mapping_household_cleanup_direct_world_labels_sanitized() -> None:
    route = trace_task_run("household-cleanup", "direct", "world-public-labels")

    assert route[:6] == [
        "just",
        "molmo::cleanup",
        "direct",
        "world-public-labels",
        "7",
        "output/household/household-cleanup/direct-world-public-labels",
    ]


@pytest.mark.parametrize(
    ("args", "expected"),
    (
        (("molmospace-cleanup", "codex"), "unsupported task 'molmospace-cleanup'"),
        (("molmospaces-cleanup", "codex"), "unsupported task 'molmospaces-cleanup'"),
        (("cleanup-report", "direct"), "unsupported task 'cleanup-report'"),
        (("household-cleanup", "codex-live"), "unsupported agent_engine 'codex-live'"),
        (("household-cleanup", "claude-live"), "unsupported agent_engine 'claude-live'"),
        (
            ("household-cleanup", "codex", "world-oracle-labels-perf"),
            "unsupported household cleanup lane",
        ),
        (("household-cleanup", "codex", "minimal"), "unsupported household cleanup lane"),
        (("household-cleanup", "codex", "visual"), "unsupported household cleanup lane"),
        (
            ("household-cleanup", "codex", "camera-raw-fpv", "cleanup_routine=mcp"),
            "unsupported cleanup_routine",
        ),
        (
            ("household-cleanup", "codex", "world-oracle-labels", "generated_mess_count=5"),
            "generated_mess_count is no longer",
        ),
    ),
)
def test_task_router_rejects_removed_compatibility_aliases(
    args: tuple[str, ...], expected: str
) -> None:
    stderr = assert_task_run_fails(*args)
    if expected.startswith("unsupported task"):
        expected = expected.replace("unsupported task", "unsupported surface")
    assert expected in stderr


def test_surface_router_is_importable_source_of_truth() -> None:
    resolved = resolve_surface_run(
        (
            "surface=household-world",
            "agent_engine=codex-cli",
            "intent=cleanup",
            "evidence_lane=smoke",
            "output_dir=output/custom",
        )
    )

    assert resolved.argv == (
        "just",
        "agent::run",
        "household-world.cleanup",
        "codex-cli",
        "smoke",
        "output_dir=output/custom",
        "scene_source=procthor-10k-val",
        "scene_index=0",
        "backend=molmospaces_subprocess",
        "generated_mess_count=5",
    )
    assert "scenario_setup=relocate-cleanup-related-objects" in resolved.overrides
    assert "relocation_count=5" in resolved.overrides
    assert not any(item.startswith("generated_mess_count=") for item in resolved.overrides)
    assert resolved.world == "molmospaces/val_0"
    assert resolved.backend == "mujoco"
    assert resolved.agent_engine == "codex-cli"
    assert resolved.provider_profile == "codex-env"
    assert resolved.mode == "smoke"

    with pytest.raises(CommandError, match="unsupported surface 'molmospace-cleanup'"):
        resolve_surface_run(("surface=molmospace-cleanup", "agent_engine=codex-cli"))


def test_surface_launch_plan_exposes_domain_metadata_before_dispatch() -> None:
    plan = resolve_surface_launch(
        (
            "surface=household-world",
            "world=agibot-g2/map-12",
            "backend=agibot-gdk",
            "agent_engine=codex-cli",
            "intent=cleanup",
            "evidence_lane=smoke",
        )
    )

    assert plan.argv == (
        "just",
        "agent::run",
        "household-world.cleanup",
        "codex-cli",
        "smoke",
        "backend=agibot_gdk",
        "generated_mess_count=5",
    )
    assert "scenario_setup=relocate-cleanup-related-objects" in plan.overrides
    assert "relocation_count=5" in plan.overrides
    assert not any(item.startswith("generated_mess_count=") for item in plan.overrides)
    assert plan.dispatch_target == "household-world.cleanup"
    assert plan.agent_engine == "codex-cli"
    assert plan.dispatch_runner == "codex"
    assert plan.profile == "smoke"
    assert plan.report is None
    assert plan.world == "agibot-g2/map-12"
    assert plan.backend == "agibot-gdk"
    assert plan.implementation_backend == "agibot_gdk"
    assert plan.prompt_id == "household_cleanup"
    assert plan.checker_id == "cleanup_report"
    assert plan.required_capabilities == (
        "household_world",
        "household_manipulation",
        "household_episode",
    )


def test_surface_launch_plan_keeps_non_household_report_axis() -> None:
    plan = resolve_surface_launch(
        (
            "surface=ai2thor-world",
            "agent_engine=openclaw-gateway",
            "intent=navigate",
            "report=minimal",
        )
    )

    assert plan.argv == (
        "just",
        "agent::run",
        "ai2thor-world.navigate",
        "openclaw-gateway",
        "minimal",
        "scene=FloorPlan201",
        "backend=ai2thor",
    )
    assert plan.profile is None
    assert plan.report == "minimal"
    assert plan.backend == "ai2thor"
    assert plan.prompt_id == "ai2thor_nav"


def test_trace_mode_exposes_resolved_python_launch_plan() -> None:
    route, plan_trace = trace_task_run_with_plan(
        "household-cleanup",
        "codex",
        "camera-grounded-labels",
        "camera_labeler=grounding-dino",
    )

    assert route[:5] == ["just", "molmo::cleanup", "codex-live", "camera-grounded-labels", "7"]
    assert plan_trace[:7] == [
        "launch-plan",
        "surface=household-world",
        "world=molmospaces/val_0",
        "backend=mujoco",
        "intent=cleanup",
        "agent_engine=codex-cli",
        "provider_profile=codex-env",
    ]
    assert "dispatch_runner=codex" in plan_trace
    assert "dispatch_target=household-world.cleanup" in plan_trace
    assert "mode=camera-grounded-labels" in plan_trace
    assert "profile=camera-grounded-labels" in plan_trace
    assert "report=" in plan_trace
    assert "prompt=household_cleanup" in plan_trace
    assert "checker=cleanup_report" in plan_trace
    assert (
        "target=just agent::run household-world.cleanup codex-cli camera-grounded-labels "
        "camera_labeler=grounding-dino scene_source=procthor-10k-val scene_index=0 "
        "backend=molmospaces_subprocess generated_mess_count=5"
    ) in plan_trace


def test_python_launch_plan_accepts_world_labels_sanitized_lane() -> None:
    plan = resolve_surface_launch(
        (
            "surface=household-world",
            "agent_engine=codex-cli",
            "intent=cleanup",
            "evidence_lane=world-public-labels",
        )
    )

    assert plan.mode == "world-public-labels"
    assert plan.profile == "world-public-labels"
    assert plan.supported_profiles == (
        "smoke",
        "world-oracle-labels",
        "world-public-labels",
        "camera-raw-fpv",
        "camera-grounded-labels",
    )
    assert plan.argv == (
        "just",
        "agent::run",
        "household-world.cleanup",
        "codex-cli",
        "world-public-labels",
        "scene_source=procthor-10k-val",
        "scene_index=0",
        "backend=molmospaces_subprocess",
        "generated_mess_count=5",
    )
    assert "scenario_setup=relocate-cleanup-related-objects" in plan.overrides
    assert "relocation_count=5" in plan.overrides
    assert not any(item.startswith("generated_mess_count=") for item in plan.overrides)


def test_prompt_mapping_ai2thor_nav_openclaw_visual_default() -> None:
    route = trace_task_run("ai2thor-nav", "openclaw")

    assert route == [
        "just",
        "openclaw::run",
        "nav",
        "2",
        "10",
        "kimi",
        "output/openclaw/nav",
    ]


def test_openclaw_direct_game_recipe_disables_mcp_tools() -> None:
    text = OPENCLAW_JUST.read_text(encoding="utf-8")

    assert 'if [[ "{{game}}" != "photo" ]]; then' in text
    assert "bootstrap_cmd+=(ROBOCLAWS_MCP_ENABLED=0)" in text


def test_key_value_third_argument_keeps_molmo_profile_default() -> None:
    route = trace_task_run("household-cleanup", "codex", "output_dir=output/custom")

    assert route[:6] == [
        "just",
        "molmo::cleanup",
        "codex-live",
        "world-oracle-labels",
        "7",
        "output/custom",
    ]


def test_semantic_map_build_routes_minimal_map_mode_to_direct_sweep() -> None:
    route = trace_task_run(
        "semantic-map-build",
        "direct",
        "world-oracle-labels",
        "map_mode=minimal",
        "output_dir=output/custom-map",
    )

    assert route[:6] == [
        "just",
        "molmo::cleanup",
        "direct",
        "world-oracle-labels",
        "7",
        "output/custom-map",
    ]
    assert route[15:] == [
        "on",
        "",
        "molmospaces_subprocess",
        "minimal",
        "procthor-10k-val",
        "0",
        "",
        "auto",
        "",
        "semantic-map-build",
    ]


def test_molmo_cleanup_route_passes_selected_map_bundle_override() -> None:
    route = trace_task_run(
        "household-cleanup",
        "codex",
        "world-oracle-labels",
        "map_bundle=molmo-cleanup-default-7",
    )

    assert route[:10] == [
        "just",
        "molmo::cleanup",
        "codex-live",
        "world-oracle-labels",
        "7",
        "output/household/household-cleanup/codex-report",
        "帮我收拾这个房间",
        "5",
        "127.0.0.1",
        "18788",
    ]
    assert route[10] == "molmo-cleanup-default-7"


def test_molmo_cleanup_route_passes_visual_grounding_override() -> None:
    route = trace_agent_run(
        "household-cleanup",
        "mcp-smoke",
        "camera-grounded-labels",
        "camera_labeler=fake-http",
    )

    assert route[:6] == [
        "just",
        "molmo::cleanup",
        "mcp-smoke",
        "camera-grounded-labels",
        "7",
        "output/household/household-cleanup/mcp-smoke-camera-grounded-labels",
    ]
    assert route[13] == "fake-http"


def test_molmo_cleanup_route_passes_isaac_backend_override() -> None:
    route = trace_task_run(
        "household-cleanup",
        "direct",
        "world-oracle-labels",
        "backend=isaaclab_subprocess",
        "seed=7",
        "environment_setup=relocate-cleanup-related-objects",
        "relocation_count=1",
    )

    assert route[:6] == [
        "just",
        "molmo::cleanup",
        "direct",
        "world-oracle-labels",
        "7",
        "output/household/household-cleanup/direct-report",
    ]
    assert route[16:] == [
        "",
        "isaaclab_subprocess",
        "minimal",
        "procthor-10k-val",
        "0",
        "",
        "auto",
        "",
        "household-cleanup",
        "",
        "default_cleanup",
    ]


def test_molmo_cleanup_route_allows_explicit_legacy_rich_map_mode() -> None:
    route = trace_task_run(
        "household-cleanup",
        "direct",
        "world-oracle-labels",
        "map_mode=rich",
    )

    assert route[18] == "rich"


def test_semantic_map_build_routes_agibot_backend_to_physical_pilot_cli() -> None:
    route = trace_task_run(
        "semantic-map-build",
        "direct",
        "camera-grounded-labels",
        "camera_labeler=grounding-dino",
        "backend=agibot_gdk",
        "context_json=tests/fixtures/agibot_map_context.completed.json",
        "waypoint_id=wp_sofa_front",
        "output_dir=output/agibot/map-build",
    )

    assert route[:6] == [
        "cmd",
        ".venv/bin/python",
        "scripts/molmo_cleanup/run_physical_agibot_cleanup_pilot.py",
        "--output-dir",
        "output/agibot/map-build",
        "--context-json",
    ]
    assert route[6] == "tests/fixtures/agibot_map_context.completed.json"
    assert "--waypoint-id" in route
    assert "wp_sofa_front" in route
    assert "agibot-g2-cleanup" not in " ".join(route)


def test_semantic_map_build_codex_routes_agibot_backend_to_live_runner() -> None:
    route = trace_task_run(
        "semantic-map-build",
        "codex",
        "camera-grounded-labels",
        "backend=agibot_gdk",
        "context_json=tests/fixtures/agibot_map_context.completed.json",
        "run_dir=output/agibot/map-build-codex/test-run",
        "policy=codex_agibot_semantic_map_build_pilot",
        "camera_labeler=grounding-dino",
        "visual_grounding_timeout_s=12.5",
    )

    assert route[:3] == [
        "cmd",
        ".venv/bin/python",
        "scripts/molmo_cleanup/run_live_codex_agibot_map_build.py",
    ]
    assert "--repo-root" in route
    assert str(REPO_ROOT) in route
    assert "--run-dir" in route
    assert "output/agibot/map-build-codex/test-run" in route
    assert "--server-arg=--context-json" in route
    assert "--server-arg=tests/fixtures/agibot_map_context.completed.json" in route
    assert "--server-arg=--evidence-lane" in route
    assert "--server-arg=camera-grounded-labels" in route
    assert "--server-arg=--camera-labeler" in route
    assert "--server-arg=grounding-dino" in route
    assert "--server-arg=--visual-grounding-timeout-s" in route
    assert "--server-arg=12.5" in route
    assert "--backend" in route
    assert "agibot_gdk" in route
    assert "--policy" in route
    assert "codex_agibot_semantic_map_build_pilot" in route
    assert str(AGIBOT_MAP_BUILD_CODEX_RUNNER.relative_to(REPO_ROOT)) in route
    assert "molmo::cleanup" not in route


def test_semantic_map_build_codex_routes_molmospaces_backend_to_live_runner() -> None:
    route = trace_task_run(
        "semantic-map-build",
        "codex",
        "world-oracle-labels",
        "backend=molmospaces_subprocess",
    )

    assert route[:7] == [
        "just",
        "molmo::cleanup",
        "codex-live",
        "world-oracle-labels",
        "7",
        "output/household/semantic-map-build/codex-report",
        "帮我建立这个房间的语义地图",
    ]
    assert route[15] == "on"
    assert route[17] == "molmospaces_subprocess"
    assert route[18] == "minimal"
    assert route[-1] == "semantic-map-build"


def test_semantic_map_build_codex_routes_isaac_backend_to_live_runner() -> None:
    route = trace_task_run(
        "semantic-map-build",
        "codex",
        "world-oracle-labels",
        "backend=isaaclab_subprocess",
    )

    assert route[:4] == ["just", "molmo::cleanup", "codex-live", "world-oracle-labels"]
    assert route[15] == "on"
    assert route[17] == "isaaclab_subprocess"
    assert route[-1] == "semantic-map-build"


def test_household_cleanup_routes_agibot_backend_to_default_cleanup_pilot_cli() -> None:
    route = trace_task_run(
        "household-cleanup",
        "direct",
        "world-oracle-labels",
        "backend=agibot_gdk",
    )

    assert route == [
        "cmd",
        ".venv/bin/python",
        "scripts/molmo_cleanup/run_physical_agibot_cleanup_pilot.py",
        "--output-dir",
        "output/household/household-cleanup/direct-report",
    ]


def test_household_cleanup_routes_agibot_backend_override_to_cleanup_pilot_cli() -> None:
    route = trace_task_run(
        "household-cleanup",
        "direct",
        "world-oracle-labels",
        "backend=agibot_gdk",
        "context_json=tests/fixtures/agibot_map_context.completed.json",
        "agibot_map_artifact_dir=vendors/agibot_sdk/artifacts/maps/robot_map_9",
        "waypoint_id=wp_sofa_front",
        "output_dir=output/agibot/cleanup",
    )

    assert route == [
        "cmd",
        ".venv/bin/python",
        "scripts/molmo_cleanup/run_physical_agibot_cleanup_pilot.py",
        "--output-dir",
        "output/agibot/cleanup",
        "--context-json",
        "tests/fixtures/agibot_map_context.completed.json",
        "--waypoint-id",
        "wp_sofa_front",
        "--agibot-map-artifact-dir",
        "vendors/agibot_sdk/artifacts/maps/robot_map_9",
    ]


def test_household_cleanup_routes_agibot_molmospaces_sim_backend_to_rehearsal() -> None:
    route = trace_agent_run(
        "household-cleanup",
        "direct",
        "world-oracle-labels",
        "backend=agibot_molmospaces_sim",
        "context_json=tests/fixtures/agibot_robot_map_9_context.completed.json",
        "agibot_map_artifact_dir=vendors/agibot_sdk/artifacts/maps/robot_map_9",
        "run_dir=output/agibot/molmospaces-sim/test-run",
        "rehearsal_mode=cleanup-actions",
        "generated_mess_count=5",
        "cleanup_object_count=1",
    )

    assert route[:3] == [
        "cmd",
        ".venv/bin/python",
        "scripts/molmo_cleanup/run_molmospaces_agibot_contract_rehearsal.py",
    ]
    assert "--run-dir" in route
    assert "output/agibot/molmospaces-sim/test-run" in route
    assert "--runtime" in route
    assert "fixture" in route
    assert "--flow" in route
    assert "prehardware" in route
    assert "--task-name" in route
    assert "household-cleanup" in route
    assert "--profile" in route
    assert "world-oracle-labels" in route
    assert "--rehearsal-mode" in route
    assert "cleanup-actions" in route
    assert "--context-json" in route
    assert "tests/fixtures/agibot_robot_map_9_context.completed.json" in route
    assert "--agibot-map-artifact-dir" in route
    assert "vendors/agibot_sdk/artifacts/maps/robot_map_9" in route
    assert "--seed" in route
    assert "7" in route
    assert "--cleanup-object-count" in route
    assert "1" in route


def test_semantic_map_build_routes_agibot_molmospaces_sim_to_minimal_map_prehardware() -> None:
    route = trace_agent_run(
        "semantic-map-build",
        "direct",
        "camera-grounded-labels",
        "backend=agibot_molmospaces_sim",
        "run_dir=output/agibot/molmospaces-sim/map-build-test",
        "runtime=molmospaces-subprocess",
        "camera_labeler=grounding-dino",
        "generated_mess_count=0",
    )

    assert route[:3] == [
        "cmd",
        ".venv/bin/python",
        "scripts/molmo_cleanup/run_molmospaces_agibot_contract_rehearsal.py",
    ]
    assert "--flow" in route
    assert "prehardware" in route
    assert "--task-name" in route
    assert "semantic-map-build" in route
    assert "--profile" in route
    assert "camera-grounded-labels" in route
    assert "--camera-labeler" in route
    assert "grounding-dino" in route
    assert "--runtime" in route
    assert "molmospaces-subprocess" in route
    assert "--include-robot" in route
    assert "--record-robot-views" in route


def test_semantic_map_build_agibot_sim_defaults_camera_labeler_for_public_facade() -> None:
    route = trace_agent_run(
        "semantic-map-build",
        "direct",
        "camera-grounded-labels",
        "backend=agibot_molmospaces_sim",
        "runtime=fixture",
        "camera_labeler=sim-projected-labels",
        "generated_mess_count=0",
    )

    assert "--camera-labeler" in route
    assert "sim-projected-labels" in route


def test_agibot_molmospaces_sim_backend_rejects_multi_seed_runs() -> None:
    stderr = assert_agent_run_fails(
        "household-cleanup",
        "direct",
        "world-oracle-labels",
        "backend=agibot_molmospaces_sim",
        "seeds=1 2",
    )

    assert "backend=agibot_molmospaces_sim accepts exactly one seed per run" in stderr


def test_live_cleanup_server_entrypoint_accepts_agibot_shared_mcp_backend() -> None:
    result = subprocess.run(
        [
            os.environ.get("ROBOCLAWS_DEVTOOLS_PYTHON") or sys.executable,
            "-m",
            HOUSEHOLD_AGENT_SERVER_MODULE,
            "household-cleanup",
            "--help",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "agibot_gdk" in result.stdout
    assert "--context-json" in result.stdout
    assert "--real-movement-enabled" in result.stdout


def test_agibot_codex_map_build_route_requires_context_json() -> None:
    stderr = assert_task_run_fails(
        "semantic-map-build",
        "codex",
        "camera-grounded-labels",
        "backend=agibot_gdk",
        "camera_labeler=grounding-dino",
    )

    assert "backend=agibot_gdk semantic-map-build Codex requires context_json" in stderr


def test_molmo_camera_labels_fake_http_uses_contract_not_cleanup_quality_gate() -> None:
    text = MOLMO_JUST.read_text(encoding="utf-8")
    match = re.search(r"camera-grounded-labels\)\n(?P<body>.*?)\n\s+;;", text, re.DOTALL)
    assert match is not None
    body = match.group("body")

    assert "--expect-visual-grounding-pipeline" in body
    assert "--allow-partial-cleanup" in body
    assert "--min-sweep-coverage 1.0" in body


def test_molmo_apple2apple_grid_recipe_strips_key_value_prefixes(tmp_path: Path) -> None:
    output_dir = tmp_path / "apple2apple-grid"
    result = subprocess.run(
        [
            just_bin(),
            "molmo::apple2apple-grid",
            "dry-run",
            f"output_dir={output_dir}",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert (output_dir / "apple2apple_test_grid.json").is_file()
    assert (output_dir / "apple2apple_test_grid.html").is_file()
    assert f"apple-to-apple grid manifest: {output_dir / 'apple2apple_test_grid.json'}" in (
        result.stdout
    )


def test_molmo_cleanup_world_labels_recipe_uses_map_bundle_gate() -> None:
    text = MOLMO_JUST.read_text(encoding="utf-8")

    assert 'map_bundle="auto"' in text
    assert 'map_bundle_dir="assets/maps/molmospaces-procthor-val-0-7"' in text
    assert "--map-bundle-dir" in text
    assert "--require-map-bundle" in text


def test_molmo_world_labels_checker_matches_official_acceptance_gate() -> None:
    text = MOLMO_JUST.read_text(encoding="utf-8")
    match = re.search(r"world-oracle-labels\)\n(?P<body>.*?)\n\s+;;", text, re.DOTALL)
    assert match is not None
    body = match.group("body")

    assert "--require-waypoint-honesty" in body
    assert "--require-real-robot-alignment" in body
    assert "--min-semantic-accepted-count 5" in body
    assert "--min-sweep-coverage 1.0" in body


def test_molmo_semantic_sweep_strips_cleanup_quality_gate() -> None:
    text = MOLMO_JUST.read_text(encoding="utf-8")

    assert 'if [[ "$semantic_sweep_enabled" == "true" && "$driver" == "codex-live" ]]; then' in text
    assert "checker_semantic_args=(--require-runtime-metric-map)" in text
    assert 'elif [[ "$semantic_sweep_enabled" == "true" ]]; then' in text
    assert (
        "--min-semantic-accepted-count|--min-model-declared-observations|--min-model-declared-actions"
        in text
    )
    assert "--require-model-declared-observations)" in text
    assert "filtered_checker_visual_args" in text
    assert 'checker_visual_args=("${filtered_checker_visual_args[@]}")' in text


def test_molmo_world_labels_allows_explicit_robot_view_capture_toggle() -> None:
    route = trace_task_run(
        "household-cleanup",
        "codex",
        "world-oracle-labels",
        "robot_views=off",
    )

    assert route[:12] == [
        "just",
        "molmo::cleanup",
        "codex-live",
        "world-oracle-labels",
        "7",
        "output/household/household-cleanup/codex-report",
        "帮我收拾这个房间",
        "5",
        "127.0.0.1",
        "18788",
        "auto",
        "skill",
    ]
    assert route[12] == "off"


def test_prompt_mapping_molmo_cleanup_camera_profiles() -> None:
    raw_route = trace_task_run("household-cleanup", "direct", "camera-raw-fpv")
    labels_route = trace_task_run(
        "household-cleanup",
        "direct",
        "camera-grounded-labels",
        "camera_labeler=sim-projected-labels",
    )

    assert raw_route[:7] == [
        "just",
        "molmo::cleanup",
        "direct",
        "camera-raw-fpv",
        "7",
        "output/household/household-cleanup/direct-camera-raw-fpv",
        "帮我收拾这个房间",
    ]
    assert labels_route[:7] == [
        "just",
        "molmo::cleanup",
        "direct",
        "camera-grounded-labels",
        "7",
        "output/household/household-cleanup/direct-camera-grounded-labels",
        "帮我收拾这个房间",
    ]
    assert raw_route[11] == "skill"


def test_prompt_mapping_semantic_map_build_direct_enables_sweep() -> None:
    route = trace_task_run("semantic-map-build", "direct", "smoke")

    assert route[:6] == [
        "just",
        "molmo::cleanup",
        "direct",
        "smoke",
        "7",
        "output/household/semantic-map-build/direct-smoke",
    ]
    assert route[6] == "帮我建立这个房间的语义地图"
    assert route[15] == "on"


def test_household_cleanup_route_passes_runtime_map_prior_override() -> None:
    route = trace_task_run(
        "household-cleanup",
        "direct",
        "smoke",
        "runtime_map_prior=output/prior/runtime_metric_map.json",
    )

    assert route[15] == "off"
    assert route[16] == "output/prior/runtime_metric_map.json"


def test_household_cleanup_route_passes_operator_messages_path_override() -> None:
    route = trace_task_run(
        "household-cleanup",
        "codex",
        "world-oracle-labels",
        "operator_messages_path=output/operator-console/runs/run-a/operator_messages.jsonl",
    )

    assert route[-2] == "output/operator-console/runs/run-a/operator_messages.jsonl"
    assert route[-1] == "default_cleanup"


def test_household_cleanup_prompt_override_uses_custom_task_intent() -> None:
    route = trace_task_run(
        "household-cleanup",
        "codex",
        "world-oracle-labels",
        "prompt=我渴了，帮我找些解渴的东西",
    )

    assert "我渴了，帮我找些解渴的东西" in route
    assert route[-1] == "custom"


def test_household_cleanup_prompt_override_does_not_imply_direct_custom_task() -> None:
    route = trace_task_run(
        "household-cleanup",
        "direct",
        "smoke",
        "prompt=我渴了，帮我找些解渴的东西",
    )

    assert "我渴了，帮我找些解渴的东西" in route
    assert route[-1] == "default_cleanup"


def test_household_cleanup_prompt_override_does_not_imply_openclaw_custom_task() -> None:
    route = trace_task_run(
        "household-cleanup",
        "openclaw",
        "world-oracle-labels",
        "prompt=我渴了，帮我找些解渴的东西",
    )

    assert "我渴了，帮我找些解渴的东西" in route
    assert route[-1] == "default_cleanup"


def test_molmo_camera_raw_prompt_requires_exact_waypoint_checklist() -> None:
    prompt = render_kickoff_prompt("camera-raw-fpv")

    assert "exact waypoint checklist" in prompt
    assert "metric_map.inspection_waypoints" in prompt
    assert "mark a waypoint complete only after" in prompt
    assert "cleanup MCP tool entries exactly as exposed by Codex" in prompt
    assert "namespace cleanup" in prompt
    assert "server named cleanup" not in prompt
    assert "compare the checklist before done" in prompt
    assert "never mcp__cleanup__" in prompt
    assert "roboclaws__" in prompt
    assert "visit any missing waypoint_id" in prompt
    assert "trace-preserving camera-raw-fpv skill lane" in prompt
    assert "at most one fresh high-confidence cleanup object" in prompt
    assert "skip tiny slivers" in prompt
    assert "already cleaned or already tried from that same source observation" in prompt
    assert "Use the exact visual class when the image makes it clear" in prompt
    assert "Use broader cleanup categories" in prompt
    assert "only when the exact object class is uncertain" in prompt
    assert "use image_region={type:bbox,value:[x,y,width,height]}" in prompt
    assert "plain verbal_region" in prompt
    assert "Do not retry the same source_observation_id/category/region combination" in prompt
    assert "fresh source_observation_id and a tighter bbox" in prompt
    assert "Omit source_fixture_id in minimal map mode" in prompt
    assert "Never send bbox_normalized" in prompt
    assert 'target_fixture_id=""' in prompt
    assert 'target_fixture_id="None"' in prompt
    assert "target_fixture_id=null" in prompt
    assert "bare x/y/width/height fields" in prompt
    assert "at least 7 grounded cleanup chains have succeeded" in prompt
    assert "place/place_inside" in prompt
    assert "use place_inside for shelf/bookshelf/bookcase/shelving/fridge targets" in prompt


def test_molmo_camera_raw_prompt_scales_to_requested_cleanup_count() -> None:
    prompt = render_kickoff_prompt("camera-raw-fpv", target_cleanup_count=5)

    assert "successful cleanup count is still below 5" in prompt
    assert "Clean at least 5 grounded visual candidates" in prompt
    assert "at least 5 grounded cleanup chains have succeeded" in prompt
    assert "at least seven grounded cleanup chains have succeeded" not in prompt


def test_molmo_camera_raw_live_gate_uses_generated_mess_success_threshold() -> None:
    text = MOLMO_JUST.read_text(encoding="utf-8")
    match = re.search(r"camera-raw-fpv\)\n(?P<body>.*?)\n\s+;;", text, re.DOTALL)
    assert match is not None
    body = match.group("body")

    assert "generated_mess_success_threshold=$(( (generated_mess_count * 7 + 9) / 10 ))" in text
    assert 'raw_fpv_required_cleanup_count="$generated_mess_success_threshold"' in body
    assert '--min-model-declared-observations "$raw_fpv_required_cleanup_count"' in body
    assert '--min-model-declared-actions "$raw_fpv_required_cleanup_count"' in body
    assert '--min-semantic-accepted-count "$raw_fpv_required_cleanup_count"' in body


def test_molmo_live_kickoff_prompt_receives_success_threshold_for_camera_raw() -> None:
    text = MOLMO_JUST.read_text(encoding="utf-8")

    assert 'prompt_cleanup_count="$generated_mess_count"' in text
    assert 'prompt_cleanup_count="$generated_mess_success_threshold"' in text
    assert '--target-cleanup-count "$prompt_cleanup_count"' in text
    assert '--task-intent-mode "$task_intent_mode"' in text


def test_live_codex_camera_raw_default_gate_uses_generated_mess_success_threshold() -> None:
    flags = checker_flags_for_household_intent(
        intent_id="cleanup",
        profile="camera-raw-fpv",
        min_generated_mess_count="5",
    )
    text = LIVE_CODEX_RUNNER.read_text(encoding="utf-8")

    assert flags[flags.index("--min-model-declared-observations") + 1] == "4"
    assert flags[flags.index("--min-model-declared-actions") + 1] == "4"
    assert flags[flags.index("--min-semantic-accepted-count") + 1] == "4"
    assert "checker_flags_for_household_intent" in text
    assert "merge_checker_flags" in text
    assert "def _raw_fpv_required_cleanup_count" not in text
    assert "math.ceil(generated_mess_count * 0.70)" not in text
    assert '"--min-semantic-accepted-count", "7"' not in text


def test_live_runners_custom_task_checker_drops_full_cleanup_gates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    modules = [
        (
            load_script_module(LIVE_CODEX_RUNNER, "run_live_codex_cleanup_custom_gate_test"),
            "LiveCodexCleanupRunner",
            {
                "tmux_session": "custom-gate-test",
                "codex_bin": "codex",
                "codex_model": "",
                "codex_provider_summary": "test",
                "codex_model_arg": [],
            },
        ),
        (
            load_script_module(LIVE_CLAUDE_RUNNER, "run_live_claude_cleanup_custom_gate_test"),
            "LiveClaudeCleanupRunner",
            {
                "claude_bin": "claude",
                "claude_provider_summary": "test",
                "claude_model_arg": [],
                "claude_env": [],
            },
        ),
        (
            load_script_module(
                LIVE_OPENAI_AGENTS_RUNNER,
                "run_live_openai_agents_cleanup_custom_gate_test",
            ),
            "LiveOpenAIAgentsCleanupRunner",
            {
                "provider_profile": "codex-env",
                "model": "gpt-5.5",
                "max_turns": 128,
                "incomplete_turn_continuation_attempts": 0,
                "cache_tools_list": True,
            },
        ),
    ]

    for module, runner_name, extra_args in modules:
        run_dir = tmp_path / runner_name
        run_dir.mkdir()
        (run_dir / "run_result.json").write_text("{}\n", encoding="utf-8")
        captured_commands: list[list[str]] = []

        def fake_run_and_tee(command, *, cwd, stdout_path, stderr_path, env, **_kwargs):
            captured_commands.append(command)
            stdout_path.write_text("checker ok\n", encoding="utf-8")
            return 0

        monkeypatch.setattr(module, "_run_and_tee", fake_run_and_tee)
        args = SimpleNamespace(
            run_dir=run_dir,
            repo_root=REPO_ROOT,
            status_path=run_dir / "live_status.json",
            client_url="http://127.0.0.1:18788/mcp",
            host="127.0.0.1",
            port=18788,
            lock_path=tmp_path / f"{runner_name}.lock",
            server_startup_timeout_s=1.0,
            kickoff_prompt="custom prompt",
            backend="molmospaces_subprocess",
            task_name="household-cleanup",
            task_intent_mode="custom",
            policy="codex_agent" if "Codex" in runner_name else "test_agent",
            task="我渴了，帮我找些解渴的东西",
            min_generated_mess_count="5",
            profile="camera-raw-fpv",
            server_arg=[],
            checker_visual_arg=[
                "--require-robot-views",
                "--require-raw-fpv-observations",
                "--require-model-declared-observations",
                "--min-model-declared-observations",
                "4",
                "--min-model-declared-actions",
                "4",
                "--min-semantic-accepted-count",
                "4",
                "--min-sweep-coverage",
                "1.0",
                "--require-clean-agent-run",
            ],
            **extra_args,
        )

        runner = getattr(module, runner_name)(args)
        runner._check_result()

        assert captured_commands, runner_name
        checker_command = captured_commands[0]
        assert "--allow-partial-cleanup" in checker_command
        assert checker_command.count("--allow-partial-cleanup") == 1
        assert "--require-robot-views" in checker_command
        assert "--require-raw-fpv-observations" in checker_command
        assert "--require-clean-agent-run" not in checker_command
        assert "--require-model-declared-observations" not in checker_command
        assert "--min-model-declared-observations" not in checker_command
        assert "--min-model-declared-actions" not in checker_command
        assert "--min-semantic-accepted-count" not in checker_command
        assert "--min-sweep-coverage" not in checker_command


def test_molmo_world_labels_prompt_requires_nav2_bundle_checklist() -> None:
    prompt = render_kickoff_prompt("world-oracle-labels")

    assert "This run is household-cleanup" in prompt
    assert "User task: clean up this room" in prompt
    assert "exact waypoint checklist" in prompt
    assert "metric_map.inspection_waypoints" in prompt
    assert "selected Nav2 map bundle" in prompt
    assert "not raw occupancy images" in prompt
    assert "mark a waypoint complete only after" in prompt
    assert "place/place_inside" in prompt
    assert "use place_inside for shelf/bookshelf/bookcase/shelving/fridge targets" in prompt
    assert "cleanup MCP tool entries exactly as exposed by Codex" in prompt
    assert "namespace cleanup" in prompt
    assert "server named cleanup" not in prompt
    assert "compare the checklist before done" in prompt
    assert "never mcp__cleanup__" in prompt
    assert "roboclaws__" in prompt
    assert "visit any missing waypoint_id" in prompt
    assert "fresh same-handle source FPV observation with a reviewable bbox" in prompt
    assert "adjust_camera(0, 0) is only a no-op camera command" in prompt


def test_molmo_cleanup_live_prompt_includes_custom_user_task() -> None:
    prompt = render_kickoff_prompt(
        "world-oracle-labels",
        task="我渴了，帮我找些解渴的东西",
        task_intent_mode="custom",
    )

    assert "This run is household-cleanup" in prompt
    assert "custom operator task" in prompt
    assert "authoritative and overrides the default cleanup task" in prompt
    assert "我渴了，帮我找些解渴的东西" in prompt
    assert "The operator task is the only goal" in prompt
    assert "Do not start a room-cleanup routine" in prompt
    assert "visual-scan prerequisite" in prompt
    assert "If the task asks for information, report the answer" in prompt
    assert "Do not treat unrelated pending cleanup candidates" in prompt
    assert "call done so the report is generated" in prompt
    assert "Use the MCP tools as a bounded household robot capability surface" in prompt
    assert "Use the bundled molmo-realworld-cleanup skill instructions" not in prompt
    assert "build an exact waypoint checklist" not in prompt
    assert "sweep every waypoint" not in prompt
    assert "fresh same-handle source FPV observation" not in prompt
    assert "cleaned every public recommended candidate" not in prompt
    assert "call done only after every metric_map.inspection_waypoints" not in prompt


def test_molmo_world_labels_sanitized_prompt_omits_destination_oracle_reliance() -> None:
    prompt = render_kickoff_prompt("world-public-labels")

    assert "perfect structured detections without cleanup destination oracle fields" in prompt
    assert "do not wait for or rely on cleanup_recommended" in prompt
    assert "destination_policy_status is policy_required" in prompt
    assert "destination_policy.preferred_fixture_categories" in prompt
    assert "destination_policy.placement_tool_by_fixture_category" in prompt
    assert "instead of skipping the object" in prompt
    assert "If no matching public anchor or destination_options entry is available yet" in prompt
    assert "continue the waypoint sweep rather than inventing fixture ids" in prompt
    assert "do not re-clean observed handles" in prompt
    assert "Treat public tool responses as authoritative" in prompt
    assert "pending_cleanup_candidates" in prompt
    assert "candidate_fixture_id or destination_options" in prompt
    assert "required_tool" in prompt
    assert "runtime_metric_map.public_semantic_anchors" in prompt
    assert "tool recovery hints" in prompt
    assert "exact waypoint checklist" in prompt
    assert "metric_map.inspection_waypoints" in prompt
    assert "first complete an anchor discovery sweep" not in prompt


def test_molmo_compact_label_prompts_keep_public_done_boundary() -> None:
    world_prompt = render_kickoff_prompt("world-public-labels", prompt_mode="compact")
    camera_prompt = render_kickoff_prompt("camera-grounded-labels", prompt_mode="compact")

    assert "Compact action cadence for world-public-labels" in world_prompt
    assert "observe -> candidate decision" in world_prompt
    assert "pending_cleanup_candidates" in world_prompt
    assert "only MCP done producing run_result.json counts" in world_prompt
    assert "private scoring artifacts" in world_prompt
    assert "Compact action cadence for camera-grounded-labels" in camera_prompt
    assert "declare_visual_candidates with observation_id only" in camera_prompt
    assert "service URLs" in camera_prompt
    assert "only MCP done producing run_result.json counts" in camera_prompt


def test_molmo_raw_fpv_compact_prompt_includes_budget_contract() -> None:
    prompt = render_kickoff_prompt(
        "camera-raw-fpv",
        target_cleanup_count=5,
        prompt_mode="raw_fpv_compact",
        raw_fpv_candidate_budget=3,
        max_observe_per_waypoint=2,
        done_retry_budget=1,
    )

    assert "Compact action cadence for camera-raw-fpv" in prompt
    assert "run budget of 3 raw-FPV candidate attempts" in prompt
    assert "use at most 2 observe response(s)" in prompt
    assert "retry done at most 1 time(s)" in prompt
    assert "Never retry the same source_observation_id/category/region" in prompt
    assert "only MCP done producing run_result.json counts" in prompt


def test_molmo_live_openai_agents_profile_controls_prompt_mode() -> None:
    text = MOLMO_JUST.read_text(encoding="utf-8")

    assert 'prompt_mode="${ROBOCLAWS_OPENAI_AGENTS_PROMPT_MODE:-full}"' in text
    assert "gpt_compact_v1|mimo_compact_v1)" in text
    assert 'prompt_mode="compact"' in text
    assert "raw_fpv_budgeted_v1)" in text
    assert 'prompt_mode="raw_fpv_compact"' in text
    assert '--prompt-mode "$prompt_mode"' in text
    assert '--raw-fpv-candidate-budget "$prompt_raw_fpv_candidate_budget"' in text
    assert '--max-observe-per-waypoint "$prompt_max_observe_per_waypoint"' in text
    assert '--done-retry-budget "$prompt_done_retry_budget"' in text
    assert 'runner_args+=(--max-turns "${ROBOCLAWS_OPENAI_AGENTS_MAX_TURNS}")' in text
    assert '--max-turns "${ROBOCLAWS_OPENAI_AGENTS_MAX_TURNS:-128}"' not in text


def test_semantic_map_build_live_prompt_disables_cleanup_actions() -> None:
    prompt = render_semantic_map_build_prompt(
        "camera-grounded-labels",
        "帮我建立这个房间的语义地图",
    )

    assert "This run is semantic-map-build, not household-cleanup" in prompt
    assert "User task: 帮我建立这个房间的语义地图" in prompt
    assert "Do not pick, place, place_inside" in prompt
    assert "sweep every inspection waypoint" in prompt
    assert "declare_visual_candidates" in prompt
    assert "runtime_metric_map.json" in prompt


def test_live_agent_server_routes_use_cli_modules_not_examples() -> None:
    molmo_text = MOLMO_JUST.read_text(encoding="utf-8")
    codex_runner_text = LIVE_CODEX_RUNNER.read_text(encoding="utf-8")
    agibot_runner_text = AGIBOT_MAP_BUILD_CODEX_RUNNER.read_text(encoding="utf-8")

    assert "roboclaws.cli.agent_server household-cleanup" in molmo_text
    assert "examples/molmo_cleanup/molmo_realworld_cleanup_agent_server.py" not in molmo_text
    assert "examples/molmo_cleanup/molmo_realworld_cleanup_agent_server.py" not in codex_runner_text
    assert "examples/molmo_cleanup/agibot_semantic_map_build_agent_server.py" not in (
        agibot_runner_text
    )
    assert "household_cleanup_server_argv" in codex_runner_text
    assert "semantic_map_build_server_argv" in agibot_runner_text


def test_molmo_cleanup_recipe_passes_goal_contract_to_all_household_runners() -> None:
    molmo_text = MOLMO_JUST.read_text(encoding="utf-8")
    agent_text = AGENT_JUST.read_text(encoding="utf-8")

    assert 'ROBOCLAWS_GOAL_CONTRACT_JSON="$goal_contract_json" \\' in agent_text
    assert 'ROBOCLAWS_GOAL_CONTRACT_PATH="$goal_contract_path" \\' in agent_text
    assert 'run_just molmo::cleanup "${molmo_args[@]}"' in agent_text
    assert 'goal_contract_json="${goal_contract_json:-${ROBOCLAWS_GOAL_CONTRACT_JSON:-}}"' in (
        molmo_text
    )
    assert 'if [[ -z "$goal_contract_json" && -z "$goal_contract_path" ]]; then' in molmo_text
    assert "normalize_goal_contract" in molmo_text
    assert 'goal_contract_args+=(--goal-contract-json "$goal_contract_json")' in molmo_text
    assert '"${goal_contract_args[@]}" \\' in molmo_text
    assert 'prompt_args+=("${goal_contract_args[@]}")' in molmo_text
    assert 'server_args+=("${goal_contract_args[@]}")' in molmo_text


def test_ci_does_not_define_codex_live_proof() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "molmo_official_codex" not in workflow
    assert "molmo-official-codex" not in workflow
    assert "report-molmo-official-codex" not in workflow
    assert "codex-provider-smoke" not in workflow
    assert ".tmp/coding-agent-bin/codex" not in workflow


def test_ci_direct_openclaw_game_smokes_disable_mcp_tools() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert workflow.count('ROBOCLAWS_MCP_ENABLED: "0"') == 3
    for job_name in (
        "Bootstrap OpenClaw Gateway (2 named agents)",
        "Bootstrap OpenClaw Gateway (2 agents — aggressive, defensive)",
        "Bootstrap OpenClaw Gateway (2 agents — cooperative)",
    ):
        job_start = workflow.index(job_name)
        job_chunk = workflow[job_start : job_start + 500]
        assert 'ROBOCLAWS_MCP_ENABLED: "0"' in job_chunk


def test_coding_agent_model_helper_prefers_driver_override_then_shared_fallback() -> None:
    env = clean_code_agent_env()
    env["ROBOCLAWS_HELPER"] = str(CODING_AGENT_ENV)
    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            ROBOCLAWS_CODE_AGENT_MODEL=shared-model
            roboclaws_code_agent_model ROBOCLAWS_CODEX_MODEL
            ROBOCLAWS_CODEX_MODEL=codex-model
            roboclaws_code_agent_model ROBOCLAWS_CODEX_MODEL
            args=()
            roboclaws_code_agent_model_args args ROBOCLAWS_CODEX_MODEL
            printf '%s\n' "${args[@]}"
            """,
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.splitlines() == [
        "shared-model",
        "codex-model",
        "--model",
        "codex-model",
    ]


def test_coding_agent_provider_helper_defaults_codex_to_codex_env_without_args() -> None:
    env = clean_code_agent_env()
    env["ROBOCLAWS_HELPER"] = str(CODING_AGENT_ENV)
    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            claude_model_args=()
            claude_env_args=()
            roboclaws_claude_provider_args claude_model_args claude_env_args
            roboclaws_code_agent_provider ROBOCLAWS_CODEX_PROVIDER
            printf 'claude_model_args=%s\n' "${#claude_model_args[@]}"
            printf 'claude_env_args=%s\n' "${#claude_env_args[@]}"
            """,
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.splitlines() == ["codex-env", "claude_model_args=0", "claude_env_args=0"]


def test_coding_agent_codex_default_ignores_xm_key_and_requires_codex_env() -> None:
    env = clean_code_agent_env()
    env["ROBOCLAWS_HELPER"] = str(CODING_AGENT_ENV)
    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            XM_LLM_API_KEY=fake-xm-key
            roboclaws_code_agent_provider ROBOCLAWS_CODEX_PROVIDER
            args=()
            roboclaws_codex_provider_args args
            """,
        ],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert result.stdout.splitlines() == ["codex-env"]
    assert "codex-env requires CODEX_BASE_URL" in result.stderr


def test_coding_agent_codex_default_prefers_codex_env_even_when_xm_key_is_available() -> None:
    env = clean_code_agent_env()
    env["ROBOCLAWS_HELPER"] = str(CODING_AGENT_ENV)
    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            XM_LLM_API_KEY=fake-xm-key
            XM_LLM_BASE_URL=https://api.llm.mioffice.cn/v1
            CODEX_BASE_URL=https://api-router.evad.mioffice.cn/v1
            CODEX_API_KEY=fake-codex-key
            roboclaws_code_agent_provider ROBOCLAWS_CODEX_PROVIDER
            args=()
            roboclaws_codex_provider_args args
            printf '%s\n' "${args[@]}"
            """,
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.splitlines() == [
        "codex-env",
        "-c",
        'model="gpt-5.5"',
        "-c",
        'model_provider="codex-env"',
        "-c",
        'model_providers.codex-env.name="codex-env"',
        "-c",
        'model_providers.codex-env.base_url="https://api-router.evad.mioffice.cn/v1"',
        "-c",
        'model_providers.codex-env.env_key="CODEX_API_KEY"',
        "-c",
        'model_providers.codex-env.wire_api="responses"',
    ]


def test_coding_agent_codex_explicit_mify_profile_uses_xm_key() -> None:
    env = clean_code_agent_env()
    env["ROBOCLAWS_HELPER"] = str(CODING_AGENT_ENV)
    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            ROBOCLAWS_CODEX_PROVIDER=mify
            XM_LLM_API_KEY=fake-xm-key
            XM_LLM_BASE_URL=https://api.llm.mioffice.cn/v1
            roboclaws_code_agent_provider ROBOCLAWS_CODEX_PROVIDER
            args=()
            roboclaws_codex_provider_args args
            printf '%s\n' "${args[@]}"
            """,
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.splitlines() == [
        "mify",
        "-c",
        'model="xiaomi/mimo-v2.5"',
        "-c",
        'model_provider="mify"',
        "-c",
        'model_providers.mify.name="mify"',
        "-c",
        'model_providers.mify.base_url="https://api.llm.mioffice.cn/v1"',
        "-c",
        'model_providers.mify.env_key="XM_LLM_API_KEY"',
        "-c",
        'model_providers.mify.wire_api="responses"',
        "-c",
        "model_providers.mify.supports_parallel_tool_calls=false",
        "-c",
        'web_search="disabled"',
    ]


def test_coding_agent_codex_can_disable_responses_websockets() -> None:
    env = clean_code_agent_env()
    env["ROBOCLAWS_HELPER"] = str(CODING_AGENT_ENV)
    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            CODEX_BASE_URL=https://codex.example.test/v1
            CODEX_API_KEY=fake-codex-key
            ROBOCLAWS_CODEX_DISABLE_RESPONSES_WEBSOCKETS=1
            args=()
            roboclaws_codex_provider_args args
            printf '%s\n' "${args[@]}"
            """,
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.splitlines() == [
        "-c",
        'model="gpt-5.5"',
        "-c",
        'model_provider="codex-env"',
        "-c",
        'model_providers.codex-env.name="codex-env"',
        "-c",
        'model_providers.codex-env.base_url="https://codex.example.test/v1"',
        "-c",
        'model_providers.codex-env.env_key="CODEX_API_KEY"',
        "-c",
        'model_providers.codex-env.wire_api="responses"',
        "--disable",
        "responses_websockets",
        "--disable",
        "responses_websockets_v2",
    ]


def test_coding_agent_codex_key_contract_builds_scoped_config_args() -> None:
    env = clean_code_agent_env()
    env["ROBOCLAWS_HELPER"] = str(CODING_AGENT_ENV)
    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            CODEX_BASE_URL=https://codex.example.test/v1
            CODEX_API_KEY=fake-codex-key
            args=()
            roboclaws_codex_provider_args args
            printf '%s\n' "${args[@]}"
            """,
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.splitlines() == [
        "-c",
        'model="gpt-5.5"',
        "-c",
        'model_provider="codex-env"',
        "-c",
        'model_providers.codex-env.name="codex-env"',
        "-c",
        'model_providers.codex-env.base_url="https://codex.example.test/v1"',
        "-c",
        'model_providers.codex-env.env_key="CODEX_API_KEY"',
        "-c",
        'model_providers.codex-env.wire_api="responses"',
    ]


def test_coding_agent_codex_official_openai_uses_same_key_contract() -> None:
    env = clean_code_agent_env()
    env["ROBOCLAWS_HELPER"] = str(CODING_AGENT_ENV)
    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            CODEX_BASE_URL=https://api.openai.com/v1
            CODEX_API_KEY=fake-openai-key
            args=()
            roboclaws_codex_provider_args args
            printf '%s\n' "${args[@]}"
            """,
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.splitlines() == [
        "-c",
        'model="gpt-5.5"',
        "-c",
        'model_provider="codex-env"',
        "-c",
        'model_providers.codex-env.name="codex-env"',
        "-c",
        'model_providers.codex-env.base_url="https://api.openai.com/v1"',
        "-c",
        'model_providers.codex-env.env_key="CODEX_API_KEY"',
        "-c",
        'model_providers.codex-env.wire_api="responses"',
    ]


def test_coding_agent_codex_env_profile_requires_base_url() -> None:
    env = clean_code_agent_env()
    env["ROBOCLAWS_HELPER"] = str(CODING_AGENT_ENV)
    env["CODEX_API_KEY"] = "fake-codex-key"
    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            args=()
            roboclaws_codex_provider_args args
            """,
        ],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "codex-env requires CODEX_BASE_URL" in result.stderr
    assert "sk-" not in result.stderr


def test_coding_agent_codex_env_profile_requires_api_key_without_printing_secret() -> None:
    env = clean_code_agent_env()
    env["ROBOCLAWS_HELPER"] = str(CODING_AGENT_ENV)
    env["CODEX_BASE_URL"] = "https://codex.example.test/v1"
    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            args=()
            roboclaws_codex_provider_args args
            """,
        ],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "codex-env requires CODEX_API_KEY" in result.stderr
    assert "fake" not in result.stderr


def test_coding_agent_claude_profile_builds_scoped_env() -> None:
    env = clean_code_agent_env()
    env["ROBOCLAWS_HELPER"] = str(CODING_AGENT_ENV)
    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            MIMO_TP_KEY=fake-mimo-key
            model_args=()
            env_args=()
            roboclaws_claude_provider_args model_args env_args
            printf 'model:%s\n' "${model_args[@]}"
            printf 'env:%s\n' "${env_args[@]}"
            """,
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.splitlines() == [
        "model:--model",
        "model:mimo-v2.5",
        "env:ANTHROPIC_API_KEY=fake-mimo-key",
        "env:ANTHROPIC_BASE_URL=https://token-plan-cn.xiaomimimo.com/anthropic",
        "env:CLAUDE_CODE_SIMPLE=1",
    ]


def test_coding_agent_claude_mify_anthropic_profile_builds_scoped_env() -> None:
    env = clean_code_agent_env()
    env["ROBOCLAWS_HELPER"] = str(CODING_AGENT_ENV)
    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            ROBOCLAWS_CLAUDE_PROVIDER=mify-anthropic
            XM_LLM_API_KEY=fake-xm-key
            XM_LLM_BASE_URL=https://api.llm.mioffice.cn/v1
            model_args=()
            env_args=()
            roboclaws_claude_provider_args model_args env_args
            printf 'model:%s\n' "${model_args[@]}"
            printf 'env:%s\n' "${env_args[@]}"
            """,
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.splitlines() == [
        "model:--model",
        "model:xiaomi/mimo-v2.5",
        "env:ANTHROPIC_API_KEY=fake-xm-key",
        "env:ANTHROPIC_BASE_URL=https://api.llm.mioffice.cn/anthropic",
        "env:CLAUDE_CODE_SIMPLE=1",
    ]


def test_coding_agent_claude_simple_mode_can_be_overridden() -> None:
    env = clean_code_agent_env()
    env["ROBOCLAWS_HELPER"] = str(CODING_AGENT_ENV)
    env["CLAUDE_CODE_SIMPLE"] = "0"
    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            MIMO_TP_KEY=fake-mimo-key
            model_args=()
            env_args=()
            roboclaws_claude_provider_args model_args env_args
            printf 'env:%s\n' "${env_args[@]}"
            """,
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "env:CLAUDE_CODE_SIMPLE=0" in result.stdout.splitlines()


def test_coding_agent_launchers_apply_provider_overrides_per_invocation() -> None:
    code_text = CODE_JUST.read_text(encoding="utf-8")
    molmo_text = MOLMO_JUST.read_text(encoding="utf-8")
    helper_text = CODING_AGENT_ENV.read_text(encoding="utf-8")
    docker_text = CODING_AGENT_DOCKER.read_text(encoding="utf-8")
    runner_text = LIVE_CODEX_RUNNER.read_text(encoding="utf-8")

    assert "source scripts/dev/coding_agent_env.sh" in code_text
    assert "roboclaws_load_dotenv .env" in code_text
    assert "roboclaws_codex_provider_args codex_model_args" in code_text
    assert "roboclaws_claude_provider_args claude_model_args claude_env_args" in code_text
    assert 'docker_codex=("$repo_root/scripts/dev/coding_agent_docker.sh" run codex)' in code_text
    assert '"${docker_codex[@]}" "${codex_model_args[@]}" {{codex_full_permission_args}}' in (
        code_text
    )
    assert (
        'claude_command=("${docker_claude[@]}" "${claude_model_args[@]}" '
        "{{claude_full_permission_args}})" in code_text
    )
    assert 'for entry in "${claude_env_args[@]}"; do' in code_text
    assert 'export "$entry"' in code_text
    assert "export ANTHROPIC_API_KEY" not in code_text

    assert "source scripts/dev/coding_agent_env.sh" in molmo_text
    assert "roboclaws_codex_provider_args codex_model_args" in molmo_text
    assert "roboclaws_claude_provider_args claude_model_args claude_env_args" in molmo_text
    assert "scripts/dev/coding_agent_docker.sh ensure" in molmo_text
    assert 'scripts/dev/coding_agent_docker.sh install-wrappers "$docker_shim_dir"' in molmo_text
    assert '"--codex-model-arg=$arg"' in molmo_text
    assert "--codex-provider-summary" in molmo_text
    assert "XM_LLM_API_KEY" in molmo_text
    assert "XM_LLM_BASE_URL" in molmo_text
    assert "XM_LLM_API_KEY" in docker_text
    assert "XM_LLM_BASE_URL" in docker_text
    assert "*self.args.codex_model_arg" in runner_text
    assert "codex_provider_summary" in runner_text
    assert 'FULL_PERMISSION_ARG = "--dangerously-bypass-approvals-and-sandbox"' in runner_text
    assert '--claude-bin "$claude_bin"' in molmo_text
    assert "ANTHROPIC_BASE_URL" in helper_text
    assert "ANTHROPIC_API_KEY" in helper_text


def test_codex_provider_smoke_requires_repo_local_endpoint() -> None:
    code_text = CODE_JUST.read_text(encoding="utf-8")

    assert re.search(r"^codex-provider-smoke ", code_text, re.MULTILINE)
    assert "codex-env is the default" in code_text
    assert "ROBOCLAWS_CODEX_PROVIDER=mify" in code_text
    assert "--sandbox read-only" in code_text
    assert "--ephemeral" in code_text
    assert "--ignore-user-config" in code_text
    assert "no system-provider fallback was used" in code_text


def test_molmo_codex_live_is_detached_and_probeable() -> None:
    molmo_text = MOLMO_JUST.read_text(encoding="utf-8")
    runner_text = LIVE_CODEX_RUNNER.read_text(encoding="utf-8")

    assert 'tmux new-session -d -s "$session_name"' in molmo_text
    assert (
        'session_suffix="$(basename "$(dirname "$run_root")")-$(basename "$run_root")"'
        in molmo_text
    )
    assert "p${port}-seed-${seed}" in molmo_text
    assert "run_live_codex.sh" in molmo_text
    assert "scripts/molmo_cleanup/run_live_codex_cleanup.py" in molmo_text
    assert "another interactive Codex Molmo cleanup session appears to be active" in molmo_text
    assert "another non-Molmo live cleanup run appears to be active" in molmo_text
    assert "ROBOCLAWS_MOLMO_ALLOW_BATCH_VISUAL_BACKENDS" in molmo_text
    assert "ROBOCLAWS_MOLMO_MAX_VISUAL_BACKENDS \\" in molmo_text
    assert "roboclaws.household.visual_backend_slots acquire" in molmo_text
    assert "visual_backend_slot.json" in molmo_text
    assert "refusing to choose another port" in molmo_text
    assert "--lock-path output/molmo/.live-codex.lock" in molmo_text
    assert "tmux_session.txt" in molmo_text
    assert "live_status.json" in molmo_text
    assert "codex-events.jsonl" in runner_text
    assert "codex-last-message.md" in runner_text
    assert "acquire_visual_backend_slot" in runner_text
    assert "visual_backend_slot" in runner_text
    assert "no MolmoSpaces visual backend slot is available" in runner_text
    assert "is already in use before server start" in runner_text
    assert re.search(r'^status path=""', molmo_text, re.MULTILINE)
    assert "scripts/molmo_cleanup/summarize_live_run.py" in molmo_text


def test_semantic_map_build_codex_live_passes_task_identity_to_server_and_checker() -> None:
    molmo_text = MOLMO_JUST.read_text(encoding="utf-8")
    runner_text = LIVE_CODEX_RUNNER.read_text(encoding="utf-8")
    server_args_match = re.search(r"server_args=\(\n(?P<body>.*?)\n\s+\)", molmo_text, re.DOTALL)

    assert server_args_match is not None
    assert '--task-name "$task_name"' in server_args_match.group("body")
    assert "--server-arg=--task-name" not in molmo_text
    assert '--task-name "$task_name"' in molmo_text
    assert '"--expect-task-name",' in runner_text
    assert 'task_name = getattr(self.args, "task_name", "household-cleanup")' in runner_text
    assert "household_intent_id_for_checker" in runner_text
    assert (
        household_intent_id_for_checker(
            task_name="semantic-map-build",
            task_intent="",
            custom_task=False,
        )
        == "map-build"
    )


def test_lower_level_just_modules_do_not_call_task_or_agent_facades() -> None:
    for path in JUST_DIR.glob("*.just"):
        if path.name in {"task.just", "agent.just"}:
            continue
        text = path.read_text(encoding="utf-8")
        assert "just task::" not in text, path
        assert "just agent::" not in text, path
