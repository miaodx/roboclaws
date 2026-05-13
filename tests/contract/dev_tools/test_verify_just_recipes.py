from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
JUSTFILE = REPO_ROOT / "justfile"
JUST_DIR = REPO_ROOT / "just"
VERIFY_JUST = JUST_DIR / "verify.just"
HARNESS_JUST = JUST_DIR / "harness.just"
MOLMO_JUST = JUST_DIR / "molmo.just"
LIVE_CODEX_RUNNER = REPO_ROOT / "scripts" / "molmo_cleanup" / "run_live_codex_cleanup.py"


def test_verify_module_is_registered() -> None:
    text = JUSTFILE.read_text(encoding="utf-8")

    assert re.search(r"^mod verify\s+'just/verify\.just'$", text, re.MULTILINE)


def test_molmo_module_is_registered() -> None:
    text = JUSTFILE.read_text(encoding="utf-8")

    assert re.search(r"^mod molmo\s+'just/molmo\.just'$", text, re.MULTILINE)


def test_verify_layer_keeps_static_checks_out_of_harness_namespace() -> None:
    verify_text = VERIFY_JUST.read_text(encoding="utf-8")
    harness_text = HARNESS_JUST.read_text(encoding="utf-8")

    assert "ruff check ." in verify_text
    assert "ruff format --check ." in verify_text
    assert "git diff --check" in verify_text
    assert "ruff check ." not in harness_text
    assert "ruff format --check ." not in harness_text
    assert "git diff --check" not in harness_text


def test_verify_delegates_scenario_gates_to_harness() -> None:
    text = VERIFY_JUST.read_text(encoding="utf-8")

    expected_calls = (
        "just harness::regression",
        "just harness::sim",
        "just harness::openclaw",
        "just harness::navigator",
        "just harness::molmo-cleanup",
        "just harness::molmo-prompt-cleanup",
        "just harness::molmo-real-cleanup",
        "just harness::molmo-robot-visual",
        "just harness::molmo-agent-bridge",
        "just harness::molmo-agent-bridge-visual",
        "just harness::molmo-realworld-cleanup",
        "just harness::molmo-realworld-agent-mcp",
        "just harness::molmo-realworld-agent-dogfood-kit",
        "just harness::molmo-realworld-openclaw-dogfood-kit",
        "just harness::molmo-realworld-openclaw-visual-dogfood-kit",
        "just harness::molmo-realworld-raw-fpv",
        "just harness::molmo-planner-proof-bundle-runner",
        "just harness::molmo-planner-proof-bundle-execute-rerun",
        "just harness::molmo-planner-manipulation-probe",
    )
    for call in expected_calls:
        assert call in text


def test_harness_exposes_named_execution_rigs() -> None:
    text = HARNESS_JUST.read_text(encoding="utf-8")

    expected_headers = (
        r"^navigator task cap=\"900\":$",
        r"^regression mode=\"mock\"",
        r"^sim scenes=\"FloorPlan201\"",
        r"^openclaw scenes=\"FloorPlan201\"",
        r"^molmo-cleanup seed=\"7\"",
        r"^molmo-prompt-cleanup seed=\"7\"",
        r"^molmo-real-cleanup seed=\"7\"",
        r"^molmo-robot-visual seed=\"7\"",
        r"^molmo-agent-bridge seed=\"7\"",
        r"^molmo-agent-bridge-visual seed=\"7\"",
        r"^molmo-realworld-cleanup seeds=\"1 2 3\"",
        r"^molmo-realworld-agent-mcp seeds=\"1\"",
        r"^molmo-realworld-agent-dogfood-kit seed=\"7\"",
        r"^molmo-realworld-openclaw-dogfood-kit seed=\"7\"",
        r"^molmo-realworld-openclaw-visual-dogfood-kit seed=\"7\"",
        r"^molmo-realworld-raw-fpv seed=\"7\"",
        (
            r"^molmo-planner-proof-bundle-runner "
            r"output_dir=\"output/molmo-planner-proof-bundle-runner-harness\""
        ),
        (
            r"^molmo-planner-proof-bundle-execute-rerun "
            r"output_dir=\"output/molmo-planner-proof-bundle-execute-rerun\""
        ),
        (
            r"^molmo-planner-manipulation-probe "
            r"output_dir=\"output/molmo-planner-manipulation-probe-harness\""
        ),
    )
    for header in expected_headers:
        assert re.search(header, text, re.MULTILINE), f"missing recipe header: {header}"


