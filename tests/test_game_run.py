from __future__ import annotations

import json

import numpy as np

from roboclaws.core.game_run import (
    create_game_provider,
    prepare_prompt_payload,
    record_game_turn,
)
from roboclaws.core.replay import ReplayRecorder


def test_create_game_provider_seeds_mock_provider_for_direct_runs() -> None:
    first = create_game_provider(
        backend="vlm",
        gateway_url=None,
        agent_count=2,
        model="mock",
        agent_soul_content={},
        provider_seed=7,
    )
    second = create_game_provider(
        backend="vlm",
        gateway_url=None,
        agent_count=2,
        model="mock",
        agent_soul_content={},
        provider_seed=7,
    )

    first_action = first.get_action([], {})["action"]
    second_action = second.get_action([], {})["action"]

    assert first_action == second_action


def test_prepare_prompt_payload_keeps_openclaw_frames_unencoded() -> None:
    frame = np.zeros((4, 4, 3), dtype=np.uint8)

    prompt_images, payload_metrics, encode_seconds = prepare_prompt_payload(
        backend="openclaw",
        prompt_image_frames=[frame],
        prompt_state_text='{"step": 1}',
        prompt_state_metrics={"chars": 11},
    )

    assert prompt_images == [frame]
    assert encode_seconds == 0.0
    assert payload_metrics["transport"] == "openclaw_ndarray"


def test_prepare_prompt_payload_encodes_direct_vlm_frames() -> None:
    frame = np.zeros((4, 4, 3), dtype=np.uint8)

    prompt_images, payload_metrics, encode_seconds = prepare_prompt_payload(
        backend="vlm",
        prompt_image_frames=[frame, frame, frame],
        prompt_state_text='{"step": 1}',
        prompt_state_metrics={"chars": 11},
    )

    assert len(prompt_images) == 3
    assert isinstance(prompt_images[0], str)
    assert encode_seconds >= 0.0
    assert payload_metrics["transport"] == "vlm_base64_jpeg"


def test_record_game_turn_persists_turn_timing_metrics(tmp_path) -> None:
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    recorder = ReplayRecorder(agent_count=1, game="explore")
    turn_metrics = {"timings": {"provider_call_seconds": 0.1}, "payload": {"transport": "mock"}}

    record_game_turn(
        recorder=recorder,
        step=0,
        agent_id=0,
        agent_frames=[frame],
        overhead_frame=frame,
        game_state={"step": 0},
        prompt_state={"views": "map-v2+chase"},
        response={"action": "MoveAhead"},
        provider_status={"provider_name": "mock"},
        turn_metrics=turn_metrics,
        step_started=0.0,
    )
    out_path = recorder.save(tmp_path / "run", generate_gif=False)
    replay = json.loads((out_path / "replay.json").read_text(encoding="utf-8"))

    recorded_metrics = replay["steps"][0]["turn_metrics"]
    assert recorded_metrics["payload"] == {"transport": "mock"}
    assert recorded_metrics["timings"]["provider_call_seconds"] == 0.1
    assert "record_step_seconds" in recorded_metrics["timings"]
    assert "step_loop_seconds" in recorded_metrics["timings"]
