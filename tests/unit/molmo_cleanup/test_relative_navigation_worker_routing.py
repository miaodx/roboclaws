from __future__ import annotations

import pytest

from scripts.molmo_cleanup import (
    molmospaces_subprocess_worker,
    molmospaces_worker_cli,
    molmospaces_worker_protocol,
)


def test_molmospaces_worker_cli_routes_relative_pose_kwargs() -> None:
    parser = molmospaces_worker_cli.build_arg_parser(
        default_render_width=540,
        default_render_height=360,
    )

    args = parser.parse_args(
        [
            "--state-path",
            "state.json",
            "navigate_to_relative_pose",
            "--forward-m",
            "0.25",
            "--lateral-m",
            "-0.125",
            "--yaw-delta-deg",
            "15",
        ]
    )
    kwargs = molmospaces_worker_protocol.cli_command_kwargs(args)

    assert kwargs == {
        "forward_m": 0.25,
        "lateral_m": -0.125,
        "yaw_delta_deg": 15.0,
    }
    assert "navigate_to_relative_pose" in molmospaces_subprocess_worker._STATE_MUTATING_COMMANDS
    assert (
        "navigate_to_relative_pose"
        in molmospaces_subprocess_worker._WORKER_COMMAND_HANDLERS
    )


def test_molmospaces_worker_dispatches_relative_pose_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_navigate_to_relative_pose(
        state,  # noqa: ANN001
        *,
        forward_m: float,
        lateral_m: float,
        yaw_delta_deg: float,
    ) -> dict[str, object]:
        captured["state"] = state
        captured["forward_m"] = forward_m
        captured["lateral_m"] = lateral_m
        captured["yaw_delta_deg"] = yaw_delta_deg
        return {"ok": True, "tool": "navigate_to_relative_pose"}

    monkeypatch.setattr(
        molmospaces_subprocess_worker,
        "navigate_to_relative_pose",
        fake_navigate_to_relative_pose,
    )

    state = {"robot_pose": {"x": 0.0, "y": 0.0, "theta": 0.0}}
    result, should_write = molmospaces_subprocess_worker._run_loaded_state_command(
        state,
        "navigate_to_relative_pose",
        {"forward_m": "0.25", "lateral_m": "-0.125", "yaw_delta_deg": "15"},
    )

    assert result == {"ok": True, "tool": "navigate_to_relative_pose"}
    assert should_write is True
    assert captured == {
        "state": state,
        "forward_m": 0.25,
        "lateral_m": -0.125,
        "yaw_delta_deg": 15.0,
    }


def test_isaac_worker_cli_exposes_relative_pose_command() -> None:
    from scripts.isaac_lab_cleanup import isaac_lab_backend_worker

    args = isaac_lab_backend_worker.parse_args(
        [
            "--state-path",
            "state.json",
            "navigate_to_relative_pose",
            "--forward-m",
            "0.25",
            "--lateral-m",
            "-0.125",
            "--yaw-delta-deg",
            "15",
        ]
    )

    assert args.command == "navigate_to_relative_pose"
    assert args.forward_m == pytest.approx(0.25)
    assert args.lateral_m == pytest.approx(-0.125)
    assert args.yaw_delta_deg == pytest.approx(15.0)
    assert "navigate_to_relative_pose" in isaac_lab_backend_worker._STATE_COMMANDS