def test_molmo_operator_surface_exposes_axis_runner_and_aliases() -> None:
    text = MOLMO_JUST.read_text(encoding="utf-8")

    expected_headers = (
        r"^cleanup driver=\"mcp-smoke\" profile=\"smoke\"",
        r"^quick-check driver=\"mcp-smoke\" profile=\"smoke\"",
        r"^review-report seeds=\"1 2 3\"",
        r"^mcp-smoke-report seed=\"7\"",
        r"^openclaw-smoke-report seed=\"7\"",
        r"^camera-raw-report seed=\"7\"",
        r"^codex-report seed=\"7\"",
        r"^claude-report seed=\"7\"",
        r"^openclaw-report seed=\"7\"",
    )
    for header in expected_headers:
        assert re.search(header, text, re.MULTILINE), f"missing recipe header: {header}"


def test_molmo_operator_aliases_map_to_truthful_axes() -> None:
    text = MOLMO_JUST.read_text(encoding="utf-8")

    expected_calls = (
        'just molmo::cleanup "{{driver}}" "{{profile}}"',
        'just molmo::cleanup "direct" "world-labels"',
        'just molmo::cleanup "mcp-smoke" "world-labels"',
        'just molmo::cleanup "openclaw-smoke" "world-labels"',
        'just molmo::cleanup "direct" "camera-raw"',
        'just molmo::cleanup "codex-live" "{{profile}}"',
        'just molmo::cleanup "claude-live" "{{profile}}"',
        'just molmo::cleanup "openclaw-live" "{{profile}}"',
    )
    for call in expected_calls:
        assert call in text

    assert "agent-report" not in text
    assert "openclaw_agent" in text
    assert "realworld_contract_smoke_agent" in text


def test_molmo_axis_runner_distinguishes_smoke_from_live_agents() -> None:
    text = MOLMO_JUST.read_text(encoding="utf-8")
    runner_text = LIVE_CODEX_RUNNER.read_text(encoding="utf-8")

    for expected in (
        'driver="${driver#driver=}"',
        'profile="${profile#profile=}"',
        "unsupported profile",
        "--cleanup-profile",
        "--expect-profile",
        "mcp-smoke/openclaw-smoke for deterministic substitutes",
        "command -v codex",
        "command -v claude",
        "claude mcp add --transport http roboclaws",
        'SKILLS_DIR="$PWD/skills/molmo-realworld-cleanup"',
        "just chat::run",
        'bash scripts/dev/network_status.sh --assert-off-work "OpenClaw Molmo cleanup live report"',
        'roboclaws_assert_claude_code_network_allowed "Claude Code Molmo cleanup live report"',
    ):
        assert expected in text

    assert '"mcp", "add", "roboclaws"' in runner_text


def test_molmo_visual_reports_require_robot_timeline_and_real_robot_checks() -> None:
    text = MOLMO_JUST.read_text(encoding="utf-8")

    for expected in (
        "--include-robot",
        "--robot-name rby1m",
        "--record-robot-views",
        "--require-robot-views",
        "--require-waypoint-honesty",
        "--require-real-robot-alignment",
        'perception_mode="raw_fpv_only"',
        'perception_mode="camera_model_policy"',
        "--require-raw-fpv-observations",
        "--require-camera-model-policy",
    ):
        assert expected in text


def test_molmo_harness_output_roots_keep_timestamped_runs() -> None:
    text = HARNESS_JUST.read_text(encoding="utf-8")

    assert 'timestamp_cmd := "TZ=Asia/Shanghai date +%m%d_%H%M"' in text
    recipe_names = (
        "molmo-cleanup",
        "molmo-prompt-cleanup",
        "molmo-real-cleanup",
        "molmo-robot-visual",
        "molmo-agent-bridge",
        "molmo-agent-bridge-visual",
        "molmo-realworld-cleanup",
        "molmo-realworld-agent-mcp",
        "molmo-realworld-agent-dogfood-kit",
        "molmo-realworld-openclaw-dogfood-kit",
        "molmo-realworld-openclaw-visual-dogfood-kit",
        "molmo-realworld-raw-fpv",
        "molmo-planner-proof-bundle-runner",
        "molmo-planner-proof-bundle-execute-rerun",
        "molmo-planner-manipulation-probe",
    )
    for recipe_name in recipe_names:
        recipe = re.search(
            rf"^{recipe_name}[\s\S]*?(?=^# |\Z)",
            text,
            re.MULTILINE,
        )
        assert recipe is not None, recipe_name
        body = recipe.group(0)
        assert re.search(r'stamp="\$\(\{\{\s*timestamp_cmd\s*\}\}\)"', body), recipe_name
        assert 'rm -rf "{{output_dir}}"' not in body, recipe_name


