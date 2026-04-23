from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np
import pytest

from roboclaws.core.engine import NAVIGATION_ACTIONS
from roboclaws.openclaw.mcp_server import RoboclawsMCPServer, make_roboclaws_mcp
from roboclaws.openclaw.vision_bridge import VisionBridgeResult

REFERENCE = json.loads(
    (Path(__file__).parent / "fixtures" / "trace_schema_reference.json").read_text(encoding="utf-8")
)


def _frame(color: int = 0) -> np.ndarray:
    return np.full((240, 320, 3), color, dtype=np.uint8)


@dataclass
class FakeAgentState:
    agent_id: int
    frame: np.ndarray
    position: dict[str, float]
    rotation: dict[str, float]
    camera_horizon: float
    last_action_success: bool
    last_action_error: str = ""
    visible_objects: list[dict[str, Any]] = field(default_factory=list)


class FakeEngine:
    """Minimal stand-in for MultiAgentEngine used by the MCP server tests."""

    def __init__(self) -> None:
        self.agent_count = 1
        self._fpv = _frame(10)
        self._overhead = _frame(200)
        self._chase = _frame(90)
        self.calls_step: list[tuple[int, str]] = []
        self.chase_updates = 0
        self._position = {"x": 1.0, "y": 0.0, "z": -2.0}
        self._rotation = {"x": 0.0, "y": 90.0, "z": 0.0}
        self._last_action_success = True
        self._last_action_error = ""

    def _state(self, agent_id: int) -> FakeAgentState:
        return FakeAgentState(
            agent_id=agent_id,
            frame=self._fpv,
            position=dict(self._position),
            rotation=dict(self._rotation),
            camera_horizon=30.0,
            last_action_success=self._last_action_success,
            last_action_error=self._last_action_error,
        )

    def get_agent_state(self, agent_id: int) -> FakeAgentState:
        return self._state(agent_id)

    def get_all_agent_states(self) -> list[FakeAgentState]:
        return [self._state(0)]

    def get_reachable_positions(self) -> set[tuple[int, int]]:
        return {(4, -8), (5, -8), (6, -8), (6, -7)}

    def get_overhead_frame(self) -> np.ndarray:
        return self._overhead

    def add_chase_cam(self, agent_id: int) -> int:
        return agent_id + 1

    def update_chase_cam(self, agent_id: int) -> None:
        self.chase_updates += 1

    def get_chase_cam_frame(self, agent_id: int) -> np.ndarray:
        return self._chase

    def step(self, agent_id: int, direction: str) -> FakeAgentState:
        self.calls_step.append((agent_id, direction))
        # MoveBack is used in the suite to exercise the "blocked" branch.
        success = direction != "MoveBack"
        self._last_action_success = success
        self._last_action_error = "" if success else "blocked"
        if success and direction == "MoveAhead":
            self._position["x"] = 1.25
        return self._state(agent_id)


@pytest.fixture
def engine() -> FakeEngine:
    return FakeEngine()


@pytest.fixture
def server(engine: FakeEngine, tmp_path: Path) -> RoboclawsMCPServer:
    srv = make_roboclaws_mcp(engine, agent_id=0, run_dir=tmp_path, port=0)
    try:
        yield srv
    finally:
        srv.close()


