from __future__ import annotations

import json

import numpy as np
import pytest
from PIL import Image  # noqa: E402

from roboclaws.core.replay import ReplayRecorder, ReplaySummary, _jsonify, _make_composite

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_frame(h: int = 48, w: int = 64, value: int = 128) -> np.ndarray:
    return np.full((h, w, 3), value, dtype=np.uint8)


def _make_recorder(agent_count: int = 2, game: str = "test") -> ReplayRecorder:
    return ReplayRecorder(agent_count=agent_count, game=game)


def _record_n_steps(recorder: ReplayRecorder, n: int = 3) -> None:
    agent_count = recorder._agent_count
    for i in range(n):
        recorder.record_step(
            step=i,
            agent_id=i % agent_count,
            agent_frames=[_make_frame(value=v * 20) for v in range(agent_count)],
            overhead_frame=_make_frame(value=50),
            game_state={"game": "test", "step": i, "score": i * 10},
            vlm_prompt_state={"my_agent_id": i % agent_count, "step": i},
            vlm_response={"reasoning": "move ahead", "action": "MoveAhead"},
        )


# ---------------------------------------------------------------------------
# ReplayRecorder — basic recording
# ---------------------------------------------------------------------------


def test_recorder_starts_empty() -> None:
    recorder = _make_recorder()
    assert len(recorder._steps) == 0


def test_record_step_increments_buffer() -> None:
    recorder = _make_recorder()
    _record_n_steps(recorder, n=5)
    assert len(recorder._steps) == 5


def test_record_step_copies_frames() -> None:
    """Mutations to the original frame after recording should not affect the stored copy."""
    recorder = _make_recorder(agent_count=1)
    original = _make_frame(value=100)
    recorder.record_step(
        step=0,
        agent_id=0,
        agent_frames=[original],
        overhead_frame=_make_frame(),
        game_state={},
        vlm_prompt_state={},
        vlm_response={"action": "MoveAhead"},
    )
    original[:] = 0  # mutate original
    stored = recorder._steps[0].agent_frames[0]
    assert stored[0, 0, 0] == 100  # copy is unaffected


def test_record_step_copies_overhead() -> None:
    recorder = _make_recorder(agent_count=1)
    overhead = _make_frame(value=77)
    recorder.record_step(
        step=0,
        agent_id=0,
        agent_frames=[_make_frame()],
        overhead_frame=overhead,
        game_state={},
        vlm_prompt_state={},
        vlm_response={"action": "MoveAhead"},
    )
    overhead[:] = 0
    stored = recorder._steps[0].overhead_frame
    assert stored[0, 0, 0] == 77


# ---------------------------------------------------------------------------
# save() — directory structure
# ---------------------------------------------------------------------------


def test_save_creates_output_dir(tmp_path) -> None:
    recorder = _make_recorder()
    _record_n_steps(recorder, n=2)
    out = recorder.save(tmp_path / "run")
    assert out.exists()
    assert out.is_dir()


def test_save_creates_subdirectories(tmp_path) -> None:
    recorder = _make_recorder()
    _record_n_steps(recorder, n=2)
    out = recorder.save(tmp_path / "run", generate_gif=False)
    assert (out / "frames").is_dir()
    assert (out / "agent_frames").is_dir()
    assert (out / "overhead").is_dir()


def test_save_creates_replay_json(tmp_path) -> None:
    recorder = _make_recorder()
    _record_n_steps(recorder, n=3)
    out = recorder.save(tmp_path / "run", generate_gif=False)
    assert (out / "replay.json").exists()


def test_save_replay_json_structure(tmp_path) -> None:
    recorder = _make_recorder(agent_count=2, game="territory")
    _record_n_steps(recorder, n=4)
    out = recorder.save(
        tmp_path / "run",
        vlm_cost_usd=0.01,
        final_scores={"0": 3, "1": 5},
        termination_reason="max_steps",
        generate_gif=False,
    )
    manifest = json.loads((out / "replay.json").read_text())
    assert manifest["metadata"]["game"] == "territory"
    assert manifest["metadata"]["agent_count"] == 2
    assert manifest["metadata"]["total_steps"] == 4
    assert manifest["metadata"]["vlm_cost_usd"] == pytest.approx(0.01)
    assert manifest["summary"]["termination_reason"] == "max_steps"
    assert len(manifest["steps"]) == 4


def test_save_replay_json_step_fields(tmp_path) -> None:
    recorder = _make_recorder()
    _record_n_steps(recorder, n=1)
    out = recorder.save(tmp_path / "run", generate_gif=False)
    manifest = json.loads((out / "replay.json").read_text())
    step = manifest["steps"][0]
    assert "step" in step
    assert "agent_id" in step
    assert "game_state" in step
    assert "vlm_prompt_state" in step
    assert "vlm_response" in step


