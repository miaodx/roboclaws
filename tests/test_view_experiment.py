from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))

from view_experiment import run_view_experiment  # noqa: E402


def test_run_view_experiment_smoke(monkeypatch, tmp_path: Path) -> None:
    def stub_runner(**kwargs):
        out_dir = Path(kwargs["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "replay.json").write_text(json.dumps({"summary": {"total_steps": 7}}))
        return {
            "cells_claimed": {0: 3, 1: 4},
            "blocking_events": 1,
            "total_steps": 7,
            "termination_reason": "max_steps",
            "vlm_cost_usd": 0.25,
            "provider_status": {"provider_name": "mock"},
        }

    monkeypatch.setattr("view_experiment.GAME_RUNNERS", {"territory": stub_runner})
    result = run_view_experiment(
        seeds=[1],
        scenes=["FloorPlan201"],
        games=["territory"],
        model="mock",
        agents=2,
        steps=5,
        output_dir=str(tmp_path / "view-experiment"),
        max_usd=10.0,
    )

    results_path = Path(result["results_path"])
    rows = [json.loads(line) for line in results_path.read_text().splitlines()]
    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == "ok"
    assert row["variant"] == "map-v2+chase"
    assert row["game"] == "territory"
    assert row["cells_claimed_total"] == 7
    assert row["total_steps"] == 7


def test_run_view_experiment_logs_error_and_continues(monkeypatch, tmp_path: Path) -> None:
    calls = {"n": 0}

    def flaky_runner(**kwargs):
        calls["n"] += 1
        out_dir = Path(kwargs["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        if calls["n"] == 1:
            raise RuntimeError("boom")
        (out_dir / "replay.json").write_text(json.dumps({"summary": {"total_steps": 3}}))
        return {
            "cells_covered": 10,
            "coverage_pct": 50.0,
            "work_balance": 1.0,
            "total_steps": 3,
            "termination_reason": "max_steps",
            "vlm_cost_usd": 0.75,
            "provider_status": {"provider_name": "mock"},
        }

    monkeypatch.setattr("view_experiment.GAME_RUNNERS", {"coverage": flaky_runner})
    result = run_view_experiment(
        seeds=[1, 2],
        scenes=["FloorPlan201"],
        games=["coverage"],
        model="mock",
        agents=2,
        steps=5,
        output_dir=str(tmp_path / "view-experiment"),
        max_usd=1.0,
    )

    rows = [json.loads(line) for line in Path(result["results_path"]).read_text().splitlines()]
    assert [row["status"] for row in rows] == ["error", "ok"]
    assert rows[0]["error_kind"] == "RuntimeError"
    assert rows[1]["coverage_fraction"] == 0.5
