from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from roboclaws.devtools.commands import CommandError, resolve_task_run

REPO_ROOT = Path(__file__).resolve().parents[3]
JUSTFILE = REPO_ROOT / "justfile"
JUST_DIR = REPO_ROOT / "just"
TASK_JUST = JUST_DIR / "task.just"
AGENT_JUST = JUST_DIR / "agent.just"
CODE_JUST = JUST_DIR / "code.just"
MOLMO_JUST = JUST_DIR / "molmo.just"
CODING_AGENT_ENV = REPO_ROOT / "scripts" / "dev" / "coding_agent_env.sh"
CODING_AGENT_DOCKER = REPO_ROOT / "scripts" / "dev" / "coding_agent_docker.sh"
LIVE_CODEX_RUNNER = REPO_ROOT / "scripts" / "molmo_cleanup" / "run_live_codex_cleanup.py"
AGIBOT_MAP_BUILD_CODEX_RUNNER = (
    REPO_ROOT / "scripts" / "molmo_cleanup" / "run_live_codex_agibot_map_build.py"
)
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
    binary = just_bin()
    env = os.environ.copy()
    env["ROBOCLAWS_JUST_TRACE"] = "1"
    env["PATH"] = f"{Path(binary).parent}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        [binary, "task::run", *args],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().split("\t")


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


def assert_task_run_fails(*args: str) -> str:
    binary = just_bin()
    env = os.environ.copy()
    env["ROBOCLAWS_JUST_TRACE"] = "1"
    env["PATH"] = f"{Path(binary).parent}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        [binary, "task::run", *args],
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


