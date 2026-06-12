from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from pytest import MonkeyPatch

REPO_ROOT = Path(__file__).resolve().parents[3]
SELECTOR_PATH = (
    REPO_ROOT / "skills" / "agent-validation-matrix" / "scripts" / "select_validation_matrix.py"
)
RUNNER_PATH = (
    REPO_ROOT / "skills" / "agent-validation-matrix" / "scripts" / "run_validation_matrix.py"
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


selector = _load_module("agent_validation_selector_test", SELECTOR_PATH)
runner = _load_module("agent_validation_runner_test", RUNNER_PATH)


def _selected_gates(matrix: dict) -> dict[str, dict]:
    return {gate["gate_id"]: gate for gate in matrix["gates"] if gate["selected"]}


def test_cleanup_skill_change_selects_live_codex_cleanup_gate(tmp_path: Path) -> None:
    matrix = selector.build_validation_matrix(
        budget="focused",
        changed_files=["skills/molmo-realworld-cleanup/SKILL.md"],
        output_dir=tmp_path,
    )

    gates = _selected_gates(matrix)
    codex_gate = gates["codex-cleanup-world-oracle"]
    assert codex_gate["axes"]["agent_engine"] == "codex-cli"
    assert codex_gate["axes"]["provider_profile"] == "codex-env"
    assert codex_gate["axes"]["evidence_lane"] == "world-oracle-labels"
    assert codex_gate["status"] == "optional_not_run"


def test_agent_sdk_change_selects_openai_agents_sdk_gate(tmp_path: Path) -> None:
    matrix = selector.build_validation_matrix(
        budget="focused",
        changed_files=["roboclaws/agents/drivers/openai_agents_live.py"],
        output_dir=tmp_path,
    )

    gates = _selected_gates(matrix)
    sdk_gate = gates["openai-agents-sdk-cleanup"]
    assert sdk_gate["axes"]["agent_engine"] == "openai-agents-sdk"
    assert sdk_gate["axes"]["provider_profile"] == "codex-env"


def test_visual_grounding_change_selects_real_dino_gate(tmp_path: Path) -> None:
    matrix = selector.build_validation_matrix(
        budget="focused",
        changed_files=["roboclaws/household/visual_grounding.py"],
        output_dir=tmp_path,
    )

    gates = _selected_gates(matrix)
    dino_gate = gates["direct-camera-grounded-grounding-dino"]
    assert dino_gate["axes"]["evidence_lane"] == "camera-grounded-labels"
    assert dino_gate["axes"]["camera_labeler"] == "grounding-dino"
    assert dino_gate["status"] == "optional_not_run"


def test_explicit_changed_file_does_not_pull_unrelated_worktree_diff(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(selector, "_changed_files_from_worktree", lambda: ["just/agent.just"])

    matrix = selector.build_validation_matrix(
        budget="focused",
        changed_files=["roboclaws/household/visual_grounding.py"],
        output_dir=tmp_path,
    )

    gates = _selected_gates(matrix)
    assert "direct-camera-grounded-grounding-dino" in gates
    assert "route-trace-contract-tests" not in gates


def test_raw_fpv_change_selects_raw_fpv_gate(tmp_path: Path) -> None:
    matrix = selector.build_validation_matrix(
        budget="focused",
        changed_files=["roboclaws/household/raw_fpv_guidance.py"],
        output_dir=tmp_path,
    )

    gates = _selected_gates(matrix)
    assert gates["direct-camera-raw-fpv"]["axes"]["evidence_lane"] == "camera-raw-fpv"
    assert gates["codex-cleanup-camera-raw-fpv"]["axes"]["agent_engine"] == "codex-cli"


def test_map_build_change_selects_map_build_and_cleanup_consumer_prior(
    tmp_path: Path,
) -> None:
    matrix = selector.build_validation_matrix(
        budget="focused",
        changed_files=["roboclaws/maps/actionable_semantic_map.py"],
        output_dir=tmp_path,
    )

    gates = _selected_gates(matrix)
    assert gates["direct-map-build-world-oracle"]["axes"]["intent"] == "map-build"
    assert gates["direct-cleanup-runtime-prior-consumer"]["axes"]["runtime_map_prior"] == "required"


def test_smoke_budget_records_relevant_expensive_gates_as_user_budget_skipped(
    tmp_path: Path,
) -> None:
    matrix = selector.build_validation_matrix(
        budget="smoke",
        changed_files=["skills/molmo-realworld-cleanup/SKILL.md"],
        output_dir=tmp_path,
    )

    gates = _selected_gates(matrix)
    assert gates["codex-cleanup-world-oracle"]["status"] == "required_skipped_by_user_budget"
    assert gates["cleanup-contract-tests"]["status"] == "optional_not_run"


def test_explicit_axes_select_first_class_engine_and_provider_profile(
    tmp_path: Path,
) -> None:
    matrix = selector.build_validation_matrix(
        budget="focused",
        agent_engine=["codex-cli", "openai-agents-sdk"],
        provider_profile=["mify"],
        evidence_lane=["camera-grounded-labels"],
        camera_labeler=["grounding-dino"],
        output_dir=tmp_path,
    )

    gates = _selected_gates(matrix)
    assert gates["codex-cleanup-world-oracle"]["axes"]["provider_profile"] == "mify"
    assert gates["openai-agents-sdk-cleanup"]["axes"]["provider_profile"] == "mify"
    assert gates["direct-camera-grounded-grounding-dino"]["axes"]["camera_labeler"] == (
        "grounding-dino"
    )


def test_execute_marks_live_gate_blocked_when_provider_is_missing(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("CODEX_BASE_URL", raising=False)
    monkeypatch.delenv("CODEX_API_KEY", raising=False)
    monkeypatch.delenv("XM_LLM_API_KEY", raising=False)
    matrix = selector.build_validation_matrix(
        mode="execute",
        budget="focused",
        changed_files=["skills/molmo-realworld-cleanup/SKILL.md"],
        output_dir=tmp_path,
    )

    runner._execute_matrix(matrix)

    gates = _selected_gates(matrix)
    assert gates["codex-cleanup-world-oracle"]["status"] == "required_blocked"
    assert gates["codex-cleanup-world-oracle"]["blocker_category"] == "missing_provider_key"


def test_recommendation_writes_json_markdown_and_html(tmp_path: Path) -> None:
    exit_code = runner.main(
        [
            "recommend",
            "--budget",
            "focused",
            "--changed-file",
            "roboclaws/agents/drivers/openai_agents_live.py",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads((tmp_path / "validation_matrix.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "agent_validation_matrix_v1"
    assert (tmp_path / "validation_matrix.md").exists()
    assert (tmp_path / "validation_matrix.html").exists()
    assert "openai-agents-sdk-cleanup" in (tmp_path / "validation_matrix.md").read_text(
        encoding="utf-8"
    )
