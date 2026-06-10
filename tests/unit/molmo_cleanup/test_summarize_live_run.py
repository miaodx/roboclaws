from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SUMMARY_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "summarize_live_run.py"


def _load_summary_module():
    spec = importlib.util.spec_from_file_location("summarize_live_run", SUMMARY_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_open_ended_summary_uses_claim_headline_instead_of_cleanup_score(
    tmp_path: Path,
    capsys,
) -> None:
    summarize = _load_summary_module()
    run_dir = tmp_path / "seed-7"
    run_dir.mkdir()
    report_path = run_dir / "report.html"
    report_path.write_text("<html></html>\n", encoding="utf-8")

    result = summarize._result_summary(
        {
            "task_surface": "household-world",
            "task_intent": "open-ended",
            "cleanup_status": "failed",
            "completion_status": "failed",
            "sweep_coverage_rate": 0.875,
            "policy": "codex_agent",
            "score": {"restored_count": 0, "total_targets": 5},
            "goal_contract": {
                "schema": "roboclaws_goal_contract_v1",
                "surface": "household-world",
                "intent": "open-ended",
            },
            "agent_completion_claim": {
                "schema": "roboclaws_agent_completion_claim_v1",
                "completion_summary": "Found an apple that satisfies the thirst goal.",
            },
            "artifacts": {"report": str(report_path)},
        },
        run_dir,
    )

    assert result["intent"] == "open-ended"
    assert result["headline"] == "claim=present"

    summarize._print_summary(
        {
            "run_dir": str(run_dir),
            "session": "",
            "tmux_state": "stopped",
            "runner": {
                "phase": "finished",
                "exit_status": 0,
                "elapsed_s": 1.0,
                "started_at": "2026-06-09 18:55:31 CST",
                "finished_at": "2026-06-09 18:58:47 CST",
            },
            "trace": {
                "events": 0,
                "requests": 0,
                "responses": 0,
                "last_event": "none",
                "last_response": "none",
                "progress": {
                    "observes": 0,
                    "navigate_to_object": 0,
                    "picks": 0,
                    "navigate_to_receptacle": 0,
                    "opens": 0,
                    "places": 0,
                    "place_inside": 0,
                    "closes": 0,
                    "done": 1,
                },
            },
            "timing": {"runner": {}, "mcp": {}},
            "result": result,
            "artifacts": {},
            "last_codex_message": "",
            "driver_tail": "",
        }
    )

    output = capsys.readouterr().out
    assert "result: open-ended claim=present cleanup_score=failed" in output
    assert "claim: Found an apple that satisfies the thirst goal." in output
    assert "result: failed completion=failed" not in output


def test_agent_sdk_comparison_manifest_rejects_smoke_full_lane(
    tmp_path: Path,
    capsys,
) -> None:
    summarize = _load_summary_module()
    baseline = _write_run(tmp_path / "baseline", elapsed_s=10.0, gap_s=7.0, lane="smoke")
    candidate = _write_run(
        tmp_path / "candidate",
        elapsed_s=8.0,
        gap_s=5.0,
        lane="world-public-labels",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "comparisons": [
                    {
                        "key": "bad",
                        "lane": "world-public-labels",
                        "baseline_role": "smoke_reference",
                        "baseline_run_dir": str(baseline),
                        "candidate_run_dir": str(candidate),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    status = summarize.main(["--comparison-manifest", str(manifest)])

    assert status == 1
    assert "smoke reference cannot satisfy full-lane baseline" in capsys.readouterr().err


def test_agent_sdk_comparison_manifest_prints_explicit_run_pairs(
    tmp_path: Path,
    capsys,
) -> None:
    summarize = _load_summary_module()
    baseline = _write_run(
        tmp_path / "baseline",
        elapsed_s=100.0,
        gap_s=60.0,
        lane="world-public-labels",
        uncached_tokens=1000,
        cache_hit_ratio=0.5,
    )
    candidate = _write_run(
        tmp_path / "candidate",
        elapsed_s=70.0,
        gap_s=30.0,
        lane="world-public-labels",
        uncached_tokens=650,
        cache_hit_ratio=0.7,
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "comparisons": [
                    {
                        "key": "gpt_world_public",
                        "lane": "world-public-labels",
                        "provider_profile": "codex-env",
                        "baseline_role": "full_lane_baseline",
                        "baseline_run_dir": str(baseline),
                        "candidate_run_dir": str(candidate),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    status = summarize.main(["--comparison-manifest", str(manifest)])

    output = capsys.readouterr().out
    assert status == 0
    assert "Agent SDK comparison manifest" in output
    assert "gpt_world_public | codex-env | world-public-labels" in output
    assert "-30.0s" in output
    assert "-350" in output
    assert "available(max=900)" in output
    assert "finished" in output


def test_agent_sdk_comparison_manifest_prints_terminal_classification(
    tmp_path: Path,
    capsys,
) -> None:
    summarize = _load_summary_module()
    baseline = _write_run(
        tmp_path / "baseline",
        elapsed_s=100.0,
        gap_s=60.0,
        lane="camera-raw-fpv",
        uncached_tokens=1000,
        cache_hit_ratio=0.5,
    )
    candidate = _write_run(
        tmp_path / "candidate",
        elapsed_s=70.0,
        gap_s=30.0,
        lane="camera-raw-fpv",
        uncached_tokens=650,
        cache_hit_ratio=0.7,
        terminal_reason="raw_fpv_sdk_turn_budget_exhausted",
        run_result=False,
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "comparisons": [
                    {
                        "key": "raw_fpv",
                        "lane": "camera-raw-fpv",
                        "provider_profile": "codex-env",
                        "baseline_role": "diagnostic",
                        "baseline_run_dir": str(baseline),
                        "candidate_run_dir": str(candidate),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    status = summarize.main(["--comparison-manifest", str(manifest)])

    output = capsys.readouterr().out
    assert status == 0
    assert "raw_fpv_sdk_turn_budget_exhausted" in output
    assert "available(max=900)" in output
    assert "raw_fpv_sdk_turn_budget_exhausted" in output


def test_agent_sdk_comparison_manifest_treats_null_context_as_unavailable(
    tmp_path: Path,
    capsys,
) -> None:
    summarize = _load_summary_module()
    baseline = _write_run(
        tmp_path / "baseline",
        elapsed_s=100.0,
        gap_s=60.0,
        lane="world-public-labels",
        null_context=True,
    )
    candidate = _write_run(
        tmp_path / "candidate",
        elapsed_s=70.0,
        gap_s=30.0,
        lane="world-public-labels",
        uncached_tokens=650,
        cache_hit_ratio=0.7,
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "comparisons": [
                    {
                        "key": "null_context",
                        "lane": "world-public-labels",
                        "baseline_run_dir": str(baseline),
                        "candidate_run_dir": str(candidate),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    status = summarize.main(["--comparison-manifest", str(manifest)])

    output = capsys.readouterr().out
    assert status == 0
    assert "unavailable" in output
    assert "null_context" in output


def _write_run(
    run_dir: Path,
    *,
    elapsed_s: float,
    gap_s: float,
    lane: str,
    uncached_tokens: int | None = None,
    cache_hit_ratio: float | None = None,
    terminal_reason: str = "",
    run_result: bool = True,
    null_context: bool = False,
) -> Path:
    run_dir.mkdir()
    context_metrics = {"available": False, "source": "unavailable", "limitations": ["fixture"]}
    if uncached_tokens is not None:
        context_metrics = {
            "available": True,
            "source": "openai_agents_span_usage",
            "limitations": [],
            "total_uncached_input_tokens": uncached_tokens,
            "max_input_tokens": 900,
            "cache_hit_ratio": cache_hit_ratio,
        }
    (run_dir / "live_timing.json").write_text(
        json.dumps(
            {
                "provider_profile": "codex-env",
                "evidence_lane": lane,
                "runner_timing": {"total_elapsed_s": elapsed_s},
                "mcp_trace_timing": {"between_tool_gap_s": gap_s},
                "context_metrics": None if null_context else context_metrics,
                "agent_sdk_budget_terminal": (
                    {"reason": terminal_reason} if terminal_reason else {}
                ),
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "live_status.json").write_text(
        json.dumps(
            {
                "phase": "failed" if terminal_reason else "finished",
                "exit_status": 1 if terminal_reason else 0,
                "reason": terminal_reason,
            }
        ),
        encoding="utf-8",
    )
    if run_result:
        (run_dir / "run_result.json").write_text(
            json.dumps({"task_name": "household-cleanup"}),
            encoding="utf-8",
        )
    return run_dir
