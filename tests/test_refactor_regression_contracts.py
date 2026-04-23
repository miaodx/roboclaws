from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from roboclaws.core.replay import ReplayRecorder
from roboclaws.core.views import build_prompt_images, image_labels_for_variant
from roboclaws.regression import (
    CaptureRequest,
    RegressionSuite,
    load_replay_summary_reference,
    load_row_reference,
    load_trace_schema_reference,
    normalize_capture_row,
)


def _frame(value: int) -> np.ndarray:
    return np.full((8, 8, 3), value, dtype=np.uint8)


def test_image_labels_for_map_v2_chase_are_frozen() -> None:
    assert image_labels_for_variant("map-v2+chase") == ("fpv", "map_v2", "chase")


def test_build_prompt_images_preserves_fpv_map_chase_order() -> None:
    prompt_images = build_prompt_images(
        fpv_frame=_frame(10),
        structured_overhead_frame=_frame(20),
        chase_cam_frame=_frame(30),
    )

    assert [int(frame[0, 0, 0]) for frame in prompt_images] == [10, 20, 30]


def test_replay_recorder_summary_contract_is_a_superset(tmp_path: Path) -> None:
    recorder = ReplayRecorder(agent_count=1, game="contract-test")
    recorder.record_step(
        step=0,
        agent_id=0,
        agent_frames=[_frame(10)],
        overhead_frame=_frame(20),
        game_state={"visited_cells": 1},
        vlm_prompt_state={"step": 0},
        vlm_response={"action": "MoveAhead"},
    )
    run_dir = recorder.save(
        tmp_path / "replay",
        final_scores={"cells_visited": 1},
        termination_reason="max_steps",
        generate_gif=False,
    )

    replay = json.loads((run_dir / "replay.json").read_text(encoding="utf-8"))
    reference = load_replay_summary_reference()

    assert set(reference["metadata"]).issubset(replay["metadata"])
    assert set(reference["summary"]).issubset(replay["summary"])


def test_row_normalization_emits_required_common_fields() -> None:
    suite = RegressionSuite(
        name="fake-suite",
        backend="vlm",
        game="explore",
        capture=lambda _request, _artifact_dir: {},
    )
    request = CaptureRequest(
        label="baseline-2026-04-23",
        scene="FloorPlan201",
        seed=7,
        agents=1,
        steps=5,
        model="mock",
    )

    row = normalize_capture_row(
        suite=suite,
        request=request,
        artifact_dir=Path("output/refactor-regression/baseline/fake-suite/FloorPlan201-seed7/run"),
        run_id="run-123",
        status="ok",
        variant=None,
        extra={"wallclock_seconds": 1.2},
    )
    reference = load_row_reference()

    assert set(reference["required_keys"]).issubset(row)
    assert row["variant"] is None
    assert row["artifact_dir"].endswith("/run")


def test_trace_schema_reference_remains_the_source_of_truth() -> None:
    reference = load_trace_schema_reference()

    assert "trace_payload" in reference
    assert "frame_capture_payload" in reference
    assert "snapshot_metrics" in reference
