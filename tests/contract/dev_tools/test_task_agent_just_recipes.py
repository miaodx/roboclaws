from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

from roboclaws.agents.prompts.household_cleanup import (
    render_kickoff_prompt,
    render_semantic_map_build_prompt,
)
from roboclaws.devtools.commands import CommandError, resolve_surface_run
from roboclaws.launch import resolve_surface_launch
from roboclaws.launch.catalog import LaunchError
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
HOUSEHOLD_LIVE_DRIVER = REPO_ROOT / "roboclaws" / "agents" / "drivers" / "household_live.py"
HOUSEHOLD_AGENT_SERVER_MODULE = "roboclaws.cli.agent_server"
CODE_AGENT_ENV_VARS = (
    "ROBOCLAWS_CODE_AGENT_PROVIDER",
    "ROBOCLAWS_CODEX_PROVIDER",
    "ROBOCLAWS_CLAUDE_PROVIDER",
    "ROBOCLAWS_CODE_AGENT_MODEL",
    "ROBOCLAWS_CODEX_MODEL",
    "ROBOCLAWS_CLAUDE_MODEL",
    "ROBOCLAWS_CODEX_DISABLE_RESPONSES_WEBSOCKETS",
    "ROBOCLAWS_PROVIDER_TIMING_PROXY",
    "ROBOCLAWS_TIMING_PROXY_UPSTREAM_BASE_URL",
    "ROBOCLAWS_TIMING_PROXY_BIND_HOST",
    "ROBOCLAWS_TIMING_PROXY_BIND_PORT",
    "KIMI_API_KEY",
    "MIMO_TP_KEY",
    "OPENAI_API_KEY",
    "CODEX_BASE_URL",
    "CODEX_API_KEY",
    "XM_LLM_BASE_URL",
    "XM_LLM_API_KEY",
    "MM_BASE_URL",
    "MM_API_KEY",
)

_TEST_DIR = Path(__file__).resolve().parent
if str(_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(_TEST_DIR))

from household_surface_trace import household_cleanup_args, household_map_build_args  # noqa: E402


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


def trace_household_cleanup_run(
    agent_engine: str,
    evidence_lane: str = "",
    *overrides: str,
) -> list[str]:
    return trace_surface_run(*household_cleanup_args(agent_engine, evidence_lane, *overrides))


def trace_household_map_build_run(
    agent_engine: str,
    evidence_lane: str = "",
    *overrides: str,
) -> list[str]:
    return trace_surface_run(*household_map_build_args(agent_engine, evidence_lane, *overrides))


def trace_household_cleanup_run_with_plan(
    agent_engine: str,
    evidence_lane: str = "",
    *overrides: str,
) -> tuple[list[str], list[str]]:
    return trace_surface_run_with_plan(
        *household_cleanup_args(agent_engine, evidence_lane, *overrides)
    )


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


def trace_agent_mcp(*args: str) -> list[str]:
    binary = just_bin()
    env = os.environ.copy()
    env["ROBOCLAWS_JUST_TRACE"] = "1"
    env["PATH"] = f"{Path(binary).parent}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        [binary, "agent::mcp", *args],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().split("\t")


def assert_household_cleanup_run_fails(
    agent_engine: str,
    evidence_lane: str = "",
    *overrides: str,
) -> str:
    return assert_surface_run_fails(
        *household_cleanup_args(agent_engine, evidence_lane, *overrides)
    )


def assert_household_map_build_run_fails(
    agent_engine: str,
    evidence_lane: str = "",
    *overrides: str,
) -> str:
    return assert_surface_run_fails(
        *household_map_build_args(agent_engine, evidence_lane, *overrides)
    )


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
        "agent::eval",
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


