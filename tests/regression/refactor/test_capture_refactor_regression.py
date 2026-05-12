from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "regression"))

from capture_refactor_regression import run_capture  # noqa: E402

from roboclaws.regression import (  # noqa: E402
    SUITE_REGISTRY,
    CaptureRequest,
    RegressionSuite,
    _capture_explore_vlm,
    _capture_openclaw_autonomous,
    _capture_openclaw_demo,
)


def _write_replay(
    run_dir: Path,
    *,
    summary: dict,
    final_game_state: dict | None = None,
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    replay = {
        "metadata": {"game": "test", "agent_count": 1, "total_steps": 1},
        "summary": summary,
        "steps": [{"game_state": final_game_state or {}}],
    }
    (run_dir / "replay.json").write_text(json.dumps(replay), encoding="utf-8")


def _load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_fake_suite_rows_append_and_preserve_unique_artifact_dirs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_capture(request: CaptureRequest, artifact_dir: Path) -> dict:
        (artifact_dir / "marker.txt").write_text(request.scene, encoding="utf-8")
        return {"cells_visited": 3, "termination_reason": "max_steps"}

    monkeypatch.setitem(
        SUITE_REGISTRY,
        "fake-suite",
        RegressionSuite(
            name="fake-suite",
            backend="vlm",
            game="explore",
            capture=fake_capture,
        ),
    )

    first = run_capture(
        suites=["fake-suite"],
        output_dir=str(tmp_path / "captures"),
        label="baseline-2026-04-23",
        scenes=["FloorPlan201"],
        seeds=[1],
        agents=1,
        steps=5,
        model="mock",
    )
    second = run_capture(
        suites=["fake-suite"],
        output_dir=str(tmp_path / "captures"),
        label="baseline-2026-04-23",
        scenes=["FloorPlan201"],
        seeds=[1],
        agents=1,
        steps=5,
        model="mock",
    )

    rows = _load_rows(Path(first["results_path"]))
    assert Path(first["results_path"]) == Path(second["results_path"])
    assert len(rows) == 2
    assert rows[0]["status"] == "ok"
    assert rows[1]["status"] == "ok"
    assert rows[0]["artifact_dir"] != rows[1]["artifact_dir"]


def test_regression_suite_captures_normalized_success_row(tmp_path: Path) -> None:
    def fake_capture(request: CaptureRequest, artifact_dir: Path) -> dict:
        (artifact_dir / "marker.txt").write_text(request.scene, encoding="utf-8")
        return {
            "cells_visited": 8,
            "variant": "map-v2+chase",
            "model": "openclaw/agent-0",
        }

    suite = RegressionSuite(
        name="fake-suite",
        backend="openclaw",
        game="navigation",
        capture=fake_capture,
        default_variant="fallback",
    )
    artifact_dir = tmp_path / "artifact"
    request = CaptureRequest(
        label="baseline-2026-04-23",
        scene="FloorPlan201",
        seed=1,
        agents=2,
        steps=5,
        model="mock",
        allow_local=True,
    )

    row = suite.capture_ok_row(
        request=request,
        artifact_dir=artifact_dir,
        run_id="run-1",
        elapsed_seconds=1.2349,
    )

    assert row["suite"] == "fake-suite"
    assert row["backend"] == "openclaw"
    assert row["game"] == "navigation"
    assert row["model"] == "openclaw/agent-0"
    assert row["variant"] == "map-v2+chase"
    assert row["status"] == "ok"
    assert row["cells_visited"] == 8
    assert row["wallclock_seconds"] == 1.235


def test_regression_suite_captures_normalized_error_row(tmp_path: Path) -> None:
    suite = RegressionSuite(
        name="fake-suite",
        backend="vlm",
        game="explore",
        capture=lambda _request, _artifact_dir: {},
        default_variant="map-v2+chase",
    )
    request = CaptureRequest(
        label="baseline-2026-04-23",
        scene="FloorPlan201",
        seed=1,
        agents=1,
        steps=5,
        model="mock",
    )

    row = suite.capture_error_row(
        request=request,
        artifact_dir=tmp_path / "artifact",
        run_id="run-1",
        exc=RuntimeError("boom"),
        elapsed_seconds=2.5,
    )

    assert row["status"] == "error"
    assert row["variant"] == "map-v2+chase"
    assert row["error_kind"] == "RuntimeError"
    assert row["error"] == "boom"
    assert row["wallclock_seconds"] == 2.5


def test_multiple_suites_run_in_deterministic_order_and_continue_after_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    call_order: list[str] = []

    def alpha_capture(_request: CaptureRequest, artifact_dir: Path) -> dict:
        call_order.append(f"alpha:{artifact_dir.parent.name}")
        return {"cells_visited": 1}

    def beta_capture(request: CaptureRequest, artifact_dir: Path) -> dict:
        call_order.append(f"beta:{request.scene}")
        if request.scene == "FloorPlan201":
            raise RuntimeError("boom")
        (artifact_dir / "ok.txt").write_text("ok", encoding="utf-8")
        return {"cells_visited": 2}

    monkeypatch.setitem(
        SUITE_REGISTRY,
        "alpha-suite",
        RegressionSuite(
            name="alpha-suite",
            backend="vlm",
            game="explore",
            capture=alpha_capture,
        ),
    )
    monkeypatch.setitem(
        SUITE_REGISTRY,
        "beta-suite",
        RegressionSuite(
            name="beta-suite",
            backend="vlm",
            game="explore",
            capture=beta_capture,
        ),
    )

    result = run_capture(
        suites=["alpha-suite", "beta-suite"],
        output_dir=str(tmp_path / "captures"),
        label="candidate-dongxu-dev-0423",
        scenes=["FloorPlan201", "FloorPlan205"],
        seeds=[1],
        agents=1,
        steps=5,
        model="mock",
    )

    rows = _load_rows(Path(result["results_path"]))
    assert call_order == [
        "alpha:FloorPlan201-seed1",
        "alpha:FloorPlan205-seed1",
        "beta:FloorPlan201",
        "beta:FloorPlan205",
    ]
    assert [row["status"] for row in rows] == ["ok", "ok", "error", "ok"]
    assert rows[2]["error_kind"] == "RuntimeError"


def test_local_only_suites_require_allow_local_and_still_log_error_rows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setitem(
        SUITE_REGISTRY,
        "local-suite",
        RegressionSuite(
            name="local-suite",
            backend="openclaw",
            game="navigation",
            capture=lambda _request, _artifact_dir: {"visited_cells": 1},
            local_dev_only=True,
        ),
    )

    result = run_capture(
        suites=["local-suite"],
        output_dir=str(tmp_path / "captures"),
        label="baseline-2026-04-23",
        scenes=["FloorPlan201"],
        seeds=[1],
        agents=1,
        steps=5,
        model="mock",
        allow_local=False,
    )

    rows = _load_rows(Path(result["results_path"]))
    assert result["had_errors"] is True
    assert rows[0]["status"] == "error"
    assert rows[0]["error_kind"] == "LocalOnlySuiteError"


def test_built_in_explore_suite_extracts_result_and_replay_summary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen_kwargs: dict[str, object] = {}

    def fake_run_exploration(**kwargs):
        seen_kwargs.update(kwargs)
        out_dir = Path(kwargs["output_dir"])
        _write_replay(
            out_dir,
            summary={
                "total_steps": 7,
                "game_duration_seconds": 4.2,
                "vlm_cost_usd": 0.33,
            },
        )
        return {
            "cells_visited": 11,
            "termination_reason": "max_steps",
            "vlm_cost_usd": 0.33,
            "provider_status": {"provider_name": "mock"},
        }

    monkeypatch.setattr("roboclaws.regression._run_exploration", fake_run_exploration)
    metrics = _capture_explore_vlm(
        CaptureRequest(
            label="baseline-2026-04-23",
            scene="FloorPlan201",
            seed=1,
            agents=1,
            steps=5,
            model="mock",
        ),
        tmp_path / "explore",
    )

    assert metrics["cells_visited"] == 11
    assert metrics["total_steps"] == 7
    assert metrics["wallclock_seconds"] == 4.2
    assert seen_kwargs["provider_seed"] == 1


def test_openclaw_demo_suite_recovers_visited_cells_from_replay(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_run_demo(**kwargs):
        out_dir = Path(kwargs["output_dir"])
        _write_replay(
            out_dir,
            summary={"total_steps": 6, "game_duration_seconds": 8.5, "vlm_cost_usd": 0.0},
            final_game_state={"visited_cells": 14},
        )
        return {
            "steps_executed": 6,
            "termination_reason": "stale",
            "provider_status": {"provider_name": "openclaw", "model": "openclaw/agent-0"},
        }

    monkeypatch.setattr("roboclaws.regression._run_openclaw_demo", fake_run_demo)
    metrics = _capture_openclaw_demo(
        CaptureRequest(
            label="baseline-2026-04-23",
            scene="FloorPlan201",
            seed=1,
            agents=2,
            steps=5,
            model="ignored",
            allow_local=True,
        ),
        tmp_path / "openclaw-demo",
    )

    assert metrics["visited_cells"] == 14
    assert metrics["steps_executed"] == 6
    assert metrics["model"] == "openclaw/agent-0"


def test_openclaw_autonomous_suite_extracts_structured_summary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen_kwargs: dict[str, object] = {}

    def fake_run_autonomous(**kwargs):
        seen_kwargs.update(kwargs)
        out_dir = Path(kwargs["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "run_result.json").write_text(
            json.dumps(
                {
                    "terminated_by": "done",
                    "wallclock_s": 12.5,
                    "transcript_source": "terminal-body",
                    "view_variant": "map-v2+chase",
                    "model": "mimo_openai/mimo-v2.5-pro",
                }
            ),
            encoding="utf-8",
        )
        (out_dir / "summary.json").write_text(
            json.dumps(
                {
                    "tool_calls_by_type": {"observe": 3, "move": 2, "done": 1},
                    "frames_unseen_by_agent": 1,
                    "decision_modes": {"fresh_observe": 1, "reasoned_batch": 1, "blind_batch": 0},
                    "wallclock_seconds": 12.5,
                    "transcript_source": "terminal-body",
                    "view_variant": "map-v2+chase",
                }
            ),
            encoding="utf-8",
        )
        return {"terminated_by": "done"}

    monkeypatch.setattr("roboclaws.regression._run_autonomous_navigation", fake_run_autonomous)
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "token-123")
    metrics = _capture_openclaw_autonomous(
        CaptureRequest(
            label="baseline-2026-04-23",
            scene="FloorPlan201",
            seed=1,
            agents=1,
            steps=5,
            model="mock",
            allow_local=True,
        ),
        tmp_path / "openclaw-autonomous",
    )

    assert metrics["terminated_by"] == "done"
    assert metrics["transcript_source"] == "terminal-body"
    assert metrics["tool_calls_by_type"]["move"] == 2
    assert metrics["frames_unseen_by_agent"] == 1
    assert seen_kwargs["skip_bootstrap"] is True


def test_openclaw_autonomous_capture_raises_on_error_termination(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_run_autonomous(**kwargs):
        out_dir = Path(kwargs["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "run_result.json").write_text(
            json.dumps(
                {
                    "terminated_by": "error",
                    "final_message": "Gateway protocol error",
                    "wallclock_s": 40.0,
                    "view_variant": "map-v2+chase",
                }
            ),
            encoding="utf-8",
        )
        (out_dir / "summary.json").write_text(
            json.dumps(
                {
                    "tool_calls_by_type": {"observe": 0, "move": 0, "done": 0},
                    "frames_unseen_by_agent": 0,
                    "decision_modes": {
                        "fresh_observe": 0,
                        "reasoned_batch": 0,
                        "blind_batch": 0,
                    },
                    "wallclock_seconds": 40.0,
                    "transcript_source": "none",
                    "view_variant": "baseline",
                }
            ),
            encoding="utf-8",
        )
        return {"terminated_by": "error"}

    monkeypatch.setattr("roboclaws.regression._run_autonomous_navigation", fake_run_autonomous)

    with pytest.raises(Exception, match="terminated_by=error"):
        _capture_openclaw_autonomous(
            CaptureRequest(
                label="baseline-2026-04-23",
                scene="FloorPlan201",
                seed=1,
                agents=1,
                steps=5,
                model="mock",
                allow_local=True,
            ),
            tmp_path / "openclaw-autonomous-error",
        )
