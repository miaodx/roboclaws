from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from pytest import MonkeyPatch

REPO_ROOT = Path(__file__).resolve().parents[3]
SELECTOR_PATH = REPO_ROOT / "skills" / "eval-harness" / "scripts" / "select_eval_harness.py"
RUNNER_PATH = REPO_ROOT / "skills" / "eval-harness" / "scripts" / "run_eval_harness.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


selector = _load_module("eval_harness_selector_test", SELECTOR_PATH)
runner = _load_module("eval_harness_runner_test", RUNNER_PATH)


def _selected_rows(manifest: dict) -> dict[str, dict]:
    return {row["row_id"]: row for row in manifest["rows"] if row["selected"]}


def test_eval_harness_change_selects_eval_unit_and_smoke_suite(tmp_path: Path) -> None:
    manifest = selector.build_eval_harness(
        budget="focused",
        changed_files=["roboclaws/evals/runner.py"],
        output_dir=tmp_path,
    )

    rows = _selected_rows(manifest)
    assert manifest["schema"] == "roboclaws_eval_harness_manifest_v1"
    assert rows["eval-unit-tests"]["row_kind"] == "deterministic_gate"
    assert rows["smoke-regression-eval-suite"]["row_kind"] == "eval_suite"
    assert rows["smoke-regression-eval-suite"]["status"] == "not_run"


def test_cleanup_skill_change_selects_cleanup_suite_and_live_codex_eval(
    tmp_path: Path,
) -> None:
    manifest = selector.build_eval_harness(
        budget="focused",
        changed_files=["skills/molmo-realworld-cleanup/SKILL.md"],
        output_dir=tmp_path,
    )

    rows = _selected_rows(manifest)
    codex_row = rows["codex-cleanup-live-eval"]
    assert rows["cleanup-capability-eval-suite"]["row_kind"] == "eval_suite"
    assert codex_row["row_kind"] == "live_agent_eval"
    assert codex_row["axes"]["agent_engine"] == "codex-cli"
    assert codex_row["axes"]["provider_profile"] == "codex-env"
    assert codex_row["axes"]["evidence_lane"] == "world-public-labels"
    assert "live_execution=run" in codex_row["command"]
    assert codex_row["status"] == "not_run"


def test_agent_sdk_change_selects_openai_agents_sdk_live_eval(tmp_path: Path) -> None:
    manifest = selector.build_eval_harness(
        budget="focused",
        changed_files=["roboclaws/agents/drivers/openai_agents_live.py"],
        output_dir=tmp_path,
    )

    rows = _selected_rows(manifest)
    sdk_row = rows["openai-agents-sdk-open-task-live-eval"]
    assert sdk_row["axes"]["agent_engine"] == "openai-agents-sdk"
    assert sdk_row["axes"]["provider_profile"] == "minimax"
    assert sdk_row["axes"]["intent"] == "open-ended"
    assert sdk_row["axes"]["preset"] == ""
    assert "suite=open_ended_goals" in sdk_row["command"]
    assert "provider_profile=minimax" in sdk_row["command"]
    assert "live_execution=run" in sdk_row["command"]
    assert "openai-agents-sdk-codex-env-availability" not in rows


def test_visual_grounding_change_selects_real_dino_product_row(tmp_path: Path) -> None:
    manifest = selector.build_eval_harness(
        budget="focused",
        changed_files=["roboclaws/household/visual_grounding.py"],
        output_dir=tmp_path,
    )

    rows = _selected_rows(manifest)
    dino_row = rows["direct-camera-grounded-grounding-dino"]
    assert dino_row["row_kind"] == "product_run"
    assert dino_row["axes"]["evidence_lane"] == "camera-grounded-labels"
    assert dino_row["axes"]["camera_labeler"] == "grounding-dino"
    assert dino_row["status"] == "not_run"


