from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from roboclaws.core.replay import ReplayRecorder
from roboclaws.core.reporter import (
    _build_svg_chart,
    _extract_metrics,
    _img_to_b64,
    compare,
    generate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_frame(h: int = 48, w: int = 64, value: int = 128) -> np.ndarray:
    return np.full((h, w, 3), value, dtype=np.uint8)


def _write_replay(
    tmp_path: Path,
    agent_count: int = 2,
    n_steps: int = 3,
    game: str = "territory",
) -> Path:
    """Create a minimal replay directory with replay.json and image files."""
    recorder = ReplayRecorder(agent_count=agent_count, game=game)

    def _gs(step: int) -> dict:
        if game == "territory":
            return {
                "game": "territory",
                "step": step,
                "remaining_steps": 100 - step,
                "current_agent": step % agent_count,
                "agents": {
                    str(i): {"position": {"x": 0.0, "y": 0.0, "z": 0.0}, "cells_claimed": step + i}
                    for i in range(agent_count)
                },
                "total_claimed": step * agent_count,
                "blocking_events": 0,
            }
        return {
            "game": game,
            "step": step,
            "remaining_steps": 100 - step,
            "score": step * 5,
        }

    for i in range(n_steps):
        recorder.record_step(
            step=i,
            agent_id=i % agent_count,
            agent_frames=[_make_frame(value=v * 20) for v in range(agent_count)],
            overhead_frame=_make_frame(value=50),
            game_state=_gs(i),
            vlm_prompt_state={"my_agent_id": i % agent_count, "step": i},
            vlm_response={"reasoning": "go ahead", "action": "MoveAhead"},
            provider_status={"provider_name": "kimi", "retry_events": i, "transient_errors": i},
        )

    replay_dir = recorder.save(
        tmp_path / "replay",
        vlm_cost_usd=0.001,
        final_scores={0: 10, 1: 8},
        termination_reason="max_steps",
        generate_gif=False,
        provider_status={"provider_name": "kimi", "retry_events": 2, "transient_errors": 2},
    )
    return replay_dir


# ---------------------------------------------------------------------------
# generate()
# ---------------------------------------------------------------------------


class TestGenerate:
    def test_creates_report_html(self, tmp_path: Path) -> None:
        replay_dir = _write_replay(tmp_path)
        out = generate(replay_dir)
        assert out.name == "report.html"
        assert out.exists()

    def test_report_is_non_empty(self, tmp_path: Path) -> None:
        replay_dir = _write_replay(tmp_path)
        out = generate(replay_dir)
        assert out.stat().st_size > 1000

    def test_report_contains_doctype(self, tmp_path: Path) -> None:
        replay_dir = _write_replay(tmp_path)
        content = generate(replay_dir).read_text()
        assert "<!DOCTYPE html>" in content

    def test_report_contains_summary_info(self, tmp_path: Path) -> None:
        replay_dir = _write_replay(tmp_path, game="territory")
        content = generate(replay_dir).read_text()
        assert "territory" in content
        assert "max_steps" in content

    def test_report_contains_step_slider(self, tmp_path: Path) -> None:
        replay_dir = _write_replay(tmp_path, n_steps=4)
        content = generate(replay_dir).read_text()
        assert 'type="range"' in content

    def test_report_contains_vlm_log(self, tmp_path: Path) -> None:
        replay_dir = _write_replay(tmp_path, n_steps=3)
        content = generate(replay_dir).read_text()
        assert "go ahead" in content
        assert "MoveAhead" in content

    def test_report_contains_provider_health(self, tmp_path: Path) -> None:
        replay_dir = _write_replay(tmp_path, n_steps=3)
        content = generate(replay_dir).read_text()
        assert "Provider Health" in content
        assert "Transient errors" in content
        assert "Provider status" in content

    def test_report_contains_decision_snapshot_panel(self, tmp_path: Path) -> None:
        replay_dir = _write_replay(tmp_path, n_steps=3)
        content = generate(replay_dir).read_text()
        assert "Latest Agent Decisions" in content
        assert "Acting this step (step 0)." in content
        assert "Chosen action:" in content
        assert "No decision recorded yet." in content

    def test_report_contains_svg_chart(self, tmp_path: Path) -> None:
        replay_dir = _write_replay(tmp_path, n_steps=5)
        content = generate(replay_dir).read_text()
        assert "<svg" in content
        assert "<polyline" in content

    def test_custom_output_path(self, tmp_path: Path) -> None:
        replay_dir = _write_replay(tmp_path)
        out = generate(replay_dir, output_path=tmp_path / "custom.html")
        assert out == tmp_path / "custom.html"
        assert out.exists()

    def test_missing_replay_json_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="replay.json"):
            generate(tmp_path / "nonexistent")

    def test_no_external_resources(self, tmp_path: Path) -> None:
        """The report must be self-contained — no links to external hosts."""
        replay_dir = _write_replay(tmp_path, n_steps=3)
        content = generate(replay_dir).read_text()
        # The only allowed http:// is the SVG namespace declaration.
        # Strip that and verify no other external references remain.
        stripped = content.replace('xmlns="http://www.w3.org/2000/svg"', "")
        assert "http://" not in stripped
        assert "https://" not in stripped

    def test_images_inlined_as_base64(self, tmp_path: Path) -> None:
        replay_dir = _write_replay(tmp_path, n_steps=2, agent_count=2)
        content = generate(replay_dir).read_text()
        assert "data:image/png;base64," in content

    def test_empty_steps_no_crash(self, tmp_path: Path) -> None:
        """A replay with zero steps should produce a valid (but thin) report."""
        # Write a minimal replay.json manually
        replay_dir = tmp_path / "empty_replay"
        replay_dir.mkdir()
        manifest = {
            "metadata": {
                "game": "territory",
                "agent_count": 2,
                "total_steps": 0,
                "duration_seconds": 0.0,
                "vlm_cost_usd": 0.0,
            },
            "summary": {
                "final_scores": {},
                "termination_reason": "unknown",
                "total_steps": 0,
                "vlm_cost_usd": 0.0,
                "step_count": 0,
                "game_duration_seconds": 0.0,
            },
            "steps": [],
        }
        (replay_dir / "replay.json").write_text(json.dumps(manifest))
        out = generate(replay_dir)
        assert out.exists()
        assert "<!DOCTYPE html>" in out.read_text()


