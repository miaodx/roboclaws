from __future__ import annotations

import importlib.util
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