def test_agent_eval_recommend_writes_eval_harness_manifest(tmp_path: Path) -> None:
    binary = just_bin()
    env = os.environ.copy()
    env["PATH"] = f"{Path(binary).parent}{os.pathsep}{env.get('PATH', '')}"
    output_dir = tmp_path / "eval-harness"
    result = subprocess.run(
        [
            binary,
            "agent::eval",
            "recommend",
            f"output_dir={output_dir}",
            "changed_file=roboclaws/agents/drivers/openai_agents_live.py",
            "budget=focused",
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert f"eval harness manifest: {output_dir / 'eval_harness.json'}" in result.stdout
    manifest = json.loads((output_dir / "eval_harness.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "roboclaws_eval_harness_manifest_v1"
    selected_row_ids = {row["row_id"] for row in manifest["rows"] if row["selected"]}
    assert "openai-agents-sdk-open-task-live-eval" in selected_row_ids
    assert (output_dir / "eval_harness.md").exists()
    assert (output_dir / "eval_harness.html").exists()


def test_agent_harness_rejects_removed_agent_validation_target() -> None:
    binary = just_bin()
    env = os.environ.copy()
    env["ROBOCLAWS_JUST_TRACE"] = "1"
    env["PATH"] = f"{Path(binary).parent}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        [binary, "agent::harness", "agent-validation", "recommend"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "unsupported harness target 'agent-validation'" in result.stderr


def test_old_codex_cleanup_harness_routes_are_unsupported() -> None:
    binary = just_bin()
    env = os.environ.copy()
    env["PATH"] = f"{Path(binary).parent}{os.pathsep}{env.get('PATH', '')}"

    agent_result = subprocess.run(
        [binary, "agent::harness", "codex-cleanup-harness8", "dry-run"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    molmo_result = subprocess.run(
        [binary, "molmo::codex-harness8", "dry-run"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert agent_result.returncode != 0
    assert "unsupported harness target 'codex-cleanup-harness8'" in agent_result.stderr
    assert molmo_result.returncode != 0


def test_justfile_marks_implementation_modules_private() -> None:
    text = JUSTFILE.read_text(encoding="utf-8")

    for module in (
        "openclaw",
        "chat",
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
    assert "just molmo::household-world-impl codex-live world-oracle-labels" in harness_text
    assert '"skill" "$robot_views"' in harness_text


def test_agent_harness_no_longer_advertises_agent_validation() -> None:
    agent_text = AGENT_JUST.read_text(encoding="utf-8")
    harness_text = (JUST_DIR / "harness.just").read_text(encoding="utf-8")
    molmo_text = MOLMO_JUST.read_text(encoding="utf-8")

    assert "agent-validation" not in agent_text
    assert "agent-validation" not in harness_text
    assert re.search(r"^eval \*overrides:", agent_text, re.MULTILINE)
    assert "codex-cleanup-harness8" not in agent_text
    assert "codex-cleanup-harness8" not in harness_text
    assert "codex-harness8" not in molmo_text


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


def test_agent_mcp_accepts_canonical_household_dispatch_targets() -> None:
    cleanup = trace_agent_mcp(
        "up",
        "household-world.cleanup",
        "127.0.0.1",
        "18788",
        "output/debug/household-mcp",
    )
    map_build = trace_agent_mcp(
        "up",
        "household-world.map-build",
        "127.0.0.1",
        "18788",
        "output/debug/map-build-mcp",
    )

    assert cleanup == [
        "just",
        "mcp::up",
        "household-world.cleanup",
        "127.0.0.1",
        "18788",
        "output/debug/household-mcp",
    ]
    assert map_build == [
        "just",
        "mcp::up",
        "household-world.map-build",
        "127.0.0.1",
        "18788",
        "output/debug/map-build-mcp",
    ]


def test_agent_mcp_rejects_legacy_household_dispatch_targets() -> None:
    text = AGENT_JUST.read_text(encoding="utf-8")
    mcp_recipe = re.search(r"^mcp action=.*?(?=^# |\\Z)", text, re.MULTILINE | re.DOTALL)
    assert mcp_recipe is not None
    body = mcp_recipe.group(0)

    assert "household-world.cleanup|cleanup)" in body
    assert "household-world.map-build|map-build)" in body
    assert "household-cleanup)" not in body
    assert "semantic-map-build)" not in body


def test_surface_prompt_mapping_household_cleanup_codex_world_labels_default() -> None:
    route = trace_surface_run(
        "surface=household-world",
        "agent_engine=codex-cli",
        "preset=cleanup",
    )

    assert route[:6] == [
        "just",
        "molmo::household-world-impl",
        "codex-live",
        "world-oracle-labels",
        "7",
        "output/household/household-world/cleanup/codex-report",
    ]


def test_surface_prompt_omitted_intent_with_prompt_infers_open_ended() -> None:
    route, plan_trace = trace_surface_run_with_plan(
        "surface=household-world",
        "agent_engine=codex-cli",
        "prompt=我渴了，帮我找些解渴的东西",
    )

    assert route[:6] == [
        "just",
        "molmo::household-world-impl",
        "codex-live",
        "world-oracle-labels",
        "7",
        "output/household/household-world/open-ended/codex-report",
    ]
    assert "我渴了，帮我找些解渴的东西" in route
    assert route[-2:] == ["household-world", "open-ended"]
    assert plan_trace[:6] == [
        "launch-plan",
        "surface=household-world",
        "world=molmospaces/val_0",
        "backend=mujoco",
        "intent=open-ended",
        "preset=",
    ]
    assert "skill=household-open-task" in plan_trace
    assert "prompt=household_open_ended" in plan_trace
    assert "checker=open_ended_report" in plan_trace
    assert "goal=我渴了，帮我找些解渴的东西" in plan_trace


def test_surface_open_ended_supports_mcp_smoke_for_local_gate() -> None:
    plan = resolve_surface_launch(
        (
            "surface=household-world",
            "agent_engine=direct-runner",
            "run_preset=smoke",
            "evidence_lane=world-oracle-labels",
            "prompt=我渴了，帮我找些解渴的东西",
        )
    )
    env = export_env_from_overrides(plan.overrides)

    assert plan.surface == "household-world"
    assert plan.intent == "open-ended"
    assert plan.preset is None
    assert plan.skill_name == "household-open-task"
    assert plan.agent_engine == "direct-runner"
    assert plan.dispatch_runner == "mcp-smoke"
    assert plan.internal_runner_class == "smoke"
    assert plan.goal_contract.goal_scope == "agent-declared"
    assert env["ROBOCLAWS_TASK_INTENT"] == "open-ended"
    assert "ROBOCLAWS_TASK_PRESET" not in env
    assert env["ROBOCLAWS_TASK_SKILL"] == "household-open-task"
    assert json.loads(env["ROBOCLAWS_GOAL_CONTRACT_JSON"])["intent"] == "open-ended"


def test_surface_launch_rejects_smoke_as_public_evidence_lane() -> None:
    with pytest.raises(LaunchError, match="smoke is not an evidence lane") as exc:
        resolve_surface_launch(
            (
                "surface=household-world",
                "agent_engine=direct-runner",
                "preset=cleanup",
                "evidence_lane=smoke",
            )
        )

    assert exc.value.hint == "use run_preset=smoke with evidence_lane=world-oracle-labels"


def test_surface_launch_rejects_public_profile_alias() -> None:
    with pytest.raises(
        LaunchError,
        match="profile= is no longer a public run::surface argument",
    ) as exc:
        resolve_surface_launch(
            (
                "surface=household-world",
                "agent_engine=codex-cli",
                "preset=cleanup",
                "profile=world-oracle-labels",
            )
        )

    assert "use evidence_lane=" in str(exc.value.hint)


def test_surface_launch_rejects_public_visual_grounding_axis() -> None:
    with pytest.raises(
        LaunchError,
        match="visual_grounding is no longer a public task axis",
    ) as exc:
        resolve_surface_launch(
            (
                "surface=household-world",
                "agent_engine=direct-runner",
                "preset=cleanup",
                "evidence_lane=camera-grounded-labels",
                "camera_labeler=grounding-dino",
                "visual_grounding=grounding-dino",
            )
        )

    assert exc.value.hint == (
        "use camera_labeler=<labeler> with evidence_lane=camera-grounded-labels"
    )


def test_surface_launch_rejects_public_map_mode_axis() -> None:
    with pytest.raises(
        LaunchError,
        match="map_mode= is no longer a public run::surface argument",
    ) as exc:
        resolve_surface_launch(
            (
                "surface=household-world",
                "agent_engine=direct-runner",
                "preset=cleanup",
                "map_mode=minimal",
            )
        )

    assert "Base Navigation Map" in str(exc.value.hint)
    assert "runtime_map_prior=" in str(exc.value.hint)


def test_surface_cleanup_prompt_stays_cleanup_intent_when_explicit() -> None:
    plan = resolve_surface_launch(
        (
            "surface=household-world",
            "agent_engine=codex-cli",
            "preset=cleanup",
            "prompt=只收拾桌面上的杯子",
        )
    )

    assert plan.surface == "household-world"
    assert plan.intent == "cleanup"
    assert plan.preset == "cleanup"
    assert plan.skill_name == "molmo-realworld-cleanup"
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
            "preset=map-build",
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
    assert plan.preset == "map-build"
    assert plan.skill_name == "household-open-task"
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
            "preset=cleanup",
            "run_preset=smoke",
            "evidence_lane=world-oracle-labels",
        )
    )
    env = export_env_from_overrides(plan.overrides)

    assert env["ROBOCLAWS_TASK_SURFACE"] == "household-world"
    assert env["ROBOCLAWS_TASK_INTENT"] == "cleanup"
    assert env["ROBOCLAWS_TASK_PRESET"] == "cleanup"
    assert env["ROBOCLAWS_TASK_SKILL"] == "molmo-realworld-cleanup"
    assert json.loads(env["ROBOCLAWS_GOAL_CONTRACT_JSON"])["intent"] == "cleanup"


def test_surface_launch_rejects_retired_ai2thor_surface() -> None:
    with pytest.raises(LaunchError, match="unsupported surface 'ai2thor-world'") as exc:
        resolve_surface_launch(
            (
                "surface=ai2thor-world",
                "agent_engine=openclaw-gateway",
                "intent=navigate",
            )
        )

    assert exc.value.hint == "expected household-world|planner-proof"


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
    route = trace_household_cleanup_run("codex")

    assert route[:6] == [
        "just",
        "molmo::household-world-impl",
        "codex-live",
        "world-oracle-labels",
        "7",
        "output/household/household-world/cleanup/codex-report",
    ]


def test_prompt_mapping_household_cleanup_codex_smoke_override() -> None:
    route = trace_household_cleanup_run("codex", "smoke")

    assert route[:6] == [
        "just",
        "molmo::household-world-impl",
        "codex-live",
        "smoke",
        "7",
        "output/household/household-world/cleanup/codex-smoke",
    ]


def test_openai_agents_sdk_cleanup_route_stays_private_non_default() -> None:
    molmo_text = MOLMO_JUST.read_text(encoding="utf-8")

    assert "openai-agents-live" in molmo_text
    assert "run_live_openai_agents_cleanup.py" in molmo_text
    assert 'policy="openai_agents_agent"' in molmo_text
    assert "--agent-sdk-perf-profile" in molmo_text
    assert "ROBOCLAWS_OPENAI_AGENTS_PERF_PROFILE" in molmo_text
    assert "--context-soft-limit-tokens" in molmo_text
    assert "openai-agents-live" not in trace_household_cleanup_run("codex")

    plan = resolve_surface_launch(
        (
            "surface=household-world",
            "agent_engine=openai-agents-sdk",
            "preset=cleanup",
            "run_preset=smoke",
            "evidence_lane=world-oracle-labels",
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
    assert "run_result.json" in runner_text


def test_prompt_mapping_household_cleanup_direct_world_labels_sanitized() -> None:
    route = trace_household_cleanup_run("direct", "world-public-labels")

    assert route[:6] == [
        "just",
        "molmo::household-world-impl",
        "direct",
        "world-public-labels",
        "7",
        "output/household/household-world/cleanup/direct-world-public-labels",
    ]


@pytest.mark.parametrize(
    "surface", ("molmospace-cleanup", "molmospaces-cleanup", "cleanup-report", "household-cleanup")
)
def test_surface_router_rejects_removed_compatibility_aliases(surface: str) -> None:
    stderr = assert_surface_run_fails(f"surface={surface}", "agent_engine=codex-cli")

    assert f"unsupported surface '{surface}'" in stderr


@pytest.mark.parametrize(
    ("surface_args", "expected"),
    (
        (
            ("surface=household-world", "agent_engine=codex-live", "preset=cleanup"),
            "unsupported agent_engine 'codex-live'",
        ),
        (
            ("surface=household-world", "agent_engine=claude-live", "preset=cleanup"),
            "unsupported agent_engine 'claude-live'",
        ),
        (
            (
                "surface=household-world",
                "agent_engine=codex-cli",
                "preset=cleanup",
                "evidence_lane=world-oracle-labels-perf",
            ),
            "unsupported household-world evidence_lane",
        ),
        (
            (
                "surface=household-world",
                "agent_engine=codex-cli",
                "preset=cleanup",
                "evidence_lane=minimal",
            ),
            "unsupported household-world evidence_lane",
        ),
        (
            (
                "surface=household-world",
                "agent_engine=codex-cli",
                "preset=cleanup",
                "evidence_lane=visual",
            ),
            "unsupported household-world evidence_lane",
        ),
        (
            (
                "surface=household-world",
                "agent_engine=codex-cli",
                "preset=cleanup",
                "evidence_lane=camera-raw-fpv",
                "cleanup_routine=mcp",
            ),
            "unsupported cleanup_routine",
        ),
        (
            (
                "surface=household-world",
                "agent_engine=codex-cli",
                "preset=cleanup",
                "evidence_lane=world-oracle-labels",
                "generated_mess_count=5",
            ),
            "generated_mess_count is no longer",
        ),
    ),
)
def test_surface_router_rejects_invalid_current_axis_values(
    surface_args: tuple[str, ...], expected: str
) -> None:
    stderr = assert_surface_run_fails(*surface_args)

    assert expected in stderr


def test_surface_router_is_importable_source_of_truth() -> None:
    resolved = resolve_surface_run(
        (
            "surface=household-world",
            "agent_engine=codex-cli",
            "preset=cleanup",
            "run_preset=smoke",
            "evidence_lane=world-oracle-labels",
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
            "preset=cleanup",
            "run_preset=smoke",
            "evidence_lane=world-oracle-labels",
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
    assert plan.preset == "cleanup"
    assert plan.skill_name == "molmo-realworld-cleanup"
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


def test_surface_launch_rejects_retired_vlm_policy_engine() -> None:
    with pytest.raises(LaunchError, match="unsupported agent_engine 'vlm-policy'") as exc:
        resolve_surface_launch(
            (
                "surface=household-world",
                "agent_engine=vlm-policy",
                "preset=cleanup",
                "evidence_lane=world-oracle-labels",
            )
        )

    assert "expected codex-cli|claude-code|openai-agents-sdk|direct-runner" in exc.value.hint
    assert "openclaw-gateway is validation-required" in exc.value.hint
    assert "direct-runner|openclaw-gateway" not in exc.value.hint


def test_public_engine_docs_quarantine_openclaw_gateway() -> None:
    readme = (JUST_DIR / "README.md").read_text(encoding="utf-8")
    engine_section = readme.split("Agent engines:", 1)[1].split("Provider profiles", 1)[0]
    taxonomy = (REPO_ROOT / "docs" / "human" / "agent-task-command-taxonomy.md").read_text(
        encoding="utf-8"
    )
    taxonomy_engine_bullets = [
        line.strip()
        for line in taxonomy.split("Current agent engines:", 1)[1]
        .split("Validation-required maintainer engines", 1)[0]
        .splitlines()
        if line.strip().startswith("- ")
    ]

    assert "openclaw-gateway" not in engine_section
    assert "openclaw-gateway" in readme
    assert "Validation-required maintainer engines" in readme
    assert "- `openclaw-gateway`" not in taxonomy_engine_bullets
    assert "Validation-required maintainer engines" in taxonomy


def test_openclaw_demo_doc_stays_validation_required() -> None:
    demo_doc = (REPO_ROOT / "docs" / "human" / "openclaw" / "demo.md").read_text(encoding="utf-8")

    assert "validation-required maintainer route" in demo_doc
    assert "same public launch catalog" not in demo_doc


def test_human_docs_do_not_surface_legacy_cleanup_commands_as_current() -> None:
    settings = (REPO_ROOT / "docs" / "human" / "molmospaces-settings.md").read_text(
        encoding="utf-8"
    )
    legacy_arch = (
        REPO_ROOT / "docs" / "human" / "molmospaces-cleanup-mode-architecture.md"
    ).read_text(encoding="utf-8")
    assert "just task::run" not in legacy_arch
    assert "profile=world-labels" not in legacy_arch
    assert "profile=world-labels-sanitized" not in legacy_arch
    assert "profile=camera-raw" not in legacy_arch
    assert "profile=camera-labels" not in legacy_arch
    assert "openclaw-smoke-report" not in settings
    assert "just molmo::openclaw-report" not in settings
    assert "OpenClaw report recipes are maintainer-only validation routes" in settings


def test_trace_mode_exposes_resolved_python_launch_plan() -> None:
    route, plan_trace = trace_household_cleanup_run_with_plan(
        "codex",
        "camera-grounded-labels",
        "camera_labeler=grounding-dino",
    )

    assert route[:5] == [
        "just",
        "molmo::household-world-impl",
        "codex-live",
        "camera-grounded-labels",
        "7",
    ]
    assert plan_trace[:7] == [
        "launch-plan",
        "surface=household-world",
        "world=molmospaces/val_0",
        "backend=mujoco",
        "intent=cleanup",
        "preset=cleanup",
        "agent_engine=codex-cli",
    ]
    assert "provider_profile=codex-env" in plan_trace
    assert "skill=molmo-realworld-cleanup" in plan_trace
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
            "preset=cleanup",
            "evidence_lane=world-public-labels",
        )
    )

    assert plan.mode == "world-public-labels"
    assert plan.profile == "world-public-labels"
    assert plan.supported_profiles == (
        "world-oracle-labels",
        "world-public-labels",
        "camera-grounded-labels",
        "camera-raw-fpv",
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


def test_prompt_mapping_rejects_retired_ai2thor_nav_task() -> None:
    stderr = assert_surface_run_fails("surface=ai2thor-nav", "agent_engine=openclaw-gateway")

    assert "unsupported surface 'ai2thor-nav'" in stderr
    assert "expected household-world|planner-proof" in stderr


def test_openclaw_module_no_longer_exposes_direct_game_recipe() -> None:
    text = OPENCLAW_JUST.read_text(encoding="utf-8")

    assert not re.search(r"^run\b", text, re.MULTILINE)
    assert "ROBOCLAWS_MCP_URL is required" in text
    assert "openclaw::run" not in text


@pytest.mark.parametrize(
    "target",
    ("navigator", "regression", "sim", "openclaw", "agent-validation"),
)
def test_agent_harness_rejects_retired_targets(target: str) -> None:
    binary = just_bin()
    env = os.environ.copy()
    env["ROBOCLAWS_JUST_TRACE"] = "1"
    env["PATH"] = f"{Path(binary).parent}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        [binary, "agent::harness", target],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert f"unsupported harness target '{target}'" in result.stderr


def test_key_value_third_argument_keeps_molmo_profile_default() -> None:
    route = trace_household_cleanup_run("codex", "", "output_dir=output/custom")

    assert route[:6] == [
        "just",
        "molmo::household-world-impl",
        "codex-live",
        "world-oracle-labels",
        "7",
        "output/custom",
    ]


def test_semantic_map_build_rejects_public_map_mode_axis() -> None:
    stderr = assert_household_map_build_run_fails(
        "direct",
        "world-oracle-labels",
        "map_mode=minimal",
        "output_dir=output/custom-map",
    )

    assert "map_mode= is no longer a public run::surface argument" in stderr


def test_molmo_cleanup_route_passes_selected_map_bundle_override() -> None:
    route = trace_household_cleanup_run(
        "codex",
        "world-oracle-labels",
        "map_bundle=molmo-cleanup-default-7",
    )

    assert route[:10] == [
        "just",
        "molmo::household-world-impl",
        "codex-live",
        "world-oracle-labels",
        "7",
        "output/household/household-world/cleanup/codex-report",
        "帮我收拾这个房间",
        "5",
        "127.0.0.1",
        "18788",
    ]
    assert route[10] == "molmo-cleanup-default-7"


def test_molmo_cleanup_route_passes_visual_grounding_override() -> None:
    route = trace_agent_run(
        "household-world.cleanup",
        "mcp-smoke",
        "camera-grounded-labels",
        "camera_labeler=fake-http",
    )

    assert route[:6] == [
        "just",
        "molmo::household-world-impl",
        "mcp-smoke",
        "camera-grounded-labels",
        "7",
        "output/household/household-world/cleanup/mcp-smoke-camera-grounded-labels",
    ]
    assert route[13] == "fake-http"


def test_molmo_cleanup_rejects_isaac_backend_override() -> None:
    stderr = assert_agent_run_fails(
        "household-world.cleanup",
        "direct",
        "world-oracle-labels",
        "backend=isaaclab_subprocess",
    )

    assert "backend=isaaclab_subprocess is scoped to world=b1-map12" in stderr
    assert "MolmoSpaces household routes use backend=molmospaces_subprocess" in stderr


def test_household_cleanup_rejects_public_legacy_rich_map_mode() -> None:
    stderr = assert_household_cleanup_run_fails(
        "direct",
        "world-oracle-labels",
        "map_mode=rich",
    )

    assert "map_mode= is no longer a public run::surface argument" in stderr


def test_agent_run_rejects_public_map_mode_override() -> None:
    stderr = assert_agent_run_fails(
        "household-world.cleanup",
        "direct-runner",
        "world-oracle-labels",
        "map_mode=minimal",
    )

    assert "map_mode is no longer a public agent::run override" in stderr


@pytest.mark.parametrize("dispatch_target", ("household-cleanup", "semantic-map-build"))
def test_agent_run_rejects_legacy_household_dispatch_targets(dispatch_target: str) -> None:
    stderr = assert_agent_run_fails(dispatch_target, "direct-runner", "world-oracle-labels")

    assert "unsupported report 'world-oracle-labels'" in stderr


def test_semantic_map_build_routes_agibot_backend_to_physical_pilot_cli() -> None:
    route = trace_household_map_build_run(
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
    route = trace_household_map_build_run(
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
    route = trace_household_map_build_run(
        "codex",
        "world-oracle-labels",
        "backend=molmospaces_subprocess",
    )

    assert route[:7] == [
        "just",
        "molmo::household-world-impl",
        "codex-live",
        "world-oracle-labels",
        "7",
        "output/household/household-world/map-build/codex-report",
        "帮我建立这个房间的语义地图",
    ]
    assert route[15] == "on"
    assert route[17] == "molmospaces_subprocess"
    assert route[18] == "minimal"
    assert route[-1] == "map-build"


def test_semantic_map_build_codex_rejects_molmospaces_isaac_backend_override() -> None:
    stderr = assert_agent_run_fails(
        "household-world.map-build",
        "codex-cli",
        "world-oracle-labels",
        "backend=isaaclab_subprocess",
    )

    assert "backend=isaaclab_subprocess is scoped to world=b1-map12" in stderr


def test_b1_public_launch_routes_isaac_backend_to_current_implementation() -> None:
    route, plan_trace = trace_surface_run_with_plan(
        "surface=household-world",
        "world=b1-map12",
        "backend=isaaclab",
        "agent_engine=codex-cli",
        "prompt=inspect the digital twin",
        "evidence_lane=world-oracle-labels",
    )

    assert route[:6] == [
        "just",
        "molmo::household-world-impl",
        "codex-live",
        "world-oracle-labels",
        "7",
        "output/household/household-world/open-ended/codex-report",
    ]
    assert route[10] == "b1-map12-room-semantics"
    assert route[12] == "on"
    assert route[17] == "isaaclab_subprocess"
    assert route[21] == (
        "data/robot-data-lab/scene-engine/data/"
        "2rd_floor_seperated/storey_1/configuration/scene_base.usd"
    )
    assert route[-2:] == ["household-world", "open-ended"]
    assert "world=b1-map12" in plan_trace
    assert "backend=isaaclab" in plan_trace
    target_trace = next(item for item in plan_trace if item.startswith("target=just agent::run "))
    assert "household-world.open-ended codex-cli world-oracle-labels" in target_trace
    assert "map_bundle=b1-map12-room-semantics" in target_trace
    assert (
        "isaac_scene_usd_path=data/robot-data-lab/scene-engine/data/"
        "2rd_floor_seperated/storey_1/configuration/scene_base.usd"
    ) in target_trace
    assert "world=b1-map12" in target_trace
    assert "backend=isaaclab_subprocess" in target_trace
    assert "generated_mess_count=0" in target_trace


def test_household_cleanup_routes_agibot_backend_to_physical_pilot_cli() -> None:
    route = trace_household_cleanup_run(
        "direct",
        "world-oracle-labels",
        "backend=agibot_gdk",
    )

    assert route == [
        "cmd",
        ".venv/bin/python",
        "scripts/molmo_cleanup/run_physical_agibot_cleanup_pilot.py",
        "--output-dir",
        "output/household/household-world/cleanup/direct-report",
    ]


def test_household_cleanup_routes_agibot_backend_override_to_cleanup_pilot_cli() -> None:
    route = trace_household_cleanup_run(
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
        "household-world.cleanup",
        "direct-runner",
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
    assert "--intent" in route
    assert "cleanup" in route
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
        "household-world.map-build",
        "direct-runner",
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
    assert "--intent" in route
    assert "map-build" in route
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
        "household-world.map-build",
        "direct-runner",
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
        "household-world.cleanup",
        "direct-runner",
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
            "household-world.cleanup",
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
    stderr = assert_household_map_build_run_fails(
        "codex",
        "camera-grounded-labels",
        "backend=agibot_gdk",
        "camera_labeler=grounding-dino",
    )

    assert "backend=agibot_gdk household-world.map-build codex-cli requires context_json" in stderr


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
    route = trace_household_cleanup_run(
        "codex",
        "world-oracle-labels",
        "robot_views=off",
    )

    assert route[:12] == [
        "just",
        "molmo::household-world-impl",
        "codex-live",
        "world-oracle-labels",
        "7",
        "output/household/household-world/cleanup/codex-report",
        "帮我收拾这个房间",
        "5",
        "127.0.0.1",
        "18788",
        "auto",
        "skill",
    ]
    assert route[12] == "off"


def test_prompt_mapping_molmo_cleanup_camera_profiles() -> None:
    raw_route = trace_household_cleanup_run("direct", "camera-raw-fpv")
    labels_route = trace_household_cleanup_run(
        "direct",
        "camera-grounded-labels",
        "camera_labeler=sim-projected-labels",
    )

    assert raw_route[:7] == [
        "just",
        "molmo::household-world-impl",
        "direct",
        "camera-raw-fpv",
        "7",
        "output/household/household-world/cleanup/direct-camera-raw-fpv",
        "帮我收拾这个房间",
    ]
    assert labels_route[:7] == [
        "just",
        "molmo::household-world-impl",
        "direct",
        "camera-grounded-labels",
        "7",
        "output/household/household-world/cleanup/direct-camera-grounded-labels",
        "帮我收拾这个房间",
    ]
    assert raw_route[11] == "skill"


def test_prompt_mapping_semantic_map_build_direct_enables_sweep() -> None:
    route = trace_household_map_build_run("direct", "smoke")

    assert route[:6] == [
        "just",
        "molmo::household-world-impl",
        "direct",
        "smoke",
        "7",
        "output/household/household-world/map-build/direct-smoke",
    ]
    assert route[6] == "帮我建立这个房间的语义地图"
    assert route[15] == "on"


def test_household_cleanup_route_passes_runtime_map_prior_override() -> None:
    route = trace_household_cleanup_run(
        "direct",
        "smoke",
        "runtime_map_prior=output/prior/runtime_metric_map.json",
    )

    assert route[15] == "off"
    assert route[16] == "output/prior/runtime_metric_map.json"


def test_household_cleanup_route_passes_operator_messages_path_override() -> None:
    route = trace_household_cleanup_run(
        "codex",
        "world-oracle-labels",
        "operator_messages_path=output/operator-console/runs/run-a/operator_messages.jsonl",
    )

    assert route[-1] == "output/operator-console/runs/run-a/operator_messages.jsonl"


def test_household_open_ended_prompt_uses_first_class_intent_not_custom_mode() -> None:
    route = trace_household_cleanup_run(
        "codex",
        "world-oracle-labels",
        "prompt=我渴了，帮我找些解渴的东西",
        "task_intent=open-ended",
    )

    assert "我渴了，帮我找些解渴的东西" in route
    assert route[-2:] == ["household-world", "open-ended"]


def test_household_cleanup_prompt_override_does_not_imply_direct_open_ended_intent() -> None:
    route = trace_household_cleanup_run(
        "direct",
        "smoke",
        "prompt=我渴了，帮我找些解渴的东西",
    )

    assert "我渴了，帮我找些解渴的东西" in route
    assert route[-2:] == ["household-world", "cleanup"]


def test_household_cleanup_prompt_override_does_not_imply_openclaw_open_ended_intent() -> None:
    route = trace_household_cleanup_run(
        "openclaw",
        "world-oracle-labels",
        "prompt=我渴了，帮我找些解渴的东西",
    )

    assert "我渴了，帮我找些解渴的东西" in route
    assert route[-2:] == ["household-world", "cleanup"]


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
    assert "Omit source_fixture_id with Base Navigation Map context" in prompt
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
    assert "--task-intent-mode" not in text


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


def test_live_runners_open_ended_checker_drops_full_cleanup_gates(
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
            run_id="household-world.cleanup",
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

        monkeypatch.setenv("ROBOCLAWS_TASK_INTENT", "open-ended")
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

    assert "This run is surface=household-world intent=cleanup" in prompt
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


def test_molmo_cleanup_live_prompt_includes_open_ended_user_task() -> None:
    prompt = render_kickoff_prompt(
        "world-oracle-labels",
        task="我渴了，帮我找些解渴的东西",
        intent="open-ended",
    )

    assert "This run is surface=household-world with no task preset" in prompt
    assert "custom operator task" not in prompt
    assert "The following operator task is authoritative" in prompt
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


def test_molmo_cleanup_live_prompt_uses_cleanup_intent_without_open_ended_intent() -> None:
    prompt = render_kickoff_prompt(
        "world-oracle-labels",
        task="我渴了，帮我找些解渴的东西",
    )

    assert "This run is surface=household-world intent=cleanup" in prompt
    assert "This run is surface=household-world with no task preset" not in prompt
    assert "The operator task is the only goal" not in prompt
    assert "Use the bundled molmo-realworld-cleanup skill instructions" in prompt


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


def test_molmo_compact_camera_prompt_can_prefer_composite_observe_tool() -> None:
    prompt = render_kickoff_prompt(
        "camera-grounded-labels",
        prompt_mode="compact",
        camera_grounded_composite_tools=True,
    )

    assert "observe_camera_grounded_candidates instead of a separate observe" in prompt
    assert "response declaration as the camera-labeler candidate output" in prompt
    assert "do not call declare_visual_candidates again for the same" in prompt
    assert "only MCP done producing run_result.json counts" in prompt


def test_molmo_just_openai_agents_composite_env_forwards_prompt_flag() -> None:
    text = MOLMO_JUST.read_text(encoding="utf-8")

    assert "ROBOCLAWS_OPENAI_AGENTS_CAMERA_GROUNDED_COMPOSITE_TOOLS" in text
    assert "prompt_args+=(--camera-grounded-composite-tools)" in text
    assert (
        '[[ "$driver" == "openai-agents-live" && "$profile" == "camera-grounded-labels" ]]' in text
    )


def test_molmo_just_openai_agents_forwards_camera_grounded_history_compaction() -> None:
    text = MOLMO_JUST.read_text(encoding="utf-8")

    assert "ROBOCLAWS_OPENAI_AGENTS_CAMERA_GROUNDED_HISTORY_COMPACTION" in text
    assert "--camera-grounded-history-compaction" in text
    assert "--no-camera-grounded-history-compaction" in text
    assert "ROBOCLAWS_OPENAI_AGENTS_CAMERA_GROUNDED_HISTORY_RETAIN" in text
    assert "--camera-grounded-history-retain" in text


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

    assert "This run is surface=household-world intent=map-build" in prompt
    assert "This is not a cleanup run" in prompt
    assert "User task: 帮我建立这个房间的语义地图" in prompt
    assert "Do not pick, place, place_inside" in prompt
    assert "sweep every inspection waypoint" in prompt
    assert "declare_visual_candidates" in prompt
    assert "adjust_camera" in prompt
    assert "observe again" in prompt
    assert "required_next_tool" in prompt
    assert "required_tool" in prompt
    assert "generated target-inspection candidate" in prompt
    assert "public inspection waypoint" in prompt
    assert "runtime_metric_map.json" in prompt


def test_live_agent_server_routes_use_cli_modules_not_examples() -> None:
    molmo_text = MOLMO_JUST.read_text(encoding="utf-8")
    codex_runner_text = LIVE_CODEX_RUNNER.read_text(encoding="utf-8")
    agibot_runner_text = AGIBOT_MAP_BUILD_CODEX_RUNNER.read_text(encoding="utf-8")

    assert "roboclaws.cli.agent_server household-world.cleanup" in molmo_text
    assert "roboclaws.cli.agent_server household-cleanup" not in molmo_text
    assert "examples/molmo_cleanup/molmo_realworld_cleanup_agent_server.py" not in molmo_text
    assert "examples/molmo_cleanup/molmo_realworld_cleanup_agent_server.py" not in codex_runner_text
    assert "examples/molmo_cleanup/agibot_semantic_map_build_agent_server.py" not in (
        agibot_runner_text
    )
    assert "household_cleanup_server_argv" in codex_runner_text
    assert "semantic_map_build_server_argv" in agibot_runner_text


def test_agent_server_cli_accepts_canonical_household_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from roboclaws.cli import agent_server

    calls: list[tuple[str, list[str]]] = []

    def fake_main(name: str):
        def _main(args: list[str]) -> int:
            calls.append((name, list(args)))
            return 0

        return _main

    monkeypatch.setitem(
        sys.modules,
        "roboclaws.cli.household_agent_server",
        types.SimpleNamespace(main=fake_main("cleanup")),
    )
    monkeypatch.setitem(
        sys.modules,
        "roboclaws.cli.agibot_map_build_agent_server",
        types.SimpleNamespace(main=fake_main("map-build")),
    )

    assert agent_server.main(["household-world.cleanup", "--host", "127.0.0.1"]) == 0
    assert agent_server.main(["household-world.map-build", "--policy", "codex_agent"]) == 0
    assert calls == [
        ("cleanup", ["--host", "127.0.0.1"]),
        ("map-build", ["--policy", "codex_agent"]),
    ]


def test_agent_server_cli_rejects_legacy_household_targets(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from roboclaws.cli import agent_server

    def fail_if_called(_args: list[str]) -> int:
        raise AssertionError("legacy server target should not import a concrete server")

    monkeypatch.setitem(
        sys.modules,
        "roboclaws.cli.household_agent_server",
        types.SimpleNamespace(main=fail_if_called),
    )
    monkeypatch.setitem(
        sys.modules,
        "roboclaws.cli.agibot_map_build_agent_server",
        types.SimpleNamespace(main=fail_if_called),
    )

    assert agent_server.main(["household-cleanup"]) == 2
    assert agent_server.main(["semantic-map-build"]) == 2

    stderr = capsys.readouterr().err
    assert "unsupported server 'household-cleanup'" in stderr
    assert "unsupported server 'semantic-map-build'" in stderr
    assert "household-world.cleanup|household-world.map-build" in stderr


def test_agent_server_cli_errors_use_canonical_targets(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from roboclaws.cli import agent_server

    assert agent_server.main(["semantic-map"]) == 2

    stderr = capsys.readouterr().err
    assert "household-world.cleanup|household-world.map-build" in stderr
    assert "household-cleanup" not in stderr
    assert "semantic-map-build" not in stderr


def test_molmo_cleanup_recipe_passes_goal_contract_to_all_household_runners() -> None:
    molmo_text = MOLMO_JUST.read_text(encoding="utf-8")
    agent_text = AGENT_JUST.read_text(encoding="utf-8")

    assert 'ROBOCLAWS_GOAL_CONTRACT_JSON="$goal_contract_json" \\' in agent_text
    assert 'ROBOCLAWS_GOAL_CONTRACT_PATH="$goal_contract_path" \\' in agent_text
    assert 'ROBOCLAWS_TASK_INTENT="$resolved_task_intent" \\' in agent_text
    assert 'run_just molmo::household-world-impl "${molmo_args[@]}"' in agent_text
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


def test_ci_no_longer_defines_retired_openclaw_game_smokes() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert 'ROBOCLAWS_MCP_ENABLED: "0"' not in workflow
    for retired_name in (
        "territory-openclaw-smoke",
        "coverage-openclaw-smoke",
        "openclaw-smoke",
        "photo-task-smoke",
        "real-model-smoke",
    ):
        assert retired_name not in workflow


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


def test_coding_agent_codex_explicit_minimax_profile_uses_mm_key() -> None:
    env = clean_code_agent_env()
    env["ROBOCLAWS_HELPER"] = str(CODING_AGENT_ENV)
    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            ROBOCLAWS_CODEX_PROVIDER=minimax
            MM_API_KEY=fake-mm-key
            MM_BASE_URL=https://api.minimaxi.com/v1
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
        "minimax",
        "-c",
        'model="MiniMax-M3"',
        "-c",
        'model_provider="minimax"',
        "-c",
        'model_providers.minimax.name="minimax"',
        "-c",
        'model_providers.minimax.base_url="https://api.minimaxi.com/v1"',
        "-c",
        'model_providers.minimax.env_key="MM_API_KEY"',
        "-c",
        'model_providers.minimax.wire_api="responses"',
    ]


def test_coding_agent_env_shell_profile_facts_match_python_registry() -> None:
    env = clean_code_agent_env()
    env["ROBOCLAWS_HELPER"] = str(CODING_AGENT_ENV)
    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            roboclaws_code_agent_profile_default_model minimax
            roboclaws_code_agent_profile_wire_api mimo-openai-chat
            roboclaws_code_agent_profile_key_env codex-env
            """,
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    python_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "roboclaws.agents.provider_registry",
            "default-model",
            "minimax",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.splitlines() == [
        python_result.stdout.strip(),
        "chat-completions",
        "CODEX_API_KEY",
    ]


def test_coding_agent_minimax_model_can_select_highspeed_variant() -> None:
    env = clean_code_agent_env()
    env["ROBOCLAWS_HELPER"] = str(CODING_AGENT_ENV)
    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            ROBOCLAWS_CODEX_PROVIDER=minimax
            ROBOCLAWS_CODEX_MODEL=MiniMax-M2.7-highspeed
            MM_API_KEY=fake-mm-key
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

    assert 'model="MiniMax-M2.7-highspeed"' in result.stdout.splitlines()
    assert 'model_providers.minimax.wire_api="responses"' in result.stdout.splitlines()


def test_coding_agent_profile_summary_supports_openai_agents_chat_profiles() -> None:
    env = clean_code_agent_env()
    env["ROBOCLAWS_HELPER"] = str(CODING_AGENT_ENV)
    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            ROBOCLAWS_CODEX_PROVIDER=mimo-openai-chat
            MIMO_TP_KEY=fake-mimo-key
            roboclaws_code_agent_profile_summary ROBOCLAWS_CODEX_PROVIDER ROBOCLAWS_CODEX_MODEL
            ROBOCLAWS_CODEX_PROVIDER=kimi-openai-chat
            KIMI_API_KEY=fake-kimi-key
            roboclaws_code_agent_profile_summary ROBOCLAWS_CODEX_PROVIDER ROBOCLAWS_CODEX_MODEL
            """,
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.splitlines() == [
        (
            "mimo-openai-chat model=mimo-v2.5 "
            "base_url=https://token-plan-cn.xiaomimimo.com/v1 "
            "key_env=MIMO_TP_KEY protocol=chat-completions"
        ),
        (
            "kimi-openai-chat model=kimi-k2.7-code "
            "base_url=https://api.kimi.com/coding/v1 "
            "key_env=KIMI_API_KEY protocol=chat-completions"
        ),
    ]


def test_coding_agent_codex_provider_args_reject_openai_agents_chat_profile() -> None:
    env = clean_code_agent_env()
    env["ROBOCLAWS_HELPER"] = str(CODING_AGENT_ENV)
    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            ROBOCLAWS_CODEX_PROVIDER=mimo-openai-chat
            MIMO_TP_KEY=fake-mimo-key
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
    assert "unsupported Codex provider 'mimo-openai-chat'" in result.stderr


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


def test_coding_agent_codex_provider_timing_proxy_disables_responses_websockets() -> None:
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
            ROBOCLAWS_PROVIDER_TIMING_PROXY=1
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

    assert "--disable" in result.stdout.splitlines()
    assert "responses_websockets" in result.stdout.splitlines()
    assert 'model_providers.codex-env.wire_api="responses"' in result.stdout.splitlines()


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
    agent_text = AGENT_JUST.read_text(encoding="utf-8")
    helper_text = CODING_AGENT_ENV.read_text(encoding="utf-8")
    docker_text = CODING_AGENT_DOCKER.read_text(encoding="utf-8")
    runner_text = LIVE_CODEX_RUNNER.read_text(encoding="utf-8")

    assert "source scripts/dev/coding_agent_env.sh" in code_text
    assert "roboclaws_load_dotenv .env" in code_text
    assert "roboclaws_codex_provider_args codex_model_args" in code_text
    assert "roboclaws_claude_provider_args claude_model_args claude_env_args" not in code_text
    assert not re.search(r"^codex\s", code_text, re.MULTILINE)
    assert not re.search(r"^cc\s", code_text, re.MULTILINE)

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
    assert "MM_API_KEY" in molmo_text
    assert "MM_BASE_URL" in molmo_text
    assert "MM_API_KEY" in agent_text
    assert "MM_BASE_URL" in agent_text
    assert "MM_API_KEY" in docker_text
    assert "MM_BASE_URL" in docker_text
    assert "ROBOCLAWS_PROVIDER_TIMING_PROXY" in docker_text
    assert "ROBOCLAWS_TIMING_PROXY_UPSTREAM_BASE_URL" in docker_text
    assert "ROBOCLAWS_PROVIDER_TIMING_PROXY" in molmo_text
    assert "ROBOCLAWS_TIMING_PROXY_BIND_PORT" in molmo_text
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
    assert "minimax with MM_API_KEY" in code_text
    assert "--sandbox read-only" in code_text
    assert "--ephemeral" in code_text
    assert "--ignore-user-config" in code_text
    assert "no system-provider fallback was used" in code_text


def test_molmo_codex_live_is_detached_and_probeable() -> None:
    molmo_text = MOLMO_JUST.read_text(encoding="utf-8")
    runner_text = LIVE_CODEX_RUNNER.read_text(encoding="utf-8")
    household_live_text = HOUSEHOLD_LIVE_DRIVER.read_text(encoding="utf-8")

    assert 'tmux new-session -d -s "$session_name"' in molmo_text
    assert (
        'session_suffix="$(basename "$(dirname "$run_root")")-$(basename "$run_root")"'
        in molmo_text
    )
    assert "p${port}-seed-${seed}" in molmo_text
    assert "run_live_codex.sh" in molmo_text
    assert "scripts/molmo_cleanup/run_live_codex_cleanup.py" in molmo_text
    assert "another interactive Codex Molmo cleanup session appears to be active" in molmo_text
    assert (
        'if [[ "$backend" == "molmospaces_subprocess" && "$interactive_visual_cap" == "1" ]]'
        in molmo_text
    )
    assert "another non-Molmo live cleanup run appears to be active" not in molmo_text
    assert "active MCP servers:" not in molmo_text
    assert "ROBOCLAWS_MOLMO_ALLOW_BATCH_VISUAL_BACKENDS" in molmo_text
    assert "ROBOCLAWS_MOLMO_MAX_VISUAL_BACKENDS \\" in molmo_text
    assert "roboclaws.household.visual_backend_slots acquire" in molmo_text
    assert "visual_backend_slot.json" in molmo_text
    assert "refusing to choose another port" in molmo_text
    assert "tmux_session.txt" in molmo_text
    assert "live_status.json" in molmo_text
    assert all(item in runner_text for item in ("codex-events.jsonl", "codex-last-message.md"))
    assert "acquire_household_live_run_lease" in runner_text
    assert "acquire_visual_backend_slot" in household_live_text
    assert "no MolmoSpaces visual backend slot is available" in household_live_text
    assert "is already in use before server start" in runner_text
    assert re.search(r'^status path=""', molmo_text, re.MULTILINE)
    assert "scripts/molmo_cleanup/summarize_live_run.py" in molmo_text
    assert 'live_lock_backend="${backend//[^A-Za-z0-9_.-]/-}"' in molmo_text
    assert '--lock-path "$codex_lock_path"' in molmo_text
    assert "output/molmo/.live-codex.lock" not in molmo_text


def test_semantic_map_build_codex_live_passes_task_identity_to_server_and_checker() -> None:
    molmo_text = MOLMO_JUST.read_text(encoding="utf-8")
    runner_text = LIVE_CODEX_RUNNER.read_text(encoding="utf-8")
    server_args_match = re.search(r"server_args=\(\n(?P<body>.*?)\n\s+\)", molmo_text, re.DOTALL)

    assert server_args_match is not None
    assert '--intent "$task_intent"' in server_args_match.group("body")
    assert "--server-arg=--task-name" not in molmo_text
    assert '--task-name "$task_name"' not in molmo_text
    assert '"--expect-task-name",' in runner_text
    assert "household_task_name_from_args" in runner_text
    assert "household_intent_id_for_checker" in runner_text
    assert 'SEMANTIC_MAP_BUILD_SERVER_TASK = "household-world.map-build"' in (
        HOUSEHOLD_LIVE_DRIVER.read_text(encoding="utf-8")
    )
    assert (
        household_intent_id_for_checker(task_intent="map-build", open_ended_task=False)
        == "map-build"
    )


def test_lower_level_just_modules_do_not_call_task_or_agent_facades() -> None:
    for path in JUST_DIR.glob("*.just"):
        if path.name in {"task.just", "agent.just"}:
            continue
        text = path.read_text(encoding="utf-8")
        assert "just task::" not in text, path
        assert "just agent::" not in text, path