# ---------------------------------------------------------------------------
# compare()
# ---------------------------------------------------------------------------


class TestCompare:
    def test_creates_report_compare_html(self, tmp_path: Path) -> None:
        dir_a = _write_replay(tmp_path / "a", game="territory")
        dir_b = _write_replay(tmp_path / "b", game="territory")
        out = compare(dir_a, dir_b)
        assert out.name == "report_compare.html"
        assert out.exists()

    def test_compare_contains_both_runs(self, tmp_path: Path) -> None:
        dir_a = _write_replay(tmp_path / "a", n_steps=2)
        dir_b = _write_replay(tmp_path / "b", n_steps=2)
        content = compare(dir_a, dir_b).read_text()
        assert "Run A" in content
        assert "Run B" in content

    def test_compare_self_contained(self, tmp_path: Path) -> None:
        dir_a = _write_replay(tmp_path / "a")
        dir_b = _write_replay(tmp_path / "b")
        content = compare(dir_a, dir_b).read_text()
        stripped = content.replace('xmlns="http://www.w3.org/2000/svg"', "")
        assert "http://" not in stripped
        assert "https://" not in stripped

    def test_compare_custom_output(self, tmp_path: Path) -> None:
        dir_a = _write_replay(tmp_path / "a")
        dir_b = _write_replay(tmp_path / "b")
        out = compare(dir_a, dir_b, output_path=tmp_path / "cmp.html")
        assert out == tmp_path / "cmp.html"
        assert out.exists()


# ---------------------------------------------------------------------------
# _extract_metrics
# ---------------------------------------------------------------------------