def test_explicit_changed_file_does_not_pull_unrelated_worktree_diff(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(selector, "_changed_files_from_worktree", lambda: ["just/agent.just"])

    manifest = selector.build_eval_harness(
        budget="focused",
        changed_files=["roboclaws/household/visual_grounding.py"],
        output_dir=tmp_path,
    )

    rows = _selected_rows(manifest)
    assert "direct-camera-grounded-grounding-dino" in rows
    assert "route-trace-contract-tests" not in rows


def test_raw_fpv_change_selects_raw_fpv_rows(tmp_path: Path) -> None:
    manifest = selector.build_eval_harness(
        budget="focused",
        changed_files=["roboclaws/household/raw_fpv_guidance.py"],
        output_dir=tmp_path,
    )

    rows = _selected_rows(manifest)
    assert rows["direct-camera-raw-fpv"]["axes"]["evidence_lane"] == "camera-raw-fpv"
    assert rows["codex-cleanup-camera-raw-fpv-live-product"]["axes"]["agent_engine"] == "codex-cli"


def test_map_build_change_selects_map_build_suite_and_cleanup_consumer_prior(
    tmp_path: Path,
) -> None:
    manifest = selector.build_eval_harness(
        budget="focused",
        changed_files=["roboclaws/maps/actionable_semantic_map.py"],
        output_dir=tmp_path,
    )

    rows = _selected_rows(manifest)
    assert rows["direct-map-build-world-public"]["axes"]["intent"] == "map-build"
    assert rows["direct-cleanup-runtime-prior-consumer"]["axes"]["runtime_map_prior"] == "required"
    assert rows["map-build-consumer-eval-suite"]["row_kind"] == "eval_suite"


def test_scene_sampler_change_selects_sampler_stress_suite(tmp_path: Path) -> None:
    manifest = selector.build_eval_harness(
        budget="focused",
        changed_files=["roboclaws/launch/scene_sampler.py"],
        output_dir=tmp_path,
    )

    rows = _selected_rows(manifest)
    row = rows["scene-sampler-stress-eval-suite"]
    assert row["row_kind"] == "eval_suite"
    assert row["axes"]["suite"] == "scene_sampler_stress"
    assert "suite=scene_sampler_stress" in row["command"]


def test_open_ended_changed_file_selects_open_ended_contract_and_live_eval(
    tmp_path: Path,
) -> None:
    manifest = selector.build_eval_harness(
        budget="focused",
        changed_files=["docs/plans/2026-06-11-open-ended-proof-status.md"],
        output_dir=tmp_path / "harness",
    )

    rows = _selected_rows(manifest)
    row = rows["open-ended-household-contract-tests"]
    assert row["axes"]["intent"] == "open-ended"
    assert row["expense"] == "deterministic"
    assert any("test_surface_prompt_omitted_intent" in item for item in row["command"])
    assert rows["open-ended-goals-eval-suite"]["row_kind"] == "eval_suite"
    assert "suite=open_ended_goals" in rows["open-ended-goals-eval-suite"]["command"]
    assert rows["codex-open-task-live-eval"]["row_kind"] == "live_agent_eval"
    assert "suite=open_ended_goals" in rows["codex-open-task-live-eval"]["command"]
    assert "map-build-consumer-eval-suite" not in rows
    assert "cleanup-capability-eval-suite" not in rows


def test_explicit_open_ended_intent_selects_open_ended_row(tmp_path: Path) -> None:
    manifest = selector.build_eval_harness(
        budget="focused",
        intent=["open-ended"],
        output_dir=tmp_path,
    )

    rows = _selected_rows(manifest)
    assert rows["open-ended-household-contract-tests"]["axes"]["intent"] == "open-ended"
    assert rows["open-ended-goals-eval-suite"]["axes"]["suite"] == "open_ended_goals"
    assert rows["codex-open-task-live-eval"]["axes"]["intent"] == "open-ended"
    assert rows["openai-agents-sdk-open-task-live-eval"]["axes"]["provider_profile"] == "minimax"
    assert "openai-agents-sdk-codex-env-availability" not in rows


def test_explicit_planner_proof_intent_selects_planner_proof_row(tmp_path: Path) -> None:
    manifest = selector.build_eval_harness(
        budget="focused",
        intent=["planner-proof"],
        output_dir=tmp_path,
    )

    rows = _selected_rows(manifest)
    row = rows["planner-proof-dry-run-product"]
    assert row["row_kind"] == "product_run"
    assert row["axes"]["intent"] == "planner-proof"
    assert "surface=planner-proof" in row["command"]
    assert "intent=planner-proof" in row["command"]
    assert "mode=dry-run" in row["command"]
    assert "open-ended-goals-eval-suite" not in rows


def test_runtime_prior_placeholder_resolves_to_map_build_artifact(tmp_path: Path) -> None:
    manifest = selector.build_eval_harness(
        budget="focused",
        changed_files=["roboclaws/maps/actionable_semantic_map.py"],
        output_dir=tmp_path,
    )
    rows = _selected_rows(manifest)
    map_row = rows["direct-map-build-world-public"]
    prior = Path(map_row["row_dir"]) / "run" / "seed-7" / "runtime_metric_map.json"
    prior.parent.mkdir(parents=True)
    prior.write_text('{"schema":"runtime_metric_map_v1"}\n', encoding="utf-8")

    command = runner._resolve_row_command(rows["direct-cleanup-runtime-prior-consumer"], manifest)

    assert f"runtime_map_prior={prior}" in command


def test_smoke_budget_records_relevant_expensive_rows_as_user_budget_skipped(
    tmp_path: Path,
) -> None:
    manifest = selector.build_eval_harness(
        budget="smoke",
        changed_files=["skills/molmo-realworld-cleanup/SKILL.md"],
        output_dir=tmp_path,
    )

    rows = _selected_rows(manifest)
    assert rows["codex-cleanup-live-eval"]["status"] == "skipped_by_budget"
    assert rows["cleanup-contract-tests"]["status"] == "not_run"


def test_explicit_axes_select_first_class_engine_and_provider_profile(
    tmp_path: Path,
) -> None:
    manifest = selector.build_eval_harness(
        budget="focused",
        agent_engine=["codex-cli", "openai-agents-sdk"],
        provider_profile=["mify"],
        evidence_lane=["camera-grounded-labels"],
        camera_labeler=["grounding-dino"],
        output_dir=tmp_path,
    )

    rows = _selected_rows(manifest)
    assert rows["codex-cleanup-live-eval"]["axes"]["provider_profile"] == "mify"
    assert rows["openai-agents-sdk-open-task-live-eval"]["axes"]["provider_profile"] == "mify"
    assert rows["direct-camera-grounded-grounding-dino"]["axes"]["camera_labeler"] == (
        "grounding-dino"
    )


def test_explicit_codex_env_selects_agent_sdk_availability_evidence(
    tmp_path: Path,
) -> None:
    manifest = selector.build_eval_harness(
        budget="focused",
        agent_engine=["openai-agents-sdk"],
        provider_profile=["codex-env"],
        intent=["open-ended"],
        output_dir=tmp_path,
    )

    rows = _selected_rows(manifest)
    behavior_row = rows["openai-agents-sdk-open-task-live-eval"]
    availability_row = rows["openai-agents-sdk-codex-env-availability"]
    assert behavior_row["axes"]["provider_profile"] == "minimax"
    assert behavior_row["requirement"] == "required"
    assert availability_row["axes"]["provider_profile"] == "codex-env"
    assert availability_row["requirement"] == "optional"
    assert manifest["summary"]["optional_row_count"] == 1


def test_execute_marks_live_row_blocked_when_provider_is_missing(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("CODEX_BASE_URL", raising=False)
    monkeypatch.delenv("CODEX_API_KEY", raising=False)
    monkeypatch.delenv("XM_LLM_API_KEY", raising=False)
    manifest = selector.build_eval_harness(
        mode="execute",
        budget="focused",
        changed_files=["skills/molmo-realworld-cleanup/SKILL.md"],
        output_dir=tmp_path,
    )

    runner._execute_harness(manifest)

    rows = _selected_rows(manifest)
    assert rows["codex-cleanup-live-eval"]["status"] == "blocked"
    assert rows["codex-cleanup-live-eval"]["blocker_category"] == "model_or_provider_unavailable"


def test_execute_defaults_provider_timing_proxy_for_live_codex_row(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    captured: list[dict[str, str]] = []
    monkeypatch.delenv("ROBOCLAWS_PROVIDER_TIMING_PROXY", raising=False)
    monkeypatch.setattr(runner, "_row_blockers", lambda row, manifest: [])

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
    manifest = selector.build_eval_harness(
        mode="execute",
        budget="focused",
        changed_files=["skills/molmo-realworld-cleanup/SKILL.md"],
        output_dir=tmp_path,
    )

    runner._execute_harness(manifest)

    assert captured
    assert captured[0]["ROBOCLAWS_PROVIDER_TIMING_PROXY"] == "1"
    rows = _selected_rows(manifest)
    assert rows["codex-cleanup-live-eval"]["defaulted_provider_timing_proxy"] is True


def test_execute_preserves_provider_timing_proxy_escape_hatch(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    captured: list[dict[str, str]] = []
    monkeypatch.setenv("ROBOCLAWS_PROVIDER_TIMING_PROXY", "0")
    monkeypatch.setattr(runner, "_row_blockers", lambda row, manifest: [])

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
    manifest = selector.build_eval_harness(
        mode="execute",
        budget="focused",
        changed_files=["skills/molmo-realworld-cleanup/SKILL.md"],
        output_dir=tmp_path,
    )

    runner._execute_harness(manifest)

    assert captured
    assert captured[0]["ROBOCLAWS_PROVIDER_TIMING_PROXY"] == "0"
    rows = _selected_rows(manifest)
    assert "defaulted_provider_timing_proxy" not in rows["codex-cleanup-live-eval"]


def test_detached_live_product_row_waits_for_terminal_artifact(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner, "_row_blockers", lambda row, manifest: [])
    clock = {"now": 0.0, "sleeps": 0}

    def fake_run(command, **_kwargs):
        output_arg = next(item for item in command if str(item).startswith("output_dir="))
        output_dir = Path(str(output_arg).split("=", 1)[1])
        run_dir = output_dir / "0615_1225" / "seed-7"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "live_status.json").write_text('{"phase":"queued"}\n', encoding="utf-8")

        class _Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return _Result()

    def fake_sleep(_seconds: float) -> None:
        clock["sleeps"] += 1
        run_dir = (
            tmp_path
            / "rows"
            / "codex-cleanup-camera-raw-fpv-live-product"
            / "run"
            / "0615_1225"
            / "seed-7"
        )
        (run_dir / "run_result.json").write_text('{"cleanup_success":true}\n', encoding="utf-8")
        (run_dir / "report.html").write_text("<html></html>\n", encoding="utf-8")

    def fake_monotonic() -> float:
        clock["now"] += 0.1
        return clock["now"]

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    monkeypatch.setattr(runner.time, "sleep", fake_sleep)
    monkeypatch.setattr(runner.time, "monotonic", fake_monotonic)
    manifest = selector.build_eval_harness(
        mode="execute",
        budget="focused",
        changed_files=["roboclaws/household/raw_fpv_guidance.py"],
        output_dir=tmp_path,
    )

    runner._execute_harness(manifest)

    row = _selected_rows(manifest)["codex-cleanup-camera-raw-fpv-live-product"]
    assert clock["sleeps"] == 1
    assert row["status"] == "ran"
    assert row["outcome"] == "passed"
    assert row["detached_live_run_dir"].endswith("0615_1225/seed-7")
    assert any(path.endswith("run_result.json") for path in row["output_artifacts"])


def test_failed_live_row_with_busy_mcp_port_is_classified_as_blocked() -> None:
    for stderr in (
        (
            "error: requested MCP port 127.0.0.1:18788 is already accepting connections\n"
            "refusing to choose another port"
        ),
        "error: no MolmoSpaces visual backend slot is available under output/molmo/slots",
    ):
        row = {"exit_code": 1}

        runner._classify_failed_row(
            row,
            stderr=stderr,
            stdout="",
        )

        assert row["status"] == "blocked"
        assert row["outcome"] == "blocked"
        assert row["blocker_category"] == "environment_blocked"


def test_optional_blocked_rows_do_not_fail_harness_exit_status() -> None:
    manifest = {
        "rows": [
            {
                "selected": True,
                "requirement": "optional",
                "status": "blocked",
                "outcome": "blocked",
            },
            {
                "selected": True,
                "requirement": "required",
                "status": "ran",
                "exit_code": 0,
                "outcome": "passed",
            },
        ]
    }

    assert runner._exit_status(manifest) == 0
    manifest["rows"][1]["status"] = "blocked"
    manifest["rows"][1]["outcome"] = "blocked"
    assert runner._exit_status(manifest) == 2


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


def test_dino_sidecar_requirement_autostarts_default_service(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    calls = {"available": 0, "started": 0, "stopped": 0}

    def fake_available() -> bool:
        calls["available"] += 1
        return calls["started"] > 0

    def fake_start(manifest: dict) -> bool:
        calls["started"] += 1
        manifest["dino_sidecar_autostart"] = {"base_url": runner.DEFAULT_VISUAL_GROUNDING_BASE_URL}
        return True

    def fake_stop() -> None:
        calls["stopped"] += 1

    monkeypatch.delenv("ROBOCLAWS_EVAL_HARNESS_AUTOSTART_DINO_SIDECAR", raising=False)
    monkeypatch.setattr(runner.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(runner, "_dino_sidecar_available", fake_available)
    monkeypatch.setattr(runner, "_start_managed_dino_sidecar", fake_start)
    monkeypatch.setattr(runner, "_stop_managed_dino_sidecars", fake_stop)
    monkeypatch.setattr(
        runner,
        "_run_row",
        lambda row, manifest: row.update({"status": "ran", "outcome": "passed", "exit_code": 0}),
    )
    manifest = selector.build_eval_harness(
        mode="execute",
        budget="focused",
        changed_files=["roboclaws/household/visual_grounding.py"],
        output_dir=tmp_path,
    )

    runner._execute_harness(manifest)

    row = _selected_rows(manifest)["direct-camera-grounded-grounding-dino"]
    assert row["status"] == "ran"
    assert row["outcome"] == "passed"
    assert calls["available"] >= 1
    assert calls["started"] == 1
    assert calls["stopped"] == 1
    assert manifest["dino_sidecar_autostart"]["base_url"] == runner.DEFAULT_VISUAL_GROUNDING_BASE_URL


def test_dino_sidecar_autostart_can_be_disabled(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("ROBOCLAWS_EVAL_HARNESS_AUTOSTART_DINO_SIDECAR", "0")
    monkeypatch.setattr(runner.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(runner, "_dino_sidecar_available", lambda: False)
    monkeypatch.setattr(
        runner,
        "_start_managed_dino_sidecar",
        lambda manifest: (_ for _ in ()).throw(AssertionError("should not start")),
    )
    manifest = selector.build_eval_harness(
        mode="execute",
        budget="focused",
        changed_files=["roboclaws/household/visual_grounding.py"],
        output_dir=tmp_path,
    )

    blockers = runner._row_blockers(
        _selected_rows(manifest)["direct-camera-grounded-grounding-dino"],
        manifest,
    )

    assert blockers == [
        {
            "category": "environment_blocked",
            "detail": "Grounding DINO visual-grounding sidecar is not reachable",
        }
    ]


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
    manifest = json.loads((tmp_path / "eval_harness.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "roboclaws_eval_harness_manifest_v1"
    assert (tmp_path / "eval_harness.md").exists()
    assert (tmp_path / "eval_harness.html").exists()
    assert "openai-agents-sdk-open-task-live-eval" in (tmp_path / "eval_harness.md").read_text(
        encoding="utf-8"
    )