def test_save_replay_json_includes_provider_status(tmp_path) -> None:
    recorder = _make_recorder()
    recorder.record_step(
        step=0,
        agent_id=0,
        agent_frames=[_make_frame()],
        overhead_frame=_make_frame(value=55),
        game_state={"game": "test", "step": 0},
        vlm_prompt_state={"step": 0},
        vlm_response={"reasoning": "move", "action": "MoveAhead"},
        provider_status={"provider_name": "kimi", "retry_events": 2},
    )
    out = recorder.save(
        tmp_path / "run",
        generate_gif=False,
        provider_status={"provider_name": "kimi", "retry_events": 2},
    )
    manifest = json.loads((out / "replay.json").read_text())
    assert manifest["summary"]["provider_status"]["provider_name"] == "kimi"
    assert manifest["steps"][0]["provider_status"]["retry_events"] == 2


def test_save_creates_composite_pngs(tmp_path) -> None:
    recorder = _make_recorder()
    _record_n_steps(recorder, n=3)
    out = recorder.save(tmp_path / "run", generate_gif=False)
    composites = list((out / "frames").glob("*_composite.png"))
    assert len(composites) == 3


def test_save_creates_agent_frame_pngs(tmp_path) -> None:
    recorder = _make_recorder(agent_count=2)
    _record_n_steps(recorder, n=2)
    out = recorder.save(tmp_path / "run", generate_gif=False)
    agent_pngs = sorted((out / "agent_frames").glob("*.png"))
    # 2 steps × 2 agents = 4 files
    assert len(agent_pngs) == 4


def test_save_creates_overhead_pngs(tmp_path) -> None:
    recorder = _make_recorder()
    _record_n_steps(recorder, n=3)
    out = recorder.save(tmp_path / "run", generate_gif=False)
    overheads = list((out / "overhead").glob("*_overhead.png"))
    assert len(overheads) == 3


def test_save_empty_recorder(tmp_path) -> None:
    """Saving with no steps recorded should not raise."""
    recorder = _make_recorder()
    out = recorder.save(tmp_path / "empty", generate_gif=False)
    assert (out / "replay.json").exists()
    manifest = json.loads((out / "replay.json").read_text())
    assert manifest["metadata"]["total_steps"] == 0
    assert manifest["steps"] == []


def test_save_returns_path(tmp_path) -> None:
    recorder = _make_recorder()
    _record_n_steps(recorder, n=1)
    result = recorder.save(tmp_path / "run", generate_gif=False)
    assert isinstance(result, type(tmp_path))


# ---------------------------------------------------------------------------
# save() — GIF generation
# ---------------------------------------------------------------------------


def test_save_generates_gif_when_imageio_available(tmp_path) -> None:
    pytest.importorskip("imageio")
    recorder = _make_recorder()
    _record_n_steps(recorder, n=3)
    out = recorder.save(tmp_path / "run", generate_gif=True, gif_fps=2.0)
    gif_path = out / "replay.gif"
    assert gif_path.exists()
    assert gif_path.stat().st_size > 0


def test_save_no_gif_when_generate_gif_false(tmp_path) -> None:
    recorder = _make_recorder()
    _record_n_steps(recorder, n=3)
    out = recorder.save(tmp_path / "run", generate_gif=False)
    assert not (out / "replay.gif").exists()


# ---------------------------------------------------------------------------
# generate_gif (static)
# ---------------------------------------------------------------------------


def test_generate_gif_from_numpy_arrays(tmp_path) -> None:
    pytest.importorskip("imageio")
    frames = [_make_frame(value=v) for v in [50, 100, 150]]
    path = tmp_path / "out.gif"
    ReplayRecorder.generate_gif(frames, path, fps=2.0)
    assert path.exists()
    assert path.stat().st_size > 0


def test_generate_gif_from_pil_images(tmp_path) -> None:
    pytest.importorskip("imageio")
    frames = [Image.new("RGB", (64, 48), (v, v, v)) for v in [0, 100, 200]]
    path = tmp_path / "out.gif"
    ReplayRecorder.generate_gif(frames, path, fps=4.0)
    assert path.exists()
    assert path.stat().st_size > 0


def test_generate_gif_raises_without_imageio(tmp_path, monkeypatch) -> None:
    import roboclaws.core.replay as replay_mod

    monkeypatch.setattr(replay_mod, "_HAS_IMAGEIO", False)
    frames = [_make_frame()]
    with pytest.raises(ImportError, match="imageio"):
        ReplayRecorder.generate_gif(frames, tmp_path / "x.gif")


