"""Tests for examples/coverage_game.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from roboclaws.core.vlm import ProviderHealthError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))

from coverage_game import (  # noqa: E402
    _draw_progression_chart,
    _parse_args,
    _pos_to_world_idx,
    run_coverage_game,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

FRAME_SHAPE = (48, 64, 3)


def _make_frame(value: int = 128) -> np.ndarray:
    return np.full(FRAME_SHAPE, value, dtype=np.uint8)


def _make_agent_state(agent_id: int, x: float = 0.0, z: float = 0.0) -> MagicMock:
    s = MagicMock()
    s.agent_id = agent_id
    s.frame = _make_frame()
    s.position = {"x": x, "y": 0.9, "z": z}
    s.rotation = {"x": 0.0, "y": 0.0, "z": 0.0}
    s.last_action_success = True
    s.last_action_error = ""
    return s


# ---------------------------------------------------------------------------
# Unit: _parse_args
# ---------------------------------------------------------------------------


def test_parse_args_defaults() -> None:
    args = _parse_args([])
    assert args.scene == "FloorPlan201"
    assert args.agents == 2
    assert args.steps == 200
    assert args.model == "mock"
    assert args.output_dir == "output/coverage"
    assert args.thor_server_timeout == 100.0
    assert args.thor_server_start_timeout == 300.0
    assert args.backend == "vlm"
    assert args.gateway_url is None


def test_parse_args_backend_openclaw() -> None:
    args = _parse_args(["--backend", "openclaw"])
    assert args.backend == "openclaw"


def test_parse_args_backend_direct_accepted() -> None:
    """'direct' is a deprecated alias for 'vlm'; parser must accept it."""
    args = _parse_args(["--backend", "direct"])
    assert args.backend == "direct"


def test_parse_args_gateway_url() -> None:
    args = _parse_args(["--backend", "openclaw", "--gateway-url", "http://custom:9999"])
    assert args.gateway_url == "http://custom:9999"


def test_parse_args_custom() -> None:
    args = _parse_args(
        [
            "--scene",
            "FloorPlan205",
            "--agents",
            "3",
            "--steps",
            "50",
            "--model",
            "gpt-4o-mini",
            "--output-dir",
            "/tmp/coverage",
            "--thor-server-timeout",
            "240",
            "--thor-server-start-timeout",
            "420",
        ]
    )
    assert args.scene == "FloorPlan205"
    assert args.agents == 3
    assert args.steps == 50
    assert args.model == "gpt-4o-mini"
    assert args.output_dir == "/tmp/coverage"
    assert args.thor_server_timeout == 240.0
    assert args.thor_server_start_timeout == 420.0


# ---------------------------------------------------------------------------
# Unit: coordinate helpers
# ---------------------------------------------------------------------------


def test_pos_to_world_idx_origin() -> None:
    assert _pos_to_world_idx({"x": 0.0, "y": 0.9, "z": 0.0}) == (0, 0)


def test_pos_to_world_idx_positive() -> None:
    assert _pos_to_world_idx({"x": 0.50, "y": 0.9, "z": 0.75}) == (2, 3)


def test_pos_to_world_idx_negative() -> None:
    assert _pos_to_world_idx({"x": -0.25, "y": 0.9, "z": -0.50}) == (-1, -2)


# ---------------------------------------------------------------------------
# Unit: _draw_progression_chart
# ---------------------------------------------------------------------------


def test_draw_progression_chart_creates_file(tmp_path: Path) -> None:
    out = tmp_path / "chart.png"
    _draw_progression_chart([0, 1, 2, 3, 4], out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_draw_progression_chart_empty_list(tmp_path: Path) -> None:
    out = tmp_path / "chart.png"
    _draw_progression_chart([], out)
    assert out.exists()


def test_draw_progression_chart_single_value(tmp_path: Path) -> None:
    out = tmp_path / "chart.png"
    _draw_progression_chart([5], out)
    assert out.exists()


# ---------------------------------------------------------------------------
# Integration fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_engine_cls():
    """Patch MultiAgentEngine to avoid launching AI2-THOR."""
    with patch("coverage_game.MultiAgentEngine") as MockCls:
        inst = MockCls.return_value
        inst.agent_count = 2

        a0 = _make_agent_state(0, x=0.0)
        a1 = _make_agent_state(1, x=0.25)

        inst.get_all_agent_states.return_value = [a0, a1]
        inst.get_overhead_frame.return_value = _make_frame(80)
        inst.get_agent_state.side_effect = lambda aid: [a0, a1][aid]
        inst.step.side_effect = lambda agent_id, action, **kw: [a0, a1][agent_id]
        inst.add_chase_cam.return_value = 0
        inst.update_chase_cam.return_value = None
        inst.get_chase_cam_frame.return_value = _make_frame(60)
        # Large reachable set so 2 covered cells don't immediately hit 95% target
        inst.get_reachable_positions.return_value = {(i, j) for i in range(20) for j in range(20)}

        yield MockCls


# ---------------------------------------------------------------------------
# Integration: run_coverage_game with mocked engine
# ---------------------------------------------------------------------------


def test_run_returns_summary(mock_engine_cls, tmp_path: Path) -> None:
    result = run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=10,
        model="mock",
        output_dir=str(tmp_path / "coverage"),
    )
    assert isinstance(result, dict)
    assert "cells_covered" in result
    assert "contribution" in result
    assert "work_balance" in result
    assert "termination_reason" in result
    assert "vlm_cost_usd" in result
    assert "output_dir" in result


def test_run_contribution_has_all_agents(mock_engine_cls, tmp_path: Path) -> None:
    result = run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=10,
        model="mock",
        output_dir=str(tmp_path / "coverage"),
    )
    assert 0 in result["contribution"]
    assert 1 in result["contribution"]


def test_run_cost_is_zero_for_mock(mock_engine_cls, tmp_path: Path) -> None:
    result = run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=10,
        model="mock",
        output_dir=str(tmp_path / "coverage"),
    )
    assert result["vlm_cost_usd"] == 0.0


def test_run_work_balance_in_range(mock_engine_cls, tmp_path: Path) -> None:
    result = run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=10,
        model="mock",
        output_dir=str(tmp_path / "coverage"),
    )
    assert 0.0 <= result["work_balance"] <= 1.0


def test_run_creates_replay_json(mock_engine_cls, tmp_path: Path) -> None:
    out_dir = tmp_path / "coverage"
    run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=6,
        model="mock",
        output_dir=str(out_dir),
    )
    assert (out_dir / "replay.json").exists()


def test_run_creates_coverage_final_png(mock_engine_cls, tmp_path: Path) -> None:
    out_dir = tmp_path / "coverage"
    run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=6,
        model="mock",
        output_dir=str(out_dir),
    )
    assert (out_dir / "coverage_final.png").exists()


def test_run_creates_progression_chart(mock_engine_cls, tmp_path: Path) -> None:
    out_dir = tmp_path / "coverage"
    run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=6,
        model="mock",
        output_dir=str(out_dir),
    )
    assert (out_dir / "coverage_progression.png").exists()


def test_run_creates_work_balance_json(mock_engine_cls, tmp_path: Path) -> None:
    out_dir = tmp_path / "coverage"
    run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=6,
        model="mock",
        output_dir=str(out_dir),
    )
    assert (out_dir / "work_balance.json").exists()


def test_run_work_balance_json_content(mock_engine_cls, tmp_path: Path) -> None:
    out_dir = tmp_path / "coverage"
    run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=6,
        model="mock",
        output_dir=str(out_dir),
    )
    data = json.loads((out_dir / "work_balance.json").read_text())
    assert "cells_covered" in data
    assert "work_balance" in data
    assert "contribution" in data
    assert "termination_reason" in data


def test_run_engine_closed_on_completion(mock_engine_cls, tmp_path: Path) -> None:
    run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=6,
        model="mock",
        output_dir=str(tmp_path / "coverage"),
    )
    mock_engine_cls.return_value.close.assert_called_once()


def test_run_engine_closed_on_keyboard_interrupt(mock_engine_cls, tmp_path: Path) -> None:
    """engine.close() is called even when the game loop is interrupted."""
    inst = mock_engine_cls.return_value
    a0 = _make_agent_state(0, x=0.0)
    a1 = _make_agent_state(1, x=0.25)
    # Call order: (1) CoverageGame.__init__, (2) initial_states inside try, (3) loop → interrupt
    inst.get_all_agent_states.side_effect = [[a0, a1], [a0, a1], KeyboardInterrupt]
    run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=10,
        model="mock",
        output_dir=str(tmp_path / "coverage"),
    )
    inst.close.assert_called_once()


def test_run_termination_reason_valid(mock_engine_cls, tmp_path: Path) -> None:
    result = run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=10,
        model="mock",
        output_dir=str(tmp_path / "coverage"),
    )
    assert result["termination_reason"] in ("max_steps", "coverage_reached")


def test_run_passes_timeout_settings_to_engine(mock_engine_cls, tmp_path: Path) -> None:
    run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=1,
        model="mock",
        output_dir=str(tmp_path / "coverage"),
        thor_server_timeout=240.0,
        thor_server_start_timeout=420.0,
    )
    mock_engine_cls.assert_called()
    kwargs = mock_engine_cls.call_args.kwargs
    assert kwargs["server_timeout"] == 240.0
    assert kwargs["server_start_timeout"] == 420.0


def test_run_passes_three_images_to_provider(mock_engine_cls, tmp_path: Path) -> None:
    class SpyProvider:
        cumulative_cost = 0.0

        def __init__(self) -> None:
            self.calls: list[tuple[list[str], dict]] = []

        def get_action(self, images, state):
            self.calls.append((images, state))
            return {"reasoning": "scan the frontier", "action": "RotateRight"}

    spy = SpyProvider()
    with patch("coverage_game.create_provider", return_value=spy):
        run_coverage_game(
            scene="FloorPlan201",
            agent_count=2,
            steps=1,
            model="mock",
            output_dir=str(tmp_path / "coverage"),
        )
    assert len(spy.calls) == 1
    images, state = spy.calls[0]
    assert len(images) == 3
    assert all(images)
    assert state["my_agent_id"] == 0


def test_run_replay_records_real_vlm_response(mock_engine_cls, tmp_path: Path) -> None:
    class SpyProvider:
        cumulative_cost = 0.0

        def get_action(self, images, state):
            return {"reasoning": "scan the frontier", "action": "RotateRight"}

    out_dir = tmp_path / "coverage"
    with patch("coverage_game.create_provider", return_value=SpyProvider()):
        run_coverage_game(
            scene="FloorPlan201",
            agent_count=2,
            steps=1,
            model="mock",
            output_dir=str(out_dir),
        )
    replay = json.loads((out_dir / "replay.json").read_text())
    first_step = replay["steps"][0]
    assert first_step["vlm_response"]["reasoning"] == "scan the frontier"
    assert first_step["vlm_response"]["action"] == "RotateRight"


def test_run_replay_records_turn_metrics(mock_engine_cls, tmp_path: Path) -> None:
    out_dir = tmp_path / "coverage"
    run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=1,
        model="mock",
        output_dir=str(out_dir),
    )
    replay = json.loads((out_dir / "replay.json").read_text())
    metrics = replay["steps"][0]["turn_metrics"]
    assert metrics["timings"]["provider_call_seconds"] >= 0.0
    assert metrics["timings"]["step_loop_seconds"] >= 0.0
    assert metrics["payload"]["image_count"] == 3
    assert metrics["payload"]["state_json_chars"] > 0


def test_run_stops_cleanly_on_provider_health_error(mock_engine_cls, tmp_path: Path) -> None:
    class FailingProvider:
        cumulative_cost = 0.0
        model = "kimi-k2-5"

        def get_status(self):
            return {
                "provider_name": "kimi",
                "model": self.model,
                "retry_events": 4,
                "transient_errors": 8,
                "failed_calls": 1,
                "stop_reason": "transient_error_budget_exceeded",
            }

        def get_action(self, images, state):
            raise ProviderHealthError("kimi became unstable", status=self.get_status())

    out_dir = tmp_path / "coverage"
    with patch("coverage_game.create_provider", return_value=FailingProvider()):
        result = run_coverage_game(
            scene="FloorPlan201",
            agent_count=2,
            steps=3,
            model="mock",
            output_dir=str(out_dir),
        )
    replay = json.loads((out_dir / "replay.json").read_text())
    assert result["termination_reason"] == "provider_unstable"
    assert replay["summary"]["provider_status"]["stop_reason"] == "transient_error_budget_exceeded"


def test_run_three_agents(tmp_path: Path) -> None:
    """Three-agent game runs to completion without error."""
    with patch("coverage_game.MultiAgentEngine") as MockCls:
        inst = MockCls.return_value
        inst.agent_count = 3
        agents = [_make_agent_state(i, x=i * 0.25) for i in range(3)]
        inst.get_all_agent_states.return_value = agents
        inst.get_overhead_frame.return_value = _make_frame(80)
        inst.get_agent_state.side_effect = lambda aid: agents[aid]
        inst.step.side_effect = lambda agent_id, action, **kw: agents[agent_id]
        inst.add_chase_cam.return_value = 0
        inst.update_chase_cam.return_value = None
        inst.get_chase_cam_frame.return_value = _make_frame(60)
        inst.get_reachable_positions.return_value = {(i, j) for i in range(20) for j in range(20)}

        result = run_coverage_game(
            scene="FloorPlan201",
            agent_count=3,
            steps=10,
            model="mock",
            output_dir=str(tmp_path / "coverage3"),
        )
    assert len(result["contribution"]) == 3
    assert result["termination_reason"] in ("max_steps", "coverage_reached")


# ---------------------------------------------------------------------------
# OpenClaw backend: construction + numpy frame type contract
# ---------------------------------------------------------------------------


def test_backend_openclaw_constructs_provider(mock_engine_cls, tmp_path: Path) -> None:
    """When backend='openclaw', build_openclaw_provider_or_die is called."""

    class StubProvider:
        cumulative_cost = 0.0

        def get_action(self, images, state):
            return {"reasoning": "scan", "action": "RotateRight"}

    with patch(
        "roboclaws.openclaw.bridge.build_openclaw_provider_or_die",
        return_value=StubProvider(),
    ) as mock_build:
        run_coverage_game(
            scene="FloorPlan201",
            agent_count=2,
            steps=1,
            model="mock",
            output_dir=str(tmp_path / "coverage"),
            backend="openclaw",
        )
    mock_build.assert_called_once()


def test_backend_openclaw_passes_numpy_frames(mock_engine_cls, tmp_path: Path) -> None:
    """When backend='openclaw', images passed to provider are numpy arrays, not base64 strings."""

    class SpyProvider:
        cumulative_cost = 0.0

        def __init__(self) -> None:
            self.calls: list[list] = []

        def get_action(self, images, state):
            self.calls.append(images)
            return {"reasoning": "scan", "action": "RotateRight"}

    spy = SpyProvider()
    with patch(
        "roboclaws.openclaw.bridge.build_openclaw_provider_or_die",
        return_value=spy,
    ):
        run_coverage_game(
            scene="FloorPlan201",
            agent_count=2,
            steps=1,
            model="mock",
            output_dir=str(tmp_path / "coverage"),
            backend="openclaw",
        )
    assert len(spy.calls) == 1
    for img in spy.calls[0]:
        assert isinstance(img, np.ndarray), f"expected ndarray, got {type(img)}"


def test_run_uses_shared_prompt_image_renderer(mock_engine_cls, tmp_path: Path) -> None:
    class SpyProvider:
        cumulative_cost = 0.0

        def __init__(self) -> None:
            self.calls: list[list[np.ndarray]] = []

        def get_action(self, images, state):
            self.calls.append(images)
            return {"reasoning": "scan", "action": "RotateRight"}

    spy = SpyProvider()
    fake_bundle = MagicMock()
    fake_bundle.prompt_images = [_make_frame(12), _make_frame(23), _make_frame(34)]
    fake_bundle.trace_overhead_frame = _make_frame(23)
    fake_bundle.raw_overhead_frame = _make_frame(45)
    fake_bundle.image_labels = ("fpv", "map_v2", "chase")
    fake_bundle.agent_positions_world = [(0, 0), (1, 0)]
    fake_bundle.structured_overhead_frame = fake_bundle.trace_overhead_frame
    fake_bundle.chase_cam_frame = fake_bundle.prompt_images[2]

    with patch(
        "roboclaws.openclaw.bridge.build_openclaw_provider_or_die",
        return_value=spy,
    ):
        with patch("coverage_game.render_game_prompt_bundle", return_value=fake_bundle):
            run_coverage_game(
                scene="FloorPlan201",
                agent_count=2,
                steps=1,
                model="mock",
                output_dir=str(tmp_path / "coverage"),
                backend="openclaw",
            )

    assert len(spy.calls) == 1
    assert [int(frame[0, 0, 0]) for frame in spy.calls[0]] == [12, 23, 34]


def test_backend_openclaw_replay_records_provider_turn_metrics(
    mock_engine_cls, tmp_path: Path
) -> None:
    class SpyProvider:
        cumulative_cost = 0.0

        def get_action(self, images, state):
            return {"reasoning": "scan", "action": "RotateRight"}

        def get_last_turn_metrics(self):
            return {
                "timings": {"openclaw_gateway_request_seconds": 42.0},
                "payload": {"image_count": 3, "transport": "openclaw_data_url"},
                "provider": {"attempts": 1},
            }

    out_dir = tmp_path / "coverage"
    with patch(
        "roboclaws.openclaw.bridge.build_openclaw_provider_or_die",
        return_value=SpyProvider(),
    ):
        run_coverage_game(
            scene="FloorPlan201",
            agent_count=2,
            steps=1,
            model="mock",
            output_dir=str(out_dir),
            backend="openclaw",
        )
    replay = json.loads((out_dir / "replay.json").read_text())
    metrics = replay["steps"][0]["turn_metrics"]
    assert metrics["timings"]["openclaw_gateway_request_seconds"] == pytest.approx(42.0)
    assert metrics["payload"]["transport"] == "openclaw_data_url"
