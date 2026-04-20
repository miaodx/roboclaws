"""Tests for examples/openclaw_demo.py — auto-convergence and step-budget semantics.

The real demo talks to a live OpenClaw Gateway.  These tests mock both the
Gateway provider and the AI2-THOR engine so the loop logic can be exercised
without Docker, Unity, or an upstream VLM call.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))

from openclaw_demo import _parse_args, run_openclaw_demo  # noqa: E402

FRAME_SHAPE = (48, 64, 3)


def _make_frame(value: int = 128) -> np.ndarray:
    return np.full(FRAME_SHAPE, value, dtype=np.uint8)


def _make_agent_state(x: float = 0.0, z: float = 0.0) -> MagicMock:
    s = MagicMock()
    s.frame = _make_frame()
    s.position = {"x": x, "y": 0.9, "z": z}
    s.rotation = {"x": 0.0, "y": 0.0, "z": 0.0}
    s.last_action_success = True
    s.last_action_error = ""
    return s


# ---------------------------------------------------------------------------
# CLI defaults — pinning 200 so CI + local don't silently drift apart
# ---------------------------------------------------------------------------


def test_parse_args_default_steps_is_200() -> None:
    args = _parse_args([])
    assert args.steps == 200


def test_parse_args_default_stale_is_none() -> None:
    args = _parse_args([])
    assert args.max_stale_steps is None


def test_parse_args_stale_override() -> None:
    args = _parse_args(["--max-stale-steps", "8"])
    assert args.max_stale_steps == 8


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_engine_and_provider():
    """Patch OpenClawProvider + MultiAgentEngine so the loop runs offline."""
    with (
        patch("openclaw_demo.OpenClawProvider") as ProviderCls,
        patch("openclaw_demo.MultiAgentEngine") as EngineCls,
    ):
        provider = ProviderCls.return_value
        provider.ping.return_value = "PONG"
        provider.get_action.return_value = {
            "reasoning": "mock",
            "action": "MoveAhead",
        }
        provider.cumulative_cost = 0.0
        # provider_status_snapshot() calls get_status() and its return must be
        # JSON-serializable (replay.json).  A plain dict keeps MagicMock out of
        # the status payload.
        provider.get_status.return_value = {
            "provider_name": "openclaw",
            "model": "mock/agent",
            "total_calls": 0,
            "successful_calls": 0,
            "retry_events": 0,
            "transient_errors": 0,
            "failed_calls": 0,
            "stop_reason": None,
        }

        engine = EngineCls.return_value
        engine.get_overhead_frame.return_value = _make_frame(40)
        engine.agent_count = 2

        # Default: agents stand still (same position every call) so the
        # visited_world never grows after the first step → stale fires fast.
        stuck_states = [_make_agent_state(0.0, 0.0), _make_agent_state(0.25, 0.0)]
        engine.get_all_agent_states.return_value = stuck_states
        engine.step.return_value = MagicMock()

        yield {
            "ProviderCls": ProviderCls,
            "EngineCls": EngineCls,
            "provider": provider,
            "engine": engine,
        }


# ---------------------------------------------------------------------------
# Auto-convergence behaviour
# ---------------------------------------------------------------------------


def test_stuck_agents_trigger_stale_termination(
    mock_engine_and_provider: dict[str, Any], tmp_path: Path
) -> None:
    """Two agents that never reach a new cell should terminate on 'stale'
    well before the step budget, with stale_steps == 3*agent_count (the
    default threshold)."""
    result = run_openclaw_demo(
        scene="FloorPlan201",
        agent_count=2,
        steps=200,
        output_dir=str(tmp_path / "demo"),
    )
    assert result["termination_reason"] == "stale"
    # 3*agent_count = 6; plus the first step which *does* add cells.
    # So the loop exits somewhere between step ~2 and step ~10, certainly
    # far below the 200-step cap.
    assert result["steps_executed"] < 20


def test_stale_disabled_runs_full_budget(
    mock_engine_and_provider: dict[str, Any], tmp_path: Path
) -> None:
    """--max-stale-steps=0 disables auto-convergence; loop runs to max."""
    result = run_openclaw_demo(
        scene="FloorPlan201",
        agent_count=2,
        steps=15,
        output_dir=str(tmp_path / "demo"),
        max_stale_steps=0,
    )
    assert result["termination_reason"] == "max_steps"
    assert result["steps_executed"] == 15


def test_growing_coverage_runs_full_budget(
    mock_engine_and_provider: dict[str, Any], tmp_path: Path
) -> None:
    """When agents visit a new cell every step, stale never fires and the
    demo uses the full step budget."""
    engine = mock_engine_and_provider["engine"]
    # Build a lazy generator that yields ever-new positions per call
    call = {"n": 0}

    def new_states(*_args: Any, **_kw: Any):
        call["n"] += 1
        return [
            _make_agent_state(call["n"] * 0.25, 0.0),
            _make_agent_state(0.0, call["n"] * 0.25),
        ]

    engine.get_all_agent_states.side_effect = new_states

    result = run_openclaw_demo(
        scene="FloorPlan201",
        agent_count=2,
        steps=12,
        output_dir=str(tmp_path / "demo"),
    )
    assert result["termination_reason"] == "max_steps"
    assert result["steps_executed"] == 12


def test_custom_stale_threshold_is_respected(
    mock_engine_and_provider: dict[str, Any], tmp_path: Path
) -> None:
    """Explicit --max-stale-steps=2 fires faster than the default 3*agents."""
    result = run_openclaw_demo(
        scene="FloorPlan201",
        agent_count=2,
        steps=200,
        output_dir=str(tmp_path / "demo"),
        max_stale_steps=2,
    )
    assert result["termination_reason"] == "stale"
    # With threshold=2 and stuck agents, loop exits within a handful of steps.
    assert result["steps_executed"] <= 10


def test_provider_ping_failure_exits(tmp_path: Path) -> None:
    """If the Gateway probe fails, the demo raises SystemExit (don't boot Unity)."""
    from roboclaws.openclaw.bridge import OpenClawUnavailable

    with patch("openclaw_demo.OpenClawProvider") as ProviderCls:
        provider = ProviderCls.return_value
        provider.ping.side_effect = OpenClawUnavailable("gateway down")
        with pytest.raises(SystemExit):
            run_openclaw_demo(
                scene="FloorPlan201",
                agent_count=2,
                steps=5,
                output_dir=str(tmp_path / "demo"),
            )
        provider.close.assert_called()