def _read_trace(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / "trace.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


# ---------------------------------------------------------------------------
# Tool behavior
# ---------------------------------------------------------------------------


def test_observe_returns_state_text_plus_three_images(
    server: RoboclawsMCPServer, engine: FakeEngine
) -> None:
    result = server._do_observe()
    assert isinstance(result, list)
    assert len(result) == 4

    # Text block first — JSON-serialized state
    state_text = result[0]
    assert isinstance(state_text, str)
    state = json.loads(state_text)
    for key in ("agent_id", "position", "rotation", "camera_horizon", "last_action_success"):
        assert key in state
    assert "human_message" in state
    assert state["view_variant"] == "map-v2+chase"
    assert state["image_labels"] == ["fpv", "map_v2", "chase"]
    assert state["observe_delivery"] == "images"
    assert state["bridge_model"] is None
    assert state["agent_id"] == 0

    # Three image blocks — SDK Image objects expose `.data` as bytes
    for block in result[1:]:
        assert hasattr(block, "data") and isinstance(block.data, bytes) and len(block.data) > 0
    assert engine.chase_updates == 1

    # Trace carries raw overhead + chase for replay renderer
    frame_capture = [
        line for line in _read_trace(server.run_dir) if line.get("event") == "frame_capture"
    ][0]
    assert frame_capture["view_variant"] == "map-v2+chase"
    assert frame_capture["image_labels"] == ["fpv", "map_v2", "chase"]
    assert "baseline_overhead" in frame_capture
    assert "chase" in frame_capture

    # Ledger marks the observe as seen
    assert server.snapshot_metrics()["observed_once"] is True


@pytest.mark.parametrize(
    "model_name",
    ["anthropic_kimi/k2p5", "mimo_openai/mimo-v2-omni"],
)
def test_observe_auto_keeps_images_for_image_capable_models(
    engine: FakeEngine,
    tmp_path: Path,
    model_name: str,
) -> None:
    srv = make_roboclaws_mcp(
        engine,
        agent_id=0,
        run_dir=tmp_path,
        port=0,
        model_name=model_name,
        observe_mode="auto",
    )
    try:
        result = srv._do_observe()
    finally:
        srv.close()

    assert len(result) == 4
    state = json.loads(result[0])
    assert state["observe_delivery"] == "images"
    assert state["bridge_model"] is None


class _FakeVisionBridge:
    def __init__(self, result: VisionBridgeResult) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def describe(self, **kwargs: Any) -> VisionBridgeResult:
        self.calls.append(kwargs)
        return self.result


def test_observe_text_bridge_returns_two_text_blocks(
    engine: FakeEngine,
    tmp_path: Path,
) -> None:
    bridge = _FakeVisionBridge(
        VisionBridgeResult(
            delivery="text-bridge",
            description="Immediate view: table ahead. Navigation cues: rotate right.",
            bridge_model="mimo_openai/mimo-v2-omni",
            latency_s=0.42,
        )
    )
    srv = make_roboclaws_mcp(
        engine,
        agent_id=0,
        run_dir=tmp_path,
        port=0,
        model_name="mimo_openai/mimo-v2.5-pro",
        image_model="mimo_openai/mimo-v2-omni",
        observe_mode="auto",
        vision_bridge=bridge,
    )
    try:
        result = srv._do_observe()
    finally:
        srv.close()

    assert result == [
        result[0],
        "Immediate view: table ahead. Navigation cues: rotate right.",
    ]
    state = json.loads(result[0])
    assert state["observe_delivery"] == "text-bridge"
    assert state["bridge_model"] == "mimo_openai/mimo-v2-omni"
    assert state["image_labels"] == ["vision_bridge"]
    assert len(bridge.calls) == 1
    assert bridge.calls[0]["image_labels"] == ["fpv", "map_v2", "chase"]

    response = [
        line
        for line in _read_trace(tmp_path)
        if line.get("tool") == "observe" and line.get("event") == "response"
    ][0]["response"]
    assert response["observe_delivery"] == "text-bridge"
    assert response["bridge_model"] == "mimo_openai/mimo-v2-omni"
    assert response["bridge_latency_s"] == 0.42
    assert response["bridge_error"] is None


def test_observe_text_bridge_failure_returns_safe_text_shape(
    engine: FakeEngine,
    tmp_path: Path,
) -> None:
    bridge = _FakeVisionBridge(
        VisionBridgeResult(
            delivery="text-bridge",
            description="Vision bridge unavailable; use structured state only.",
            bridge_model="mimo_openai/mimo-v2-omni",
            latency_s=0.1,
            error="upstream unavailable",
        )
    )
    srv = make_roboclaws_mcp(
        engine,
        agent_id=0,
        run_dir=tmp_path,
        port=0,
        model_name="mimo_openai/mimo-v2.5",
        image_model="mimo_openai/mimo-v2-omni",
        observe_mode="auto",
        vision_bridge=bridge,
    )
    try:
        result = srv._do_observe()
    finally:
        srv.close()

    assert len(result) == 2
    assert all(isinstance(block, str) for block in result)
    state = json.loads(result[0])
    assert state["observe_delivery"] == "text-bridge"
    assert state["image_labels"] == ["vision_bridge"]
    assert "Vision bridge unavailable" in result[1]


def test_move_valid_direction_steps_engine(server: RoboclawsMCPServer, engine: FakeEngine) -> None:
    response = server._do_move("MoveAhead", "clear hallway")
    assert engine.calls_step == [(0, "MoveAhead")]
    assert response["result"] == "ok"
    assert response["state"]["last_action_success"] is True
    assert isinstance(response["step"], int)
    assert response["view_variant"] == "map-v2+chase"
    assert response["image_labels"] == ["fpv", "map_v2", "chase"]


def test_move_invalid_direction_does_not_step_engine(
    server: RoboclawsMCPServer, engine: FakeEngine
) -> None:
    response = server._do_move("Jump", "why not")
    assert engine.calls_step == []
    assert response["result"] == "error"
    assert response["error"] == "invalid direction"
    assert "MoveAhead" in response["valid"]


def test_move_blocked_returns_blocked(server: RoboclawsMCPServer, engine: FakeEngine) -> None:
    response = server._do_move("MoveBack", "reverse")
    assert engine.calls_step == [(0, "MoveBack")]
    assert response["result"] == "blocked"
    assert response["state"]["last_action_success"] is False


def test_done_sets_event_and_records_reason(server: RoboclawsMCPServer) -> None:
    response = server._do_done("goal reached")
    assert server.done_event.is_set()
    assert server._done_reason == "goal reached"
    assert response["final"] is True
    assert response["reason"] == "goal reached"
    assert isinstance(response["total_moves"], int) and response["total_moves"] >= 0
    assert isinstance(response["elapsed_s"], float) and response["elapsed_s"] >= 0.0


def test_done_is_idempotent_on_reason(server: RoboclawsMCPServer) -> None:
    server._do_done("first-reason")
    response = server._do_done("second-reason-ignored")
    assert response["reason"] == "first-reason"


def test_enqueue_human_message_drains_on_observe(server: RoboclawsMCPServer) -> None:
    server.enqueue_human_message("turn left")
    result = server._do_observe()
    state = json.loads(result[0])
    assert state["human_message"] == "turn left"

    result_again = server._do_observe()
    state_again = json.loads(result_again[0])
    assert state_again["human_message"] is None


def test_human_message_queue_drains_on_move(server: RoboclawsMCPServer) -> None:
    server.enqueue_human_message("rotate please")
    response = server._do_move("RotateLeft")
    assert response["human_message"] == "rotate please"


# ---------------------------------------------------------------------------
# Reference-fixture contract
# ---------------------------------------------------------------------------


def test_snapshot_metrics_keys_equal_reference(server: RoboclawsMCPServer) -> None:
    metrics = server.snapshot_metrics()
    # EQUALITY, not superset. snapshot_metrics is frozen tight because
    # run_result_json["sim_server_metrics"] consumers depend on the exact keyset.
    assert set(metrics.keys()) == set(REFERENCE["snapshot_metrics"]["required_keys"])


def test_trace_payload_is_superset_of_reference_required(server: RoboclawsMCPServer) -> None:
    server._do_observe()
    server._do_move("MoveAhead", "clear hallway")
    server._do_done("goal")
    lines = _read_trace(server.run_dir)
    assert lines, "expected at least one trace line after observe+move+done"
    required = set(REFERENCE["trace_payload"]["required_keys"])
    for line in lines:
        assert required.issubset(set(line.keys())), (
            f"trace line missing required keys: {required - set(line.keys())}"
        )


def test_frame_capture_payload_is_superset_of_reference_required(
    server: RoboclawsMCPServer,
) -> None:
    server._do_observe()
    server._do_move("MoveAhead", "clear hallway")
    frame_lines = [
        line for line in _read_trace(server.run_dir) if line.get("event") == "frame_capture"
    ]
    assert len(frame_lines) >= 2
    required = set(REFERENCE["frame_capture_payload"]["required_keys"])
    for line in frame_lines:
        assert required.issubset(set(line.keys())), (
            f"frame_capture missing required keys: {required - set(line.keys())}"
        )


def test_trace_jsonl_contains_tool_events(server: RoboclawsMCPServer) -> None:
    server._do_observe()
    server._do_move("MoveAhead")
    server._do_done("done-reason")
    events = {(line["tool"], line["event"]) for line in _read_trace(server.run_dir)}
    assert {
        ("observe", "request"),
        ("observe", "response"),
        ("move", "request"),
        ("move", "response"),
        ("done", "request"),
        ("done", "response"),
    }.issubset(events)


def test_write_trace_event_emits_additive_transcript_payload(server: RoboclawsMCPServer) -> None:
    server.write_trace_event(
        tool="assistant",
        event="assistant_transcript",
        source="stream",
        content="checking session",
        message_index=0,
        chunk_index=1,
        is_final=False,
        wallclock_elapsed=1.25,
    )
    lines = _read_trace(server.run_dir)
    transcript = lines[-1]
    assert transcript["tool"] == "assistant"
    assert transcript["event"] == "assistant_transcript"
    assert transcript["source"] == "stream"
    assert transcript["content"] == "checking session"
    assert transcript["message_index"] == 0
    assert transcript["chunk_index"] == 1
    assert transcript["is_final"] is False
    assert transcript["wallclock_elapsed"] == 1.25


# ---------------------------------------------------------------------------
# Factory / binding defaults
# ---------------------------------------------------------------------------


def test_factory_defaults_to_localhost_binding(tmp_path: Path) -> None:
    """Threat model T-02.6-01: host defaults to 127.0.0.1, not 0.0.0.0."""
    engine = FakeEngine()
    srv = make_roboclaws_mcp(engine, agent_id=0, run_dir=tmp_path, port=0)
    try:
        assert srv.host == "127.0.0.1"
    finally:
        srv.close()


def test_navigation_actions_includes_expected(server: RoboclawsMCPServer) -> None:
    # Sanity check on the constant the move tool validates against.
    assert "MoveAhead" in NAVIGATION_ACTIONS
    assert "RotateLeft" in NAVIGATION_ACTIONS


# ---------------------------------------------------------------------------
# Thread-safety: close() vs concurrent trace writers (WR-01 regression guard)
# ---------------------------------------------------------------------------


def test_write_trace_after_close_is_safe(tmp_path: Path) -> None:
    """WR-01: write_runtime_event after close() must not raise.

    In production the watchdog + stdin threads in
    examples/openclaw_nav_autonomous.py join with a 0.2s timeout, so
    close() can race with a writer that's already called `snapshot_metrics`
    and is about to call `write_runtime_event`. Pre-fix this raised
    `ValueError: I/O operation on closed file.` Post-fix it's a silent
    no-op.
    """
    engine = FakeEngine()
    srv = make_roboclaws_mcp(engine, agent_id=0, run_dir=tmp_path, port=0)
    srv._do_observe()
    srv.close()
    # Must not raise; must not re-open the file.
    srv.write_runtime_event("watchdog", metrics={"x": 1})
    srv.enqueue_human_message("post-close message")
    # Calling close() again is idempotent.
    srv.close()


def test_run_in_thread_raises_when_server_dies_before_listening(tmp_path: Path) -> None:
    engine = FakeEngine()
    srv = make_roboclaws_mcp(engine, agent_id=0, run_dir=tmp_path, port=18788)
    try:
        with (
            patch.object(srv._mcp, "run", return_value=None),
            patch(
                "roboclaws.openclaw.mcp_server._port_accepting",
                return_value=False,
            ),
        ):
            with pytest.raises(RuntimeError, match="failed to start"):
                srv.run_in_thread()
    finally:
        srv.close()


# ---------------------------------------------------------------------------
# observe(label=...) — labeled-archive branch (was: roboclaws__snapshot)
# ---------------------------------------------------------------------------


def _extract_media_hint(result: list[Any]) -> str | None:
    """Pull the trailing MEDIA hint text block out of `_do_observe`'s list result."""
    for block in reversed(result):
        if isinstance(block, str) and "MEDIA:" in block:
            return block
    return None


def test_observe_labeled_without_snapshots_dir_skips_archive(
    server: RoboclawsMCPServer,
) -> None:
    """No snapshots_dir → labeled observe still returns state+images, just no MEDIA block."""
    result = server._do_observe(label="first")
    # State block + the configured variant's images; no MEDIA hint appended.
    assert len(result) >= 2
    assert _extract_media_hint(result) is None


def test_observe_labeled_writes_png_files_and_returns_media_hint(
    engine: FakeEngine, tmp_path: Path
) -> None:
    snap_dir = tmp_path / "snapshots"
    srv = make_roboclaws_mcp(
        engine,
        agent_id=0,
        run_dir=tmp_path / "run",
        port=0,
        snapshots_dir=snap_dir,
    )
    try:
        result = srv._do_observe(label="corner view")
        hint = _extract_media_hint(result)
        assert hint is not None, "labeled observe must append a MEDIA hint text block"

        # Paths MUST be absolute container-side paths under the agent
        # workspace. Live probe 2026-04-23 proved relative `./snapshots/…`
        # silently drop in the Control UI while absolute
        # `/home/node/.openclaw/workspaces/agent-<id>/snapshots/…` renders.
        # The Gateway's REPLY_MEDIA_HINT advises the opposite; we're right.
        workspace_prefix = "/home/node/.openclaw/workspaces/agent-0/snapshots/"
        assert f"MEDIA:{workspace_prefix}corner_view-001.fpv.png" in hint
        assert f"MEDIA:{workspace_prefix}corner_view-001.map.png" in hint
        assert f"MEDIA:{workspace_prefix}corner_view-001.chase.png" in hint
        # The hint must also tell the agent to IGNORE the Gateway's
        # "avoid absolute paths" system-prompt warning — without this,
        # Kimi obeys the stronger signal and emits a broken relative
        # path (observed 2026-04-23, first half of the session).
        assert "IGNORE" in hint or "ignore" in hint
        # Turn-placement rule: only the LAST assistant message of a turn
        # has its MEDIA extracted by the Control UI — intermediate
        # messages become plain text (observed 2026-04-23, second half
        # of the session: rapid1/rapid2 A/B test).
        assert "FINAL" in hint or "final assistant message" in hint
        # Anti-spiral guardrail: the hint must tell the agent not to retry
        # with alternate paths if the Control UI rejects the attachment.
        assert "Attachment unavailable" in hint
        assert "STOP" in hint

        # Files actually exist on disk with non-zero PNG bytes.
        for key in ("fpv", "map", "chase"):
            dest = snap_dir / f"corner_view-001.{key}.png"
            assert dest.exists()
            assert dest.read_bytes().startswith(b"\x89PNG")
            # Stable `latest.<kind>.png` sibling for the live viewer.
            latest = snap_dir / f"latest.{key}.png"
            assert latest.exists(), (
                f"latest.{key}.png must be (re)written atomically every "
                "labeled observe so scripts/view-snapshots.py can poll one "
                "stable filename instead of guessing counter suffixes"
            )
            assert latest.read_bytes() == dest.read_bytes()
    finally:
        srv.close()


def test_observe_unlabeled_does_not_archive(engine: FakeEngine, tmp_path: Path) -> None:
    """Unlabeled observe must NOT write labeled archive files — keeps disk tidy."""
    snap_dir = tmp_path / "snapshots"
    srv = make_roboclaws_mcp(
        engine,
        agent_id=0,
        run_dir=tmp_path / "run",
        port=0,
        snapshots_dir=snap_dir,
    )
    try:
        result = srv._do_observe()  # no label
        assert _extract_media_hint(result) is None
        # Only the latest.* viewer files should exist — no labeled archive.
        archived = [p.name for p in snap_dir.iterdir() if not p.name.startswith("latest.")]
        assert archived == [], f"unlabeled observe archived: {archived}"
    finally:
        srv.close()


def test_observe_label_counter_increments_across_calls(engine: FakeEngine, tmp_path: Path) -> None:
    snap_dir = tmp_path / "snapshots"
    srv = make_roboclaws_mcp(
        engine,
        agent_id=0,
        run_dir=tmp_path / "run",
        port=0,
        snapshots_dir=snap_dir,
    )
    try:
        hint1 = _extract_media_hint(srv._do_observe(label="probe"))
        hint2 = _extract_media_hint(srv._do_observe(label="probe"))
        assert hint1 is not None and "probe-001.fpv.png" in hint1
        assert hint2 is not None and "probe-002.fpv.png" in hint2
    finally:
        srv.close()


def test_observe_label_sanitizes_dangerous_input(engine: FakeEngine, tmp_path: Path) -> None:
    """Path-traversal / shell-metas get rewritten to `_`."""
    snap_dir = tmp_path / "snapshots"
    srv = make_roboclaws_mcp(
        engine,
        agent_id=0,
        run_dir=tmp_path / "run",
        port=0,
        snapshots_dir=snap_dir,
    )
    try:
        hint = _extract_media_hint(srv._do_observe(label="../../etc/passwd"))
        workspace_prefix = "/home/node/.openclaw/workspaces/agent-0/snapshots/"
        assert hint is not None and workspace_prefix in hint
        # Extract first MEDIA path and check sanitization.
        import re as _re

        m = _re.search(rf"MEDIA:({_re.escape(workspace_prefix)}[^\s]+\.fpv\.png)", hint)
        assert m, f"no absolute MEDIA fpv path in hint: {hint!r}"
        fname = m.group(1).removeprefix(workspace_prefix)
        assert ".." not in fname
        assert "/" not in fname, (
            f"sanitized label produced a path with a slash: {fname!r} — "
            "label traversal must collapse, not escape the snapshots dir"
        )
        assert (snap_dir / fname).exists()
    finally:
        srv.close()


def test_observe_labeled_trace_records_label_and_paths(engine: FakeEngine, tmp_path: Path) -> None:
    snap_dir = tmp_path / "snapshots"
    run_dir = tmp_path / "run"
    srv = make_roboclaws_mcp(
        engine,
        agent_id=0,
        run_dir=run_dir,
        port=0,
        snapshots_dir=snap_dir,
    )
    try:
        srv._do_observe(label="probe")
    finally:
        srv.close()

    entries = _read_trace(run_dir)
    req = next(e for e in entries if e["tool"] == "observe" and e["event"] == "request")
    resp = next(e for e in entries if e["tool"] == "observe" and e["event"] == "response")
    assert req["request"].get("label") == "probe"
    assert resp["response"].get("label") == "probe"
    paths = resp["response"].get("snapshot_paths")
    assert isinstance(paths, dict) and paths["fpv"].endswith(".fpv.png")


def test_snapshot_tool_is_not_registered(server: RoboclawsMCPServer) -> None:
    """KISS invariant: there is no separate `snapshot` tool — it was folded into observe."""
    assert not hasattr(server, "_do_snapshot")


def test_labeled_observe_encodes_each_frame_once(engine: FakeEngine, tmp_path: Path) -> None:
    """A labeled observe archives AND refreshes latest.*.png from a SINGLE encode.

    Regression guard: the first cut of this refactor re-encoded every frame
    twice (once for the archive, once for `_write_latest_snapshots`). The
    shared `_atomic_write_latest` helper in _maybe_write_labeled_snapshot now
    reuses the encoded bytes — this test pins that invariant so a future edit
    can't silently reintroduce the double-encode.
    """
    snap_dir = tmp_path / "snapshots"
    srv = make_roboclaws_mcp(
        engine,
        agent_id=0,
        run_dir=tmp_path / "run",
        port=0,
        snapshots_dir=snap_dir,
    )
    # Baseline: three 640px encodes for the archive + three 640px for latest
    # would be 6. Three 320px encodes for the MCP image blocks are a separate
    # code path (different max_dim) so we filter on max_dim=640.
    with patch(
        "roboclaws.openclaw.mcp_server._encode_frame_png",
        wraps=__import__(
            "roboclaws.openclaw.mcp_server", fromlist=["_encode_frame_png"]
        )._encode_frame_png,
    ) as enc:
        try:
            srv._do_observe(label="perf")
        finally:
            srv.close()
    large_encodes = [c for c in enc.call_args_list if c.kwargs.get("max_dim") == 640]
    assert len(large_encodes) == 3, (
        f"labeled observe did {len(large_encodes)} 640px encodes; expected 3. "
        "The archive write and latest.*.png refresh must share encoded bytes — "
        "don't revert to re-encoding."
    )


# ---------------------------------------------------------------------------
# move response enrichment: pose_delta, visited_count, warning, blind-nudge
# ---------------------------------------------------------------------------


def test_move_response_includes_pose_delta_and_visited_count(
    server: RoboclawsMCPServer, engine: FakeEngine
) -> None:
    server._do_observe()
    response = server._do_move("MoveAhead", "clear hallway")
    assert "pose_delta" in response
    # FakeEngine pumps x 1.0 -> 1.25 on MoveAhead.
    assert response["pose_delta"]["dx"] == pytest.approx(0.25, abs=0.001)
    assert response["pose_delta"]["dz"] == pytest.approx(0.0, abs=0.001)
    assert response["pose_delta"]["dyaw"] == pytest.approx(0.0, abs=0.1)
    assert response["visited_count_here"] >= 1
    assert response["collisions"] == 0
    assert response["collisions_total"] == 0
    assert response["moves_since_observe"] == 1


def test_move_without_prior_observe_emits_warning(
    server: RoboclawsMCPServer, engine: FakeEngine
) -> None:
    """Guard A: never-observed → response warning field fires (not just trace)."""
    response = server._do_move("MoveAhead", "probe")
    assert "warning" in response
    assert "observe" in response["warning"].lower()


def test_move_warning_after_three_blind_moves(
    server: RoboclawsMCPServer, engine: FakeEngine
) -> None:
    server._do_observe()
    r1 = server._do_move("RotateRight")
    r2 = server._do_move("RotateRight")
    r3 = server._do_move("RotateRight")
    assert "warning" not in r1
    assert "warning" not in r2
    assert "warning" in r3
    assert "without observing" in r3["warning"]


def test_move_blocked_increments_collision_counter(engine: FakeEngine, tmp_path: Path) -> None:
    srv = make_roboclaws_mcp(engine, agent_id=0, run_dir=tmp_path, port=0)
    try:
        srv._do_observe()
        r = srv._do_move("MoveBack", "reverse (blocked in FakeEngine)")
        assert r["result"] == "blocked"
        assert r["collisions"] == 1
        assert r["collisions_total"] == 1
    finally:
        srv.close()


def test_blind_move_nudge_injects_synthetic_human_message(
    server: RoboclawsMCPServer, engine: FakeEngine
) -> None:
    """After 5 blind moves with no real human_message queued, server nudges via human_message."""
    server._do_observe()
    for _ in range(4):
        r = server._do_move("RotateRight")
        assert r["human_message"] is None
    r5 = server._do_move("RotateRight")
    assert r5["human_message"] is not None
    assert "observe" in r5["human_message"].lower()
    # Next move should NOT re-nudge (flag suppresses until observe clears it).
    r6 = server._do_move("RotateRight")
    assert r6["human_message"] is None
    # A fresh observe clears the flag → nudge can fire again after 5 more blind moves.
    server._do_observe()
    for _ in range(4):
        server._do_move("RotateRight")
    r_next_nudge = server._do_move("RotateRight")
    assert r_next_nudge["human_message"] is not None


def test_blind_move_nudge_does_not_overwrite_real_human_message(
    server: RoboclawsMCPServer, engine: FakeEngine
) -> None:
    """When the operator types something, the real message wins over the synthetic nudge."""
    server._do_observe()
    for _ in range(4):
        server._do_move("RotateRight")
    server.enqueue_human_message("hey look left")
    r = server._do_move("RotateRight")
    assert r["human_message"] == "hey look left"
