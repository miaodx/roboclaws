from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from roboclaws.openclaw.diagnostics import (
    ReplayTurn,
    load_replay_turn,
    probe_direct_provider,
    probe_openclaw_ping,
    probe_openclaw_turn,
    run_latency_probe,
)


def _write_replay_fixture(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "agent_frames").mkdir()
    (root / "overhead").mkdir()
    manifest = {
        "steps": [
            {
                "step": 0,
                "agent_id": 1,
                "vlm_prompt_state": {"step": 0, "my_agent_id": 1, "game": "coverage"},
            }
        ]
    }
    (root / "replay.json").write_text(json.dumps(manifest))
    frame = np.full((8, 8, 3), 120, dtype=np.uint8)
    overhead = np.full((8, 8, 3), 80, dtype=np.uint8)
    Image.fromarray(frame).save(root / "agent_frames" / "0000_agent1.png")
    Image.fromarray(overhead).save(root / "overhead" / "0000_overhead.png")
    return root


def test_load_replay_turn_reads_manifest_and_frames(tmp_path: Path) -> None:
    replay_dir = _write_replay_fixture(tmp_path / "replay")
    turn = load_replay_turn(replay_dir, step=0)
    assert turn.step == 0
    assert turn.agent_id == 1
    assert turn.prompt_state["game"] == "coverage"
    assert turn.frame.shape == (8, 8, 3)
    assert turn.overhead.shape == (8, 8, 3)


def test_probe_openclaw_ping_times_reply() -> None:
    bridge = MagicMock()
    bridge.ping.return_value = "PONG"
    result = probe_openclaw_ping(bridge, agent_id=1)
    assert result["probe"] == "openclaw_ping"
    assert result["agent_id"] == 1
    assert result["reply"] == "PONG"
    assert result["duration_seconds"] >= 0.0


def test_probe_openclaw_turn_returns_transport_metrics() -> None:
    bridge = MagicMock()
    bridge.step.return_value = {"reasoning": "go", "action": "MoveAhead"}
    bridge.get_last_step_metrics.return_value = {
        "timings": {"openclaw_gateway_request_seconds": 9.9}
    }
    turn = ReplayTurn(
        replay_dir=Path("/tmp/replay"),
        step=0,
        agent_id=1,
        prompt_state={"step": 0, "my_agent_id": 1},
        frame=np.zeros((4, 4, 3), dtype=np.uint8),
        overhead=np.zeros((4, 4, 3), dtype=np.uint8),
    )
    result = probe_openclaw_turn(bridge, turn)
    assert result["probe"] == "openclaw_turn"
    assert result["response"]["action"] == "MoveAhead"
    assert (
        result["transport_metrics"]["timings"]["openclaw_gateway_request_seconds"]
        == pytest.approx(9.9)
    )


def test_probe_direct_provider_reports_payload_metrics() -> None:
    class Provider:
        def get_action(self, images, state):
            assert len(images) == 2
            assert state["my_agent_id"] == 1
            return {"reasoning": "ok", "action": "MoveAhead"}

    turn = ReplayTurn(
        replay_dir=Path("/tmp/replay"),
        step=0,
        agent_id=1,
        prompt_state={"step": 0, "my_agent_id": 1},
        frame=np.zeros((4, 4, 3), dtype=np.uint8),
        overhead=np.zeros((4, 4, 3), dtype=np.uint8),
    )
    result = probe_direct_provider(Provider(), turn)
    assert result["probe"] == "direct_provider_turn"
    assert result["payload"]["image_count"] == 2
    assert result["payload"]["state_json_chars"] > 0
    assert result["response"]["action"] == "MoveAhead"


def test_run_latency_probe_collects_all_paths(tmp_path: Path) -> None:
    replay_dir = _write_replay_fixture(tmp_path / "replay")

    bridge = MagicMock()
    bridge.__enter__.return_value = bridge
    bridge.__exit__.return_value = None
    bridge.ping.return_value = "PONG"
    bridge.step.return_value = {"reasoning": "go", "action": "MoveAhead"}
    bridge.get_last_step_metrics.return_value = {
        "timings": {"openclaw_gateway_request_seconds": 9.9}
    }

    provider = MagicMock()
    provider.get_action.return_value = {"reasoning": "ok", "action": "MoveAhead"}
    provider.get_status.return_value = {"provider_name": "kimi", "model": "kimi-for-coding"}

    with patch("roboclaws.openclaw.diagnostics.OpenClawBridge", return_value=bridge):
        with patch("roboclaws.openclaw.diagnostics.create_provider", return_value=provider):
            result = run_latency_probe(replay_dir, step=0)

    probes = {probe["probe"] for probe in result["probes"]}
    assert {"openclaw_ping", "openclaw_turn", "direct_provider_turn"} <= probes