class TestExtractMetrics:
    def _make_territory_step(self, step: int, agent_count: int = 2) -> dict:
        return {
            "step": step,
            "agent_id": step % agent_count,
            "game_state": {
                "game": "territory",
                "step": step,
                "remaining_steps": 10 - step,
                "current_agent": step % agent_count,
                "agents": {str(i): {"cells_claimed": step + i} for i in range(agent_count)},
                "total_claimed": step * agent_count,
                "blocking_events": 0,
            },
            "vlm_prompt_state": {},
            "vlm_response": {},
        }

    def _make_coverage_step(self, step: int, agent_count: int = 2) -> dict:
        return {
            "step": step,
            "agent_id": step % agent_count,
            "game_state": {
                "game": "coverage",
                "step": step,
                "remaining_steps": 10 - step,
                "current_agent": step % agent_count,
                "agents": {str(i): {"cells_covered": step + i} for i in range(agent_count)},
                "total_covered": step * agent_count,
                "coverage_pct": float(step * 5),
            },
            "vlm_prompt_state": {},
            "vlm_response": {},
        }

    def test_territory_extracts_cells_claimed(self) -> None:
        steps = [self._make_territory_step(i) for i in range(3)]
        metrics = _extract_metrics(steps, agent_count=2)
        assert "agent_0_cells" in metrics
        assert "agent_1_cells" in metrics
        assert "total_claimed" in metrics
        assert len(metrics["agent_0_cells"]) == 3

    def test_territory_values_monotone(self) -> None:
        steps = [self._make_territory_step(i) for i in range(5)]
        metrics = _extract_metrics(steps, agent_count=2)
        vals = metrics["total_claimed"]
        assert vals == sorted(vals)

    def test_coverage_extracts_coverage_pct(self) -> None:
        steps = [self._make_coverage_step(i) for i in range(4)]
        metrics = _extract_metrics(steps, agent_count=2)
        assert "coverage_pct" in metrics
        assert "total_covered" in metrics
        assert len(metrics["coverage_pct"]) == 4

    def test_empty_steps_returns_empty(self) -> None:
        assert _extract_metrics([], agent_count=2) == {}

    def test_generic_extracts_numeric_fields(self) -> None:
        steps = [
            {
                "game_state": {"game": "custom", "score": float(i * 3), "extra": i},
                "vlm_prompt_state": {},
                "vlm_response": {},
            }
            for i in range(3)
        ]
        metrics = _extract_metrics(steps, agent_count=1)
        assert "score" in metrics
        assert metrics["score"] == [0.0, 3.0, 6.0]


# ---------------------------------------------------------------------------
# _build_svg_chart
# ---------------------------------------------------------------------------


class TestBuildSvgChart:
    def test_returns_svg_element(self) -> None:
        svg = _build_svg_chart({"score": [1.0, 2.0, 3.0]})
        assert svg.startswith("<svg")
        assert "polyline" in svg

    def test_empty_metrics_returns_p(self) -> None:
        result = _build_svg_chart({})
        assert result.startswith("<p")

    def test_single_point_series_skipped(self) -> None:
        result = _build_svg_chart({"score": [5.0]})
        assert result.startswith("<p")

    def test_multiple_series(self) -> None:
        svg = _build_svg_chart({"a": [1.0, 2.0], "b": [3.0, 4.0]})
        # Two polylines expected
        assert svg.count("<polyline") == 2

    def test_legend_labels_present(self) -> None:
        svg = _build_svg_chart({"my_metric": [0.0, 10.0, 20.0]})
        assert "my_metric" in svg

    def test_equal_values_no_crash(self) -> None:
        svg = _build_svg_chart({"flat": [5.0, 5.0, 5.0]})
        assert "<svg" in svg


# ---------------------------------------------------------------------------
# _img_to_b64
# ---------------------------------------------------------------------------


class TestImgToB64:
    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        assert _img_to_b64(tmp_path / "nope.png") == ""

    def test_existing_file_returns_data_uri(self, tmp_path: Path) -> None:
        p = tmp_path / "img.png"
        Image.fromarray(np.zeros((8, 8, 3), dtype=np.uint8)).save(str(p))
        result = _img_to_b64(p)
        assert result.startswith("data:image/png;base64,")
        assert len(result) > 30


# ---------------------------------------------------------------------------
# ReplayRecorder.save() integration (generate_report flag)
# ---------------------------------------------------------------------------


class TestReplayRecorderReportIntegration:
    def test_generate_report_false_no_html(self, tmp_path: Path) -> None:
        recorder = ReplayRecorder(agent_count=1, game="test")
        recorder.record_step(
            step=0,
            agent_id=0,
            agent_frames=[_make_frame()],
            overhead_frame=_make_frame(value=20),
            game_state={"game": "test", "step": 0},
            vlm_prompt_state={},
            vlm_response={"action": "Stop"},
        )
        out_dir = recorder.save(tmp_path / "run", generate_gif=False, generate_report=False)
        assert not (out_dir / "report.html").exists()

    def test_generate_report_true_creates_html(self, tmp_path: Path) -> None:
        recorder = ReplayRecorder(agent_count=1, game="test")
        recorder.record_step(
            step=0,
            agent_id=0,
            agent_frames=[_make_frame()],
            overhead_frame=_make_frame(value=20),
            game_state={"game": "test", "step": 0},
            vlm_prompt_state={},
            vlm_response={"action": "Stop"},
        )
        out_dir = recorder.save(tmp_path / "run", generate_gif=False, generate_report=True)
        assert (out_dir / "report.html").exists()