def test_public_just_summary_is_small_facade() -> None:
    summary = just_summary()

    assert summary == {
        "task::run",
        "agent::run",
        "agent::verify",
        "agent::harness",
        "agent::mcp",
        "agent::gateway",
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
    assert re.search(r"^mod task\s+'just/task\.just'$", text, re.MULTILINE)


def test_agent_module_exposes_compact_dispatchers() -> None:
    text = AGENT_JUST.read_text(encoding="utf-8")

    expected_headers = (
        r"^run task driver mode=\"\" \*overrides:",
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


def test_agent_harness_allows_molmo_codex_perf_target() -> None:
    agent_text = AGENT_JUST.read_text(encoding="utf-8")
    harness_text = (JUST_DIR / "harness.just").read_text(encoding="utf-8")

    assert "molmo-cleanup-codex-perf" in agent_text
    assert re.search(r"^molmo-cleanup-codex-perf \*overrides:", harness_text, re.MULTILINE)
    assert 'just molmo::cleanup "codex-live" "world-labels"' in harness_text
    assert '"skill" "$robot_views"' in harness_text


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


def test_task_module_exposes_only_run_publicly() -> None:
    text = TASK_JUST.read_text(encoding="utf-8")

    assert re.search(r"^run task driver mode=\"\" \*overrides:", text, re.MULTILINE)
    assert "-m roboclaws.devtools.commands task run" in text
    assert "normalize_task()" not in text
    assert "normalize_driver()" not in text

    removed_wrappers = (
        "navigate",
        "photo-chairs",
        "territory",
        "coverage",
        "control-ui",
        "cleanup-quick-check",
        "cleanup-report",
        "cleanup-camera-raw",
        "planner-proof",
        "check",
    )
    for wrapper in removed_wrappers:
        assert not re.search(rf"^\[private\]\n{re.escape(wrapper)}\b", text, re.MULTILINE)

    summary = just_summary()
    assert "task::run" in summary
    assert "task::navigate" not in summary
    assert "task::cleanup-report" not in summary


def test_prompt_mapping_household_cleanup_codex_world_labels_default() -> None:
    route = trace_task_run("household-cleanup", "codex")

    assert route[:6] == [
        "just",
        "molmo::cleanup",
        "codex-live",
        "world-labels",
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


@pytest.mark.parametrize(
    ("args", "expected"),
    (
        (("molmospace-cleanup", "codex"), "unsupported task 'molmospace-cleanup'"),
        (("molmospaces-cleanup", "codex"), "unsupported task 'molmospaces-cleanup'"),
        (("cleanup-report", "direct"), "unsupported task 'cleanup-report'"),
        (("household-cleanup", "codex-live"), "unsupported driver 'codex-live'"),
        (("household-cleanup", "claude-live"), "unsupported driver 'claude-live'"),
        (
            ("household-cleanup", "codex", "world-labels-perf"),
            "unsupported household cleanup lane",
        ),
        (("household-cleanup", "codex", "minimal"), "unsupported household cleanup lane"),
        (("household-cleanup", "codex", "visual"), "unsupported household cleanup lane"),
        (
            ("household-cleanup", "codex", "camera-raw", "cleanup_routine=mcp"),
            "unsupported cleanup_routine",
        ),
    ),
)
def test_task_router_rejects_removed_compatibility_aliases(
    args: tuple[str, ...], expected: str
) -> None:
    assert expected in assert_task_run_fails(*args)


def test_task_router_is_importable_source_of_truth() -> None:
    resolved = resolve_task_run(
        ("household-cleanup", "codex", "profile=smoke", "output_dir=output/custom")
    )

    assert resolved.argv == (
        "just",
        "agent::run",
        "household-cleanup",
        "codex",
        "smoke",
        "output_dir=output/custom",
    )
    assert resolved.task == "household-cleanup"
    assert resolved.driver == "codex"
    assert resolved.mode == "smoke"

    legacy = resolve_task_run(("molmo-cleanup", "direct", "smoke"))
    assert legacy.task == "household-cleanup"
    assert legacy.argv[:5] == ("just", "agent::run", "household-cleanup", "direct", "smoke")

    with pytest.raises(CommandError, match="unsupported task 'molmospace-cleanup'"):
        resolve_task_run(("molmospace-cleanup", "codex"))


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


def test_key_value_third_argument_keeps_molmo_profile_default() -> None:
    route = trace_task_run("household-cleanup", "codex", "output_dir=output/custom")

    assert route[:6] == [
        "just",
        "molmo::cleanup",
        "codex-live",
        "world-labels",
        "7",
        "output/custom",
    ]


def test_semantic_map_build_routes_minimal_map_mode_to_direct_sweep() -> None:
    route = trace_task_run(
        "semantic-map-build",
        "direct",
        "world-labels",
        "map_mode=minimal",
        "output_dir=output/custom-map",
    )

    assert route[:6] == [
        "just",
        "molmo::cleanup",
        "direct",
        "world-labels",
        "7",
        "output/custom-map",
    ]
    assert route[-4:] == ["on", "", "auto", "minimal"]


def test_molmo_cleanup_route_passes_selected_map_bundle_override() -> None:
    route = trace_task_run(
        "household-cleanup",
        "codex",
        "world-labels",
        "map_bundle=molmo-cleanup-default-7",
    )

    assert route[:10] == [
        "just",
        "molmo::cleanup",
        "codex-live",
        "world-labels",
        "7",
        "output/household/household-cleanup/codex-report",
        "帮我收拾这个房间",
        "10",
        "127.0.0.1",
        "18788",
    ]
    assert route[10] == "molmo-cleanup-default-7"


def test_molmo_cleanup_route_passes_visual_grounding_override() -> None:
    route = trace_task_run(
        "household-cleanup",
        "mcp-smoke",
        "camera-labels",
        "visual_grounding=fake-http",
    )

    assert route[:6] == [
        "just",
        "molmo::cleanup",
        "mcp-smoke",
        "camera-labels",
        "7",
        "output/household/household-cleanup/mcp-smoke-camera-labels",
    ]
    assert route[13] == "fake-http"


def test_molmo_cleanup_route_passes_isaac_backend_override() -> None:
    route = trace_task_run(
        "household-cleanup",
        "direct",
        "world-labels",
        "backend=isaaclab_subprocess",
        "seed=7",
        "generated_mess_count=1",
    )

    assert route[:6] == [
        "just",
        "molmo::cleanup",
        "direct",
        "world-labels",
        "7",
        "output/household/household-cleanup/direct-report",
    ]
    assert route[-2:] == ["isaaclab_subprocess", "rich"]


def test_semantic_map_build_routes_agibot_backend_to_physical_pilot_cli() -> None:
    route = trace_task_run(
        "semantic-map-build",
        "direct",
        "camera-labels",
        "backend=agibot_gdk",
        "context_json=tests/fixtures/agibot_map_context.completed.json",
        "waypoint_id=wp_sofa_front",
        "output_dir=output/agibot/map-build",
    )

    assert route[:6] == [
        "cmd",
        ".venv/bin/python",
        "scripts/molmo_cleanup/run_physical_agibot_cleanup_pilot.py",
        "--context-json",
        "tests/fixtures/agibot_map_context.completed.json",
        "--output-dir",
    ]
    assert route[6] == "output/agibot/map-build"
    assert "--waypoint-id" in route
    assert "wp_sofa_front" in route
    assert "agibot-g2-cleanup" not in " ".join(route)


def test_semantic_map_build_codex_routes_agibot_backend_to_live_runner() -> None:
    route = trace_task_run(
        "semantic-map-build",
        "codex",
        "camera-labels",
        "backend=agibot_gdk",
        "context_json=tests/fixtures/agibot_map_context.completed.json",
        "run_dir=output/agibot/map-build-codex/test-run",
        "policy=codex_agibot_semantic_map_build_pilot",
        "visual_grounding=grounding-dino",
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
    assert "--server-arg=camera-labels" in route
    assert "--server-arg=--visual-grounding" in route
    assert "--server-arg=grounding-dino" in route
    assert "--server-arg=--visual-grounding-timeout-s" in route
    assert "--server-arg=12.5" in route
    assert "--backend" in route
    assert "agibot_gdk" in route
    assert "--policy" in route
    assert "codex_agibot_semantic_map_build_pilot" in route
    assert str(AGIBOT_MAP_BUILD_CODEX_RUNNER.relative_to(REPO_ROOT)) in route
    assert "molmo::cleanup" not in route


def test_semantic_map_build_codex_requires_agibot_backend() -> None:
    stderr = assert_task_run_fails("semantic-map-build", "codex", "camera-labels")

    assert "semantic-map-build codex currently requires backend=agibot_gdk" in stderr


def test_household_cleanup_routes_agibot_backend_to_blocked_cleanup_pilot_cli() -> None:
    route = trace_task_run(
        "household-cleanup",
        "direct",
        "world-labels",
        "backend=agibot_gdk",
        "context_json=tests/fixtures/agibot_map_context.completed.json",
    )

    assert route[:5] == [
        "cmd",
        ".venv/bin/python",
        "scripts/molmo_cleanup/run_physical_agibot_cleanup_pilot.py",
        "--context-json",
        "tests/fixtures/agibot_map_context.completed.json",
    ]


def test_household_cleanup_routes_agibot_molmospaces_sim_backend_to_rehearsal() -> None:
    route = trace_task_run(
        "household-cleanup",
        "direct",
        "world-labels",
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


def test_agibot_molmospaces_sim_backend_rejects_multi_seed_runs() -> None:
    stderr = assert_task_run_fails(
        "household-cleanup",
        "direct",
        "world-labels",
        "backend=agibot_molmospaces_sim",
        "seeds=1 2",
    )

    assert "backend=agibot_molmospaces_sim accepts exactly one seed per run" in stderr


def test_live_cleanup_server_entrypoint_accepts_agibot_shared_mcp_backend() -> None:
    result = subprocess.run(
        [
            ".venv/bin/python",
            "examples/molmo_cleanup/molmo_realworld_cleanup_agent_server.py",
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


def test_agibot_backend_route_requires_context_json() -> None:
    stderr = assert_task_run_fails(
        "semantic-map-build",
        "direct",
        "camera-labels",
        "backend=agibot_gdk",
    )

    assert "backend=agibot_gdk requires context_json" in stderr


def test_molmo_camera_labels_fake_http_uses_contract_not_cleanup_quality_gate() -> None:
    text = MOLMO_JUST.read_text(encoding="utf-8")
    match = re.search(r"camera-labels\)\n(?P<body>.*?)\n\s+;;", text, re.DOTALL)
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
    match = re.search(r"world-labels\)\n(?P<body>.*?)\n\s+;;", text, re.DOTALL)
    assert match is not None
    body = match.group("body")

    assert "--require-waypoint-honesty" in body
    assert "--require-real-robot-alignment" in body
    assert "--min-semantic-accepted-count 5" in body
    assert "--min-sweep-coverage 1.0" in body


def test_molmo_semantic_sweep_strips_cleanup_quality_gate() -> None:
    text = MOLMO_JUST.read_text(encoding="utf-8")

    assert 'if [[ "$semantic_sweep_enabled" == "true" ]]; then' in text
    assert "--min-semantic-accepted-count|--min-model-declared-actions" in text
    assert "filtered_checker_visual_args" in text
    assert 'checker_visual_args=("${filtered_checker_visual_args[@]}")' in text


def test_molmo_world_labels_allows_explicit_robot_view_capture_toggle() -> None:
    route = trace_task_run(
        "household-cleanup",
        "codex",
        "world-labels",
        "robot_views=off",
    )

    assert route[:12] == [
        "just",
        "molmo::cleanup",
        "codex-live",
        "world-labels",
        "7",
        "output/household/household-cleanup/codex-report",
        "帮我收拾这个房间",
        "10",
        "127.0.0.1",
        "18788",
        "auto",
        "skill",
    ]
    assert route[12] == "off"


def test_prompt_mapping_molmo_cleanup_camera_profiles() -> None:
    raw_route = trace_task_run("household-cleanup", "direct", "camera-raw")
    labels_route = trace_task_run("household-cleanup", "direct", "camera-labels")

    assert raw_route[:7] == [
        "just",
        "molmo::cleanup",
        "direct",
        "camera-raw",
        "7",
        "output/household/household-cleanup/direct-camera-raw",
        "帮我收拾这个房间",
    ]
    assert labels_route[:7] == [
        "just",
        "molmo::cleanup",
        "direct",
        "camera-labels",
        "7",
        "output/household/household-cleanup/direct-camera-labels",
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


def test_molmo_camera_raw_prompt_requires_exact_waypoint_checklist() -> None:
    text = MOLMO_JUST.read_text(encoding="utf-8")
    matches = [
        match.group("body")
        for match in re.finditer(r"camera-raw\)\n(?P<body>.*?)\n\s+;;", text, re.DOTALL)
    ]
    prompt = next((body for body in matches if "kickoff_prompt" in body), "")
    assert prompt

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
    assert "trace-preserving RAW_FPV skill lane" in prompt
    assert "Prefer image_region={type:verbal_region,value:front of desk}" in prompt
    assert "image_region={type:bbox,value:[x,y,width,height]} only when" in prompt
    assert "Never send bbox_normalized" in prompt
    assert 'target_fixture_id=\\"\\"' in prompt
    assert 'target_fixture_id=\\"None\\"' in prompt
    assert "target_fixture_id=null" in prompt
    assert "bare x/y/width/height fields" in prompt
    assert "at least seven grounded cleanup chains have succeeded" in prompt
    assert "place/place_inside" in prompt
    assert "use place_inside for shelf/bookshelf/bookcase/shelving/fridge targets" in prompt


def test_molmo_world_labels_prompt_requires_nav2_bundle_checklist() -> None:
    text = MOLMO_JUST.read_text(encoding="utf-8")
    match = re.search(r'\*\)\n\s+kickoff_prompt="([^"]+)"', text)
    assert match is not None
    prompt = match.group(1)

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


def test_ci_does_not_define_codex_live_proof() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "molmo_official_codex" not in workflow
    assert "molmo-official-codex" not in workflow
    assert "report-molmo-official-codex" not in workflow
    assert "codex-provider-smoke" not in workflow
    assert ".tmp/coding-agent-bin/codex" not in workflow


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


def test_coding_agent_provider_helper_defaults_to_system_without_args() -> None:
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

    assert result.stdout.splitlines() == [
        "system",
        "claude_model_args=0",
        "claude_env_args=0",
    ]


def test_coding_agent_codex_mify_profile_is_default_when_xm_key_is_available() -> None:
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
            args=()
            roboclaws_codex_provider_args args
            roboclaws_code_agent_profile_summary ROBOCLAWS_CODEX_PROVIDER ROBOCLAWS_CODEX_MODEL
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
        (
            "mify model=xiaomi/mimo-v2-omni "
            "base_url=https://api.llm.mioffice.cn/v1 key_env=XM_LLM_API_KEY "
            "protocol=responses"
        ),
        "-c",
        'model="xiaomi/mimo-v2-omni"',
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


def test_coding_agent_codex_mify_profile_prefers_internal_platform_over_api_router() -> None:
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
        "mify",
        "-c",
        'model="xiaomi/mimo-v2-omni"',
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


def test_coding_agent_codex_mify_base_url_alone_does_not_shadow_codex_env() -> None:
    env = clean_code_agent_env()
    env["ROBOCLAWS_HELPER"] = str(CODING_AGENT_ENV)
    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            XM_LLM_BASE_URL=https://api.llm.mioffice.cn/v1
            CODEX_BASE_URL=https://codex.example.test/v1
            CODEX_API_KEY=fake-codex-key
            roboclaws_code_agent_provider ROBOCLAWS_CODEX_PROVIDER
            """,
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "codex-env"


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
        "model:mimo-v2.5-pro",
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
    assert "no repo-local Codex endpoint configured" in code_text
    assert "--sandbox read-only" in code_text
    assert "--ephemeral" in code_text
    assert "--ignore-user-config" in code_text
    assert "no system-provider fallback was used" in code_text


def test_molmo_codex_live_is_detached_and_probeable() -> None:
    molmo_text = MOLMO_JUST.read_text(encoding="utf-8")
    runner_text = LIVE_CODEX_RUNNER.read_text(encoding="utf-8")

    assert 'tmux new-session -d -s "$session_name"' in molmo_text
    assert "run_live_codex.sh" in molmo_text
    assert "scripts/molmo_cleanup/run_live_codex_cleanup.py" in molmo_text
    assert "another live Molmo cleanup run appears to be active" in molmo_text
    assert "refusing to choose another port" in molmo_text
    assert "--lock-path output/molmo/.live-codex.lock" in molmo_text
    assert "tmux_session.txt" in molmo_text
    assert "live_status.json" in molmo_text
    assert "codex-events.jsonl" in runner_text
    assert "codex-last-message.md" in runner_text
    assert "fcntl.flock" in runner_text
    assert "another live Molmo cleanup run holds" in runner_text
    assert "is already in use before server start" in runner_text
    assert re.search(r'^status path=""', molmo_text, re.MULTILINE)
    assert "scripts/molmo_cleanup/summarize_live_run.py" in molmo_text


def test_lower_level_just_modules_do_not_call_task_or_agent_facades() -> None:
    for path in JUST_DIR.glob("*.just"):
        if path.name in {"task.just", "agent.just"}:
            continue
        text = path.read_text(encoding="utf-8")
        assert "just task::" not in text, path
        assert "just agent::" not in text, path