# ---------------------------------------------------------------------------
# generate_gif_from_dir (static)
# ---------------------------------------------------------------------------


def test_generate_gif_from_dir(tmp_path) -> None:
    pytest.importorskip("imageio")
    recorder = _make_recorder()
    _record_n_steps(recorder, n=3)
    out = recorder.save(tmp_path / "run", generate_gif=False)

    gif_path = ReplayRecorder.generate_gif_from_dir(out)
    assert gif_path.exists()
    assert gif_path.stat().st_size > 0
    assert gif_path == out / "replay.gif"


def test_generate_gif_from_dir_custom_output(tmp_path) -> None:
    pytest.importorskip("imageio")
    recorder = _make_recorder()
    _record_n_steps(recorder, n=2)
    out = recorder.save(tmp_path / "run", generate_gif=False)

    custom = tmp_path / "custom.gif"
    gif_path = ReplayRecorder.generate_gif_from_dir(out, output_path=custom)
    assert gif_path == custom
    assert custom.exists()


def test_generate_gif_from_dir_empty_raises(tmp_path) -> None:
    pytest.importorskip("imageio")
    empty = tmp_path / "empty"
    (empty / "frames").mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="No composite frames"):
        ReplayRecorder.generate_gif_from_dir(empty)


# ---------------------------------------------------------------------------
# get_summary
# ---------------------------------------------------------------------------


def test_get_summary_returns_replay_summary() -> None:
    recorder = _make_recorder(agent_count=3, game="coverage")
    _record_n_steps(recorder, n=10)
    summary = recorder.get_summary(
        vlm_cost_usd=0.005,
        final_scores={"0": 20, "1": 15, "2": 18},
        termination_reason="coverage_reached",
    )
    assert isinstance(summary, ReplaySummary)
    assert summary.game == "coverage"
    assert summary.agent_count == 3
    assert summary.total_steps == 10
    assert summary.vlm_cost_usd == pytest.approx(0.005)
    assert summary.final_scores == {"0": 20, "1": 15, "2": 18}
    assert summary.termination_reason == "coverage_reached"
    assert summary.duration_seconds >= 0.0


def test_get_summary_defaults() -> None:
    recorder = _make_recorder()
    summary = recorder.get_summary()
    assert summary.final_scores == {}
    assert summary.termination_reason == "unknown"
    assert summary.vlm_cost_usd == 0.0


def test_get_summary_print_does_not_raise(capsys) -> None:
    recorder = _make_recorder()
    _record_n_steps(recorder, n=2)
    summary = recorder.get_summary(final_scores={"0": 5})
    summary.print()
    captured = capsys.readouterr()
    assert "Game" in captured.out
    assert "Steps" in captured.out


# ---------------------------------------------------------------------------
# _make_composite
# ---------------------------------------------------------------------------


def test_make_composite_returns_pil_image() -> None:
    frames = [_make_frame() for _ in range(2)]
    overhead = _make_frame(h=64, w=64)
    out = _make_composite(frames, overhead)
    assert isinstance(out, Image.Image)


def test_make_composite_height_matches_target() -> None:
    frames = [_make_frame()]
    overhead = _make_frame()
    out = _make_composite(frames, overhead, target_height=120)
    assert out.height == 120


def test_make_composite_width_increases_with_agents() -> None:
    overhead = _make_frame()
    out2 = _make_composite([_make_frame(), _make_frame()], overhead)
    out3 = _make_composite([_make_frame(), _make_frame(), _make_frame()], overhead)
    assert out3.width > out2.width


# ---------------------------------------------------------------------------
# _jsonify
# ---------------------------------------------------------------------------


def test_jsonify_plain_dict() -> None:
    result = _jsonify({"a": 1, "b": "hello"})
    assert result == {"a": 1, "b": "hello"}


def test_jsonify_numpy_integer() -> None:
    result = _jsonify(np.int64(42))
    assert result == 42
    assert isinstance(result, int)


def test_jsonify_numpy_float() -> None:
    result = _jsonify(np.float32(3.14))
    assert isinstance(result, float)


def test_jsonify_numpy_array() -> None:
    arr = np.array([1, 2, 3])
    result = _jsonify(arr)
    assert result == [1, 2, 3]
    assert isinstance(result, list)


def test_jsonify_nested() -> None:
    data = {"score": np.int64(5), "items": [np.float32(1.0), "text"], "nested": {"x": np.int32(7)}}
    result = _jsonify(data)
    json.dumps(result)  # must not raise


def test_jsonify_tuple_becomes_list() -> None:
    result = _jsonify((1, 2, 3))
    assert result == [1, 2, 3]
    assert isinstance(result, list)
