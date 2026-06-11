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


def test_open_ended_changed_file_selects_first_class_open_ended_gate(tmp_path: Path) -> None:
    matrix = selector.build_validation_matrix(
        budget="focused",
        changed_files=["docs/plans/2026-06-11-open-ended-proof-status.md"],
        output_dir=tmp_path / "matrix",
    )

    gates = _selected_gates(matrix)
    gate = gates["open-ended-household-contract-tests"]
    assert gate["axes"]["intent"] == "open-ended"
    assert gate["expense"] == "deterministic"
    assert any("test_surface_prompt_omitted_intent" in item for item in gate["command"])


def test_explicit_open_ended_intent_selects_open_ended_gate(tmp_path: Path) -> None:
    matrix = selector.build_validation_matrix(
        budget="focused",
        intent=["open-ended"],
        output_dir=tmp_path,
    )

    gates = _selected_gates(matrix)
    assert gates["open-ended-household-contract-tests"]["axes"]["intent"] == "open-ended"


def test_runtime_prior_placeholder_resolves_to_map_build_artifact(tmp_path: Path) -> None:
    matrix = selector.build_validation_matrix(
        budget="focused",
        changed_files=["roboclaws/maps/actionable_semantic_map.py"],
        output_dir=tmp_path,
    )
    gates = _selected_gates(matrix)
    map_gate = gates["direct-map-build-world-oracle"]
    prior = Path(map_gate["gate_dir"]) / "run" / "seed-7" / "runtime_metric_map.json"
    prior.parent.mkdir(parents=True)
    prior.write_text('{"schema":"runtime_metric_map_v1"}\n', encoding="utf-8")

    command = runner._resolve_gate_command(gates["direct-cleanup-runtime-prior-consumer"], matrix)

    assert f"runtime_map_prior={prior}" in command


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


def test_execute_defaults_provider_timing_proxy_for_live_codex_gate(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    captured: list[dict[str, str]] = []
    monkeypatch.delenv("ROBOCLAWS_PROVIDER_TIMING_PROXY", raising=False)
    monkeypatch.setattr(runner, "_gate_blockers", lambda gate, matrix: [])

    def fake_run(command, **kwargs):
        if "agent_engine=codex-cli" in command:
            env = kwargs.get("env")
            assert isinstance(env, dict)
            captured.append(env)

        class _Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return _Result()

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    matrix = selector.build_validation_matrix(
        mode="execute",
        budget="focused",
        changed_files=["skills/molmo-realworld-cleanup/SKILL.md"],
        output_dir=tmp_path,
    )

    runner._execute_matrix(matrix)

    assert captured
    assert captured[0]["ROBOCLAWS_PROVIDER_TIMING_PROXY"] == "1"
    gates = _selected_gates(matrix)
    assert gates["codex-cleanup-world-oracle"]["defaulted_provider_timing_proxy"] is True


def test_execute_preserves_provider_timing_proxy_escape_hatch(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    captured: list[dict[str, str]] = []
    monkeypatch.setenv("ROBOCLAWS_PROVIDER_TIMING_PROXY", "0")
    monkeypatch.setattr(runner, "_gate_blockers", lambda gate, matrix: [])

    def fake_run(command, **kwargs):
        if "agent_engine=codex-cli" in command:
            env = kwargs.get("env")
            assert isinstance(env, dict)
            captured.append(env)

        class _Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return _Result()

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    matrix = selector.build_validation_matrix(
        mode="execute",
        budget="focused",
        changed_files=["skills/molmo-realworld-cleanup/SKILL.md"],
        output_dir=tmp_path,
    )

    runner._execute_matrix(matrix)

    assert captured
    assert captured[0]["ROBOCLAWS_PROVIDER_TIMING_PROXY"] == "0"
    gates = _selected_gates(matrix)
    assert "defaulted_provider_timing_proxy" not in gates["codex-cleanup-world-oracle"]


def test_failed_live_gate_with_busy_mcp_port_is_classified_as_blocked() -> None:
    for stderr in (
        (
            "error: requested MCP port 127.0.0.1:18788 is already accepting connections\n"
            "refusing to choose another port"
        ),
        "error: no MolmoSpaces visual backend slot is available under output/molmo/slots",
    ):
        gate = {"exit_code": 1}

        runner._classify_failed_gate(
            gate,
            stderr=stderr,
            stdout="",
        )

        assert gate["status"] == "required_blocked"
        assert gate["outcome"] == "blocked"
        assert gate["blocker_category"] == "live_session_active"


def test_dino_sidecar_default_matches_documented_service_port(monkeypatch: MonkeyPatch) -> None:
    calls: list[tuple[tuple[str, int], float]] = []

    class _Socket:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    def fake_create_connection(address: tuple[str, int], timeout: float):
        calls.append((address, timeout))
        return _Socket()

    monkeypatch.delenv("VISUAL_GROUNDING_BASE_URL", raising=False)
    monkeypatch.setattr(runner.socket, "create_connection", fake_create_connection)

    assert runner._dino_sidecar_available() is True
    assert calls == [(("127.0.0.1", 18880), 0.35)]


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
