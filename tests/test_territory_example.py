"""Tests for examples/territory_game.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from roboclaws.core.vlm import ProviderHealthError
from tests.support import game_fakes

configure_example_engine_instance = game_fakes.configure_example_engine_instance
_make_agent_state = game_fakes.make_example_agent_state
_make_frame = game_fakes.make_example_frame

# Make the examples directory importable without a package install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))

from territory_game import (  # noqa: E402
    _parse_args,
    run_territory_game,
)

# ---------------------------------------------------------------------------
# Unit: _parse_args
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (
            [],
            {
                "scene": "FloorPlan201",
                "agents": 2,
                "steps": 200,
                "model": "mock",
                "output_dir": "output/territory",
                "thor_server_timeout": 100.0,
                "thor_server_start_timeout": 300.0,
                "backend": "vlm",
                "gateway_url": None,
            },
        ),
        (["--backend", "openclaw"], {"backend": "openclaw"}),
        (["--backend", "direct"], {"backend": "direct"}),
        (
            ["--backend", "openclaw", "--gateway-url", "http://custom:9999"],
            {"backend": "openclaw", "gateway_url": "http://custom:9999"},
        ),
        (
            [
                "--scene",
                "FloorPlan202",
                "--agents",
                "3",
                "--steps",
                "50",
                "--model",
                "gpt-4o-mini",
                "--output-dir",
                "/tmp/territory",
                "--thor-server-timeout",
                "240",
                "--thor-server-start-timeout",
                "420",
            ],
            {
                "scene": "FloorPlan202",
                "agents": 3,
                "steps": 50,
                "model": "gpt-4o-mini",
                "output_dir": "/tmp/territory",
                "thor_server_timeout": 240.0,
                "thor_server_start_timeout": 420.0,
            },
        ),
    ],
)
def test_parse_args(argv: list[str], expected: dict[str, object]) -> None:
    args = _parse_args(argv)
    assert {name: getattr(args, name) for name in expected} == expected


# ---------------------------------------------------------------------------
# Integration fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_engine_cls():
    """Patch MultiAgentEngine to avoid launching AI2-THOR."""
    with patch("territory_game.MultiAgentEngine") as MockCls:
        configure_example_engine_instance(MockCls.return_value)
        yield MockCls


# ---------------------------------------------------------------------------
# Integration: run_territory_game with mocked engine
# ---------------------------------------------------------------------------


def test_run_returns_summary_for_mock_provider(mock_engine_cls, tmp_path: Path) -> None:
    result = run_territory_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=10,
        model="mock",
        output_dir=str(tmp_path / "territory"),
    )
    assert isinstance(result, dict)
    assert "cells_claimed" in result
    assert "blocking_events" in result
    assert "termination_reason" in result
    assert "vlm_cost_usd" in result
    assert "output_dir" in result
    assert 0 in result["cells_claimed"]
    assert 1 in result["cells_claimed"]
    assert result["vlm_cost_usd"] == 0.0


def test_run_persists_replay_and_final_map(mock_engine_cls, tmp_path: Path) -> None:
    out_dir = tmp_path / "territory"
    run_territory_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=6,
        model="mock",
        output_dir=str(out_dir),
    )
    assert (out_dir / "replay.json").exists()
    assert (out_dir / "territory_final.png").exists()


def test_run_engine_closed_on_completion(mock_engine_cls, tmp_path: Path) -> None:
    run_territory_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=6,
        model="mock",
        output_dir=str(tmp_path / "territory"),
    )
    mock_engine_cls.return_value.close.assert_called_once()


def test_run_engine_closed_on_keyboard_interrupt(mock_engine_cls, tmp_path: Path) -> None:
    """engine.close() is called even when the game loop is interrupted."""
    inst = mock_engine_cls.return_value
    a0 = _make_agent_state(0, x=0.0)
    a1 = _make_agent_state(1, x=0.25)
    # Call order: (1) TerritoryGame.__init__, (2) initial_states inside try → interrupt
    inst.get_all_agent_states.side_effect = [[a0, a1], [a0, a1], KeyboardInterrupt]
    run_territory_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=10,
        model="mock",
        output_dir=str(tmp_path / "territory"),
    )
    inst.close.assert_called_once()


def test_run_termination_reason_valid(mock_engine_cls, tmp_path: Path) -> None:
    result = run_territory_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=10,
        model="mock",
        output_dir=str(tmp_path / "territory"),
    )
    assert result["termination_reason"] in ("max_steps", "all_cells_claimed", "stale")


def test_run_passes_timeout_settings_to_engine(mock_engine_cls, tmp_path: Path) -> None:
    run_territory_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=1,
        model="mock",
        output_dir=str(tmp_path / "territory"),
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
            return {"reasoning": "move", "action": "MoveAhead"}

    spy = SpyProvider()
    with patch("roboclaws.core.game_run.create_provider", return_value=spy):
        run_territory_game(
            scene="FloorPlan201",
            agent_count=2,
            steps=1,
            model="mock",
            output_dir=str(tmp_path / "territory"),
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
            return {"reasoning": "claim fresh ground", "action": "MoveAhead"}

    out_dir = tmp_path / "territory"
    with patch("roboclaws.core.game_run.create_provider", return_value=SpyProvider()):
        run_territory_game(
            scene="FloorPlan201",
            agent_count=2,
            steps=1,
            model="mock",
            output_dir=str(out_dir),
        )
    replay = json.loads((out_dir / "replay.json").read_text())
    first_step = replay["steps"][0]
    assert first_step["vlm_response"]["reasoning"] == "claim fresh ground"
    assert first_step["vlm_response"]["action"] == "MoveAhead"


def test_run_replay_records_turn_metrics(mock_engine_cls, tmp_path: Path) -> None:
    out_dir = tmp_path / "territory"
    run_territory_game(
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

    out_dir = tmp_path / "territory"
    with patch("roboclaws.core.game_run.create_provider", return_value=FailingProvider()):
        result = run_territory_game(
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
    with patch("territory_game.MultiAgentEngine") as MockCls:
        configure_example_engine_instance(MockCls.return_value, agent_count=3)

        result = run_territory_game(
            scene="FloorPlan201",
            agent_count=3,
            steps=10,
            model="mock",
            output_dir=str(tmp_path / "territory3"),
        )
    assert len(result["cells_claimed"]) == 3
    assert result["termination_reason"] in ("max_steps", "all_cells_claimed", "stale")


# ---------------------------------------------------------------------------
# OpenClaw backend: construction + numpy frame type contract
# ---------------------------------------------------------------------------


def test_backend_openclaw_constructs_provider(mock_engine_cls, tmp_path: Path) -> None:
    """When backend='openclaw', build_openclaw_provider_or_die is called."""

    class StubProvider:
        cumulative_cost = 0.0

        def get_action(self, images, state):
            return {"reasoning": "move", "action": "MoveAhead"}

    with patch(
        "roboclaws.openclaw.bridge.build_openclaw_provider_or_die",
        return_value=StubProvider(),
    ) as mock_build:
        run_territory_game(
            scene="FloorPlan201",
            agent_count=2,
            steps=1,
            model="mock",
            output_dir=str(tmp_path / "territory"),
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
            return {"reasoning": "move", "action": "MoveAhead"}

    spy = SpyProvider()
    with patch(
        "roboclaws.openclaw.bridge.build_openclaw_provider_or_die",
        return_value=spy,
    ):
        run_territory_game(
            scene="FloorPlan201",
            agent_count=2,
            steps=1,
            model="mock",
            output_dir=str(tmp_path / "territory"),
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
            return {"reasoning": "move", "action": "MoveAhead"}

    spy = SpyProvider()
    fake_bundle = MagicMock()
    fake_bundle.prompt_images = [_make_frame(11), _make_frame(22), _make_frame(33)]
    fake_bundle.trace_overhead_frame = _make_frame(22)
    fake_bundle.raw_overhead_frame = _make_frame(44)
    fake_bundle.image_labels = ("fpv", "map_v2", "chase")
    fake_bundle.agent_positions_world = [(0, 0), (1, 0)]
    fake_bundle.structured_overhead_frame = fake_bundle.trace_overhead_frame
    fake_bundle.chase_cam_frame = fake_bundle.prompt_images[2]

    with patch(
        "roboclaws.openclaw.bridge.build_openclaw_provider_or_die",
        return_value=spy,
    ):
        with patch("territory_game.render_game_prompt_bundle", return_value=fake_bundle):
            run_territory_game(
                scene="FloorPlan201",
                agent_count=2,
                steps=1,
                model="mock",
                output_dir=str(tmp_path / "territory"),
                backend="openclaw",
            )

    assert len(spy.calls) == 1
    assert [int(frame[0, 0, 0]) for frame in spy.calls[0]] == [11, 22, 33]


def test_backend_openclaw_replay_records_provider_turn_metrics(
    mock_engine_cls, tmp_path: Path
) -> None:
    class SpyProvider:
        cumulative_cost = 0.0

        def get_action(self, images, state):
            return {"reasoning": "move", "action": "MoveAhead"}

        def get_last_turn_metrics(self):
            return {
                "timings": {"openclaw_gateway_request_seconds": 42.0},
                "payload": {"image_count": 3, "transport": "openclaw_data_url"},
                "provider": {"attempts": 1},
            }

    out_dir = tmp_path / "territory"
    with patch(
        "roboclaws.openclaw.bridge.build_openclaw_provider_or_die",
        return_value=SpyProvider(),
    ):
        run_territory_game(
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
