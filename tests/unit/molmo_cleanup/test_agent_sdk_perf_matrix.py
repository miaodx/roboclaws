from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MATRIX_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "run_agent_sdk_perf_matrix.py"


def _load_matrix_module():
    spec = importlib.util.spec_from_file_location("run_agent_sdk_perf_matrix", MATRIX_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_agent_sdk_perf_matrix_dry_run_lists_rows_and_budgets(
    tmp_path: Path,
    capsys,
) -> None:
    matrix = _load_matrix_module()
    baseline = _write_run(tmp_path / "baseline", restored=5, elapsed_s=100)
    candidate = _write_run(tmp_path / "candidate", restored=5, elapsed_s=70)
    manifest = _write_manifest(tmp_path, baseline=baseline, candidate=candidate)

    status = matrix.main(["--manifest", str(manifest), "--dry-run"])

    output = capsys.readouterr().out
    assert status == 0
    assert "Agent SDK speedup matrix dry-run" in output
    assert "provider_calls_planned: False" in output
    assert "gpt_world_public_group0" in output
    assert "unsupported_provider" in output
    assert '"max_live_runs": 0' in output


def test_agent_sdk_perf_matrix_blocks_privacy_leak(
    tmp_path: Path,
    capsys,
) -> None:
    matrix = _load_matrix_module()
    baseline = _write_run(tmp_path / "baseline", restored=5, elapsed_s=100)
    candidate = _write_run(
        tmp_path / "candidate",
        restored=5,
        elapsed_s=70,
        live_timing_extra={"raw_prompt": "do not persist me", "note": "Bearer top-secret"},
    )
    manifest = _write_manifest(tmp_path, baseline=baseline, candidate=candidate)
    decision_packet = tmp_path / "decision.json"

    status = matrix.main(
        [
            "--manifest",
            str(manifest),
            "--offline-preflight",
            "--decision-packet",
            str(decision_packet),
        ]
    )

    assert status == 1
    assert "privacy gate failed" in capsys.readouterr().err
    packet = json.loads(decision_packet.read_text(encoding="utf-8"))
    row = packet["rows"][0]
    assert row["status"] == "blocked"
    assert row["privacy_gate"]["status"] == "failed"
    reasons = {finding["reason"] for finding in row["privacy_gate"]["findings"]}
    assert "forbidden key raw_prompt" in reasons
    assert "forbidden marker bearer " in reasons


def test_agent_sdk_perf_matrix_blocks_model_call_metric_privacy_leak(
    tmp_path: Path,
    capsys,
) -> None:
    matrix = _load_matrix_module()
    baseline = _write_run(tmp_path / "baseline", restored=5, elapsed_s=100)
    candidate = _write_run(tmp_path / "candidate", restored=5, elapsed_s=70)
    (candidate / "model_call_metrics.jsonl").write_text(
        json.dumps(
            {
                "schema": "roboclaws_model_call_metric_v1",
                "agent_engine": "codex-cli",
                "raw_prompt": "do not persist me",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = _write_manifest(tmp_path, baseline=baseline, candidate=candidate)
    decision_packet = tmp_path / "decision.json"

    status = matrix.main(
        [
            "--manifest",
            str(manifest),
            "--offline-preflight",
            "--decision-packet",
            str(decision_packet),
        ]
    )

    assert status == 1
    assert "privacy gate failed" in capsys.readouterr().err
    packet = json.loads(decision_packet.read_text(encoding="utf-8"))
    row = packet["rows"][0]
    reasons = {finding["reason"] for finding in row["privacy_gate"]["findings"]}
    assert "forbidden key raw_prompt" in reasons


def test_agent_sdk_perf_matrix_blocks_openai_agents_event_privacy_leak(
    tmp_path: Path,
    capsys,
) -> None:
    matrix = _load_matrix_module()
    baseline = _write_run(tmp_path / "baseline", restored=5, elapsed_s=100)
    candidate = _write_run(tmp_path / "candidate", restored=5, elapsed_s=70)
    (candidate / "openai-agents-events.jsonl").write_text(
        json.dumps(
            {
                "schema": "openai_agents_model_input_filter_v1",
                "event": "model_input_filter",
                "metrics": {"input_bytes_reduced": 1200},
                "raw_prompt": "do not persist me",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = _write_manifest(tmp_path, baseline=baseline, candidate=candidate)
    decision_packet = tmp_path / "decision.json"

    status = matrix.main(
        [
            "--manifest",
            str(manifest),
            "--offline-preflight",
            "--decision-packet",
            str(decision_packet),
        ]
    )

    assert status == 1
    assert "privacy gate failed" in capsys.readouterr().err
    packet = json.loads(decision_packet.read_text(encoding="utf-8"))
    row = packet["rows"][0]
    reasons = {finding["reason"] for finding in row["privacy_gate"]["findings"]}
    assert "forbidden key raw_prompt" in reasons


def test_agent_sdk_perf_matrix_rejects_faster_but_worse_quality(
    tmp_path: Path,
    capsys,
) -> None:
    matrix = _load_matrix_module()
    baseline = _write_run(tmp_path / "baseline", restored=5, elapsed_s=100)
    candidate = _write_run(tmp_path / "candidate", restored=4, elapsed_s=50)
    manifest = _write_manifest(tmp_path, baseline=baseline, candidate=candidate)
    decision_packet = tmp_path / "decision.json"

    status = matrix.main(
        [
            "--manifest",
            str(manifest),
            "--offline-preflight",
            "--decision-packet",
            str(decision_packet),
        ]
    )

    assert status == 1
    assert "behavior quality regressed" in capsys.readouterr().err
    packet = json.loads(decision_packet.read_text(encoding="utf-8"))
    row = packet["rows"][0]
    assert row["status"] == "rejected"
    assert row["quality_comparison"]["regressed"] is True
    assert row["speed_comparison"]["elapsed_delta_s"] == -50.0


def test_agent_sdk_perf_matrix_accepts_same_or_better_and_reports_buckets(
    tmp_path: Path,
) -> None:
    matrix = _load_matrix_module()
    baseline = _write_run(tmp_path / "baseline", restored=5, elapsed_s=100, gap_s=80)
    candidate = _write_run(
        tmp_path / "candidate",
        restored=5,
        elapsed_s=70,
        gap_s=50,
        trace_tools=["metric_map", "metric_map", "declare_visual_candidates"],
    )
    manifest = _write_manifest(
        tmp_path,
        baseline=baseline,
        candidate=candidate,
        lane="camera-grounded-labels",
    )
    decision_packet = tmp_path / "decision.json"

    status = matrix.main(
        [
            "--manifest",
            str(manifest),
            "--offline-preflight",
            "--decision-packet",
            str(decision_packet),
        ]
    )

    assert status == 0
    packet = json.loads(decision_packet.read_text(encoding="utf-8"))
    row = packet["rows"][0]
    assert row["status"] == "accepted"
    assert row["quality_comparison"]["regressed"] is False
    assert packet["rows"][1]["status"] == "unsupported"
    assert packet["summary"]["unsupported"] == ["unsupported_provider"]
    report = row["reducible_bucket_report"]
    assert report["available"] is True
    candidate_ids = {
        candidate_id for item in report["recommendations"] for candidate_id in item["candidate_ids"]
    }
    assert {"O", "N"}.issubset(candidate_ids)


def test_agent_sdk_perf_matrix_accepts_expected_raw_fpv_diagnostic_terminal(
    tmp_path: Path,
) -> None:
    matrix = _load_matrix_module()
    baseline = _write_run(
        tmp_path / "baseline",
        restored=0,
        elapsed_s=300,
        status={"phase": "failed", "reason": "provider_transient_failure", "exit_status": 1},
        run_result=False,
        trace_tools=[
            "navigate_to_visual_candidate",
            "navigate_to_visual_candidate",
            "navigate_to_visual_candidate",
        ],
    )
    candidate = _write_run(
        tmp_path / "candidate",
        restored=0,
        elapsed_s=180,
        status={
            "phase": "failed",
            "reason": "raw_fpv_sdk_turn_budget_exhausted",
            "exit_status": 1,
        },
        run_result=False,
        trace_tools=["navigate_to_visual_candidate"],
    )
    manifest = _write_manifest(
        tmp_path,
        baseline=baseline,
        candidate=candidate,
        lane="camera-raw-fpv",
        expected_terminal="raw_fpv_sdk_turn_budget_exhausted",
    )
    decision_packet = tmp_path / "decision.json"

    status = matrix.main(
        [
            "--manifest",
            str(manifest),
            "--offline-preflight",
            "--decision-packet",
            str(decision_packet),
        ]
    )

    assert status == 0
    packet = json.loads(decision_packet.read_text(encoding="utf-8"))
    row = packet["rows"][0]
    assert row["status"] == "accepted"
    assert "raw-FPV accepted as classified diagnostic evidence" in row["reasons"]
    assert row["quality_comparison"]["regressed"] is True


def _write_manifest(
    tmp_path: Path,
    *,
    baseline: Path,
    candidate: Path,
    lane: str = "world-public-labels",
    expected_terminal: str = "finished",
) -> Path:
    manifest = tmp_path / "matrix.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": "agent_sdk_speedup_matrix_v1",
                "budget_caps": {
                    "concurrency": 1,
                    "max_live_runs": 0,
                    "max_wall_clock_s": 0,
                    "racing_multiplier": 1.0,
                },
                "candidate_groups": [
                    {
                        "group_id": "group0_foundation",
                        "candidate_ids": ["R", "S", "T", "U", "V", "W", "Y", "B", "Z", "Q"],
                    }
                ],
                "rows": [
                    {
                        "row_id": "gpt_world_public_group0",
                        "provider_profile": "codex-env",
                        "model": "gpt-5.5",
                        "evidence_lane": lane,
                        "candidate_group": "group0_foundation",
                        "candidate_ids": ["R", "S", "T", "U", "V", "W", "Y", "B", "Z", "Q"],
                        "dependency_candidate_ids": [],
                        "feature_flags": {
                            "dry_run_matrix": True,
                            "offline_preflight": True,
                            "privacy_gate": True,
                            "provider_calls": False,
                            "quality_comparator": True,
                            "reducible_bucket_report": True,
                        },
                        "stop_conditions": [
                            "privacy_gate_failed",
                            "quality_regression",
                            "provider_calls_planned",
                        ],
                        "baseline_role": "full_lane_baseline",
                        "baseline_run_dir": str(baseline),
                        "candidate_run_dir": str(candidate),
                        "provider_calls": False,
                        "expected_terminal": expected_terminal,
                    },
                    {
                        "row_id": "unsupported_provider",
                        "provider_profile": "kimi-anthropic",
                        "model": "kimi",
                        "evidence_lane": lane,
                        "candidate_group": "group0_foundation",
                        "candidate_ids": ["B"],
                        "dependency_candidate_ids": [],
                        "feature_flags": {"unsupported_matrix_row": True, "provider_calls": False},
                        "stop_conditions": ["unsupported_provider_route"],
                        "provider_calls": False,
                        "unsupported_reason": "unsupported provider route",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return manifest


def _write_run(
    run_dir: Path,
    *,
    restored: int,
    elapsed_s: float,
    gap_s: float = 40.0,
    trace_tools: list[str] | None = None,
    live_timing_extra: dict[str, object] | None = None,
    status: dict[str, object] | None = None,
    run_result: bool = True,
) -> Path:
    run_dir.mkdir()
    timing = {
        "runner_timing": {"total_elapsed_s": elapsed_s},
        "mcp_trace_timing": {
            "between_tool_gap_s": gap_s,
            "robot_view_capture_s": 20.0,
            "tool_handler_s": 5.0,
        },
    }
    if live_timing_extra:
        timing.update(live_timing_extra)
    (run_dir / "live_timing.json").write_text(json.dumps(timing), encoding="utf-8")
    (run_dir / "live_status.json").write_text(
        json.dumps(status or {"phase": "finished", "exit_status": 0}),
        encoding="utf-8",
    )
    if run_result:
        (run_dir / "run_result.json").write_text(
            json.dumps(
                {
                    "cleanup_status": "success",
                    "completion_status": "success",
                    "mess_restoration_rate": restored / 5,
                    "sweep_coverage_rate": 1.0,
                    "disturbance_count": 0,
                    "score": {
                        "restored_count": restored,
                        "total_targets": 5,
                        "mess_restoration_rate": restored / 5,
                        "disturbance_count": 0,
                        "object_results": [
                            {"restored": True, "semantic_acceptability": "preferred"}
                            for _ in range(restored)
                        ],
                    },
                }
            ),
            encoding="utf-8",
        )
    tools = trace_tools or ["observe", "navigate_to_object", "pick", "place", "done"]
    (run_dir / "trace.jsonl").write_text(
        "\n".join(
            json.dumps(
                {
                    "event": "response",
                    "tool": tool,
                    "response": {"ok": True},
                }
            )
            for tool in tools
        )
        + "\n",
        encoding="utf-8",
    )
    return run_dir