def test_openclaw_visual_kit_uses_real_visual_backend_and_checker() -> None:
    text = HARNESS_JUST.read_text(encoding="utf-8")

    recipe = re.search(
        r"^molmo-realworld-openclaw-visual-dogfood-kit[\s\S]*?(?=^# List task files)",
        text,
        re.MULTILINE,
    )
    assert recipe is not None
    body = recipe.group(0)
    for expected in (
        "--backend molmospaces_subprocess",
        "--policy openclaw_agent",
        "--include-robot",
        "--record-robot-views",
        "--require-openclaw-minimum",
        "--require-clean-agent-run",
        "--require-robot-views",
        "--require-advisory-scoring",
    ):
        assert expected in body


def test_realworld_gates_require_advisory_scoring() -> None:
    text = HARNESS_JUST.read_text(encoding="utf-8")

    for recipe_name in (
        "molmo-realworld-cleanup",
        "molmo-realworld-agent-mcp",
        "molmo-realworld-agent-dogfood-kit",
        "molmo-realworld-openclaw-dogfood-kit",
        "molmo-realworld-openclaw-visual-dogfood-kit",
        "molmo-realworld-raw-fpv",
    ):
        recipe = re.search(
            rf"^{recipe_name}[\s\S]*?(?=^# |\Z)",
            text,
            re.MULTILINE,
        )
        assert recipe is not None, recipe_name
        assert "--require-advisory-scoring" in recipe.group(0), recipe_name


def test_raw_fpv_harness_uses_raw_mode_and_checker() -> None:
    text = HARNESS_JUST.read_text(encoding="utf-8")

    recipe = re.search(
        r"^molmo-realworld-raw-fpv[\s\S]*?(?=^# List task files)",
        text,
        re.MULTILINE,
    )
    assert recipe is not None
    body = recipe.group(0)
    for expected in (
        "--backend molmospaces_subprocess",
        "--perception-mode raw_fpv_only",
        "--include-robot",
        "--record-robot-views",
        "--require-robot-views",
        "--require-raw-fpv-observations",
    ):
        assert expected in body


def test_planner_manipulation_probe_accepts_only_explicit_blocked_gate() -> None:
    text = HARNESS_JUST.read_text(encoding="utf-8")

    recipe = re.search(
        r"^molmo-planner-manipulation-probe[\s\S]*?(?=^# List task files)",
        text,
        re.MULTILINE,
    )
    assert recipe is not None
    body = recipe.group(0)
    for expected in (
        "scripts/molmo_cleanup/run_molmo_planner_manipulation_probe.py",
        "--probe-mode",
        "scripts/molmo_cleanup/check_molmo_planner_manipulation_probe.py",
        "--accept-blocked-capability",
    ):
        assert expected in body


def test_planner_proof_bundle_runner_harness_stays_dry_run() -> None:
    text = HARNESS_JUST.read_text(encoding="utf-8")

    recipe = re.search(
        r"^molmo-planner-proof-bundle-runner[\s\S]*?(?=^# ADR-0044)",
        text,
        re.MULTILINE,
    )
    assert recipe is not None
    body = recipe.group(0)
    for expected in (
        "examples/molmo_cleanup/molmospaces_realworld_cleanup.py",
        "scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py",
        "scripts/molmo_cleanup/run_molmo_planner_proof_bundle_from_requests.py",
        "scripts/molmo_cleanup/check_molmo_planner_proof_bundle_runner_result.py",
        "--backend api_semantic_synthetic",
        "--probe-mode execute",
    ):
        assert expected in body
    assert "--execute-probes" not in body


def test_planner_proof_bundle_execute_rerun_gate_is_strict_and_local() -> None:
    text = HARNESS_JUST.read_text(encoding="utf-8")

    recipe = re.search(
        r"^molmo-planner-proof-bundle-execute-rerun[\s\S]*?(?=^# ADR-0014)",
        text,
        re.MULTILINE,
    )
    assert recipe is not None
    body = recipe.group(0)
    for expected in (
        "examples/molmo_cleanup/molmospaces_realworld_cleanup.py",
        "--backend molmospaces_subprocess",
        "--include-robot",
        "--record-robot-views",
        "scripts/molmo_cleanup/run_molmo_planner_proof_bundle_from_requests.py",
        "--torch-extensions-dir",
        "--execute-probes",
        "--rerun-cleanup",
        "--cleanup-output-dir",
        "--require-proof-outputs",
        "--require-cleanup-rerun-output",
        "--require-robot-views",
        "--require-planner-proof-attachment",
        "--require-planner-backed-cleanup-primitives",
        "--require-planner-cleanup-bridge-ready",
    ):
        assert expected in body
