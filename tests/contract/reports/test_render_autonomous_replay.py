from __future__ import annotations

import base64
import io
import json
import os
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "reports" / "render_autonomous_replay.py"


def _tiny_jpeg_b64(colour: str = "blue") -> str:
    image = Image.new("RGB", (4, 4), color=colour)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=70)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _make_tool_event(
    *,
    event_type: str,
    tool: str,
    wallclock: float,
    request: dict | None = None,
    response: dict | None = None,
) -> dict:
    event: dict[str, object] = {
        "event": event_type,
        "tool": tool,
        "wallclock_elapsed": wallclock,
    }
    if request is not None:
        event["request"] = request
    if response is not None:
        event["response"] = response
    return event


def _make_frame_event(
    *,
    wallclock: float,
    tool: str,
    seen_by_agent: bool,
    colour: str = "blue",
    human_message: str | None = None,
    decision_mode: str | None = None,
    move_reason: str | None = None,
    move_direction: str | None = None,
    view_variant: str = "baseline",
    image_labels: list[str] | None = None,
    baseline_colour: str | None = None,
    chase_colour: str | None = None,
) -> dict:
    resolved_labels = image_labels or ["fpv", "overhead"]
    event: dict[str, object] = {
        "event": "frame_capture",
        "tool": tool,
        "wallclock_elapsed": wallclock,
        "seen_by_agent": seen_by_agent,
        "fpv": _tiny_jpeg_b64(colour),
        "overhead": _tiny_jpeg_b64("white"),
        "view_variant": view_variant,
        "image_labels": resolved_labels,
        "agent_state": {"position": {"x": 1.0, "y": 0.0, "z": 2.0}},
    }
    if human_message is not None:
        event["human_message"] = human_message
    if decision_mode is not None:
        event["decision_mode"] = decision_mode
    if move_reason is not None:
        event["move_reason"] = move_reason
    if move_direction is not None:
        event["move_direction"] = move_direction
    if baseline_colour is not None:
        event["baseline_overhead"] = _tiny_jpeg_b64(baseline_colour)
    if chase_colour is not None:
        event["chase"] = _tiny_jpeg_b64(chase_colour)
    return event


def _make_transcript_event(
    *,
    wallclock: float,
    source: str,
    content: str,
    message_index: int = 0,
    chunk_index: int = 0,
    is_final: bool = False,
) -> dict:
    return {
        "event": "assistant_transcript",
        "tool": "assistant",
        "wallclock_elapsed": wallclock,
        "source": source,
        "content": content,
        "message_index": message_index,
        "chunk_index": chunk_index,
        "is_final": is_final,
    }


def _write_trace(run_dir: Path, events: list[dict]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "trace.jsonl").write_text(
        "\n".join(json.dumps(event) for event in events),
        encoding="utf-8",
    )


def _run_renderer(
    run_dir: Path,
    *,
    rerun_command: str | None = None,
    generate_gif: bool = False,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{REPO_ROOT}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else str(REPO_ROOT)
    )
    command = [sys.executable, str(SCRIPT_PATH), "--run-dir", str(run_dir)]
    if rerun_command is not None:
        command.extend(["--rerun-command", rerun_command])
    if generate_gif:
        command.append("--generate-gif")
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def test_renders_html_without_rebuildable_gif_by_default(tmp_path: Path) -> None:
    run_dir = tmp_path / "mixed"
    events = [
        _make_tool_event(
            event_type="request",
            tool="observe",
            wallclock=0.0,
            request={},
        ),
        _make_frame_event(wallclock=0.1, tool="observe", seen_by_agent=True, colour="green"),
        _make_tool_event(
            event_type="request",
            tool="move",
            wallclock=0.2,
            request={"direction": "MoveAhead"},
        ),
        _make_frame_event(
            wallclock=0.3,
            tool="move",
            seen_by_agent=False,
            colour="red",
            decision_mode="fresh_observe",
            move_direction="MoveAhead",
            view_variant="map-v2+chase",
            image_labels=["fpv", "map_v2", "chase"],
            baseline_colour="gray",
            chase_colour="purple",
        ),
    ]
    _write_trace(run_dir, events)

    _run_renderer(
        run_dir,
        rerun_command="just task::run ai2thor-nav codex visual scene=FloorPlan201",
    )

    replay_gif = run_dir / "replay.gif"
    report_html = run_dir / "report.html"
    summary_json = run_dir / "summary.json"

    assert not replay_gif.exists()
    assert report_html.exists()
    report_text = report_html.read_text(encoding="utf-8")
    assert 'type="range"' in report_text
    assert "Current Frame" in report_text
    assert "Click any panel to zoom." in report_text
    assert "frame-lightbox" in report_text
    assert report_text.index("FPV") < report_text.index("Chase") < report_text.index("Map V2")
    assert "Map V2" in report_text
    assert "Chase" in report_text
    assert "fresh observation" in report_text
    assert "fresh observe-driven move" in report_text
    assert "Rerun Locally" in report_text
    assert "just task::run ai2thor-nav codex visual scene=FloorPlan201" in report_text
    assert summary_json.exists()


def test_renders_gif_when_explicitly_requested(tmp_path: Path) -> None:
    run_dir = tmp_path / "gif"
    events = [
        _make_tool_event(event_type="request", tool="observe", wallclock=0.0, request={}),
        _make_frame_event(wallclock=0.1, tool="observe", seen_by_agent=True, colour="green"),
    ]
    _write_trace(run_dir, events)

    _run_renderer(run_dir, generate_gif=True)

    replay_gif = run_dir / "replay.gif"
    assert replay_gif.exists()
    assert replay_gif.stat().st_size > 100


def test_reasoned_and_blind_batch_labels(tmp_path: Path) -> None:
    run_dir = tmp_path / "batched"
    events = [
        _make_tool_event(
            event_type="request",
            tool="observe",
            wallclock=0.0,
            request={},
        ),
        _make_frame_event(wallclock=0.1, tool="observe", seen_by_agent=True, colour="green"),
        _make_tool_event(
            event_type="request",
            tool="move",
            wallclock=0.2,
            request={"direction": "MoveAhead"},
        ),
        _make_frame_event(
            wallclock=0.3,
            tool="move",
            seen_by_agent=False,
            colour="orange",
            decision_mode="fresh_observe",
            move_direction="MoveAhead",
        ),
        _make_tool_event(
            event_type="request",
            tool="move",
            wallclock=0.4,
            request={"direction": "MoveAhead", "reason": "clear hallway continues"},
        ),
        _make_frame_event(
            wallclock=0.5,
            tool="move",
            seen_by_agent=False,
            colour="yellow",
            decision_mode="reasoned_batch",
            move_reason="clear hallway continues",
            move_direction="MoveAhead",
        ),
        _make_tool_event(
            event_type="request",
            tool="move",
            wallclock=0.6,
            request={"direction": "MoveRight"},
        ),
        _make_frame_event(
            wallclock=0.7,
            tool="move",
            seen_by_agent=False,
            colour="red",
            decision_mode="blind_batch",
            move_direction="MoveRight",
        ),
    ]
    _write_trace(run_dir, events)

    _run_renderer(run_dir)

    report_text = (run_dir / "report.html").read_text(encoding="utf-8")
    assert "reasoned continuation: clear hallway continues" in report_text
    assert "blind batch" in report_text
    assert "reasoned-batch" in report_text
    assert "blind-batch" in report_text


def test_summary_json_key_integrity(tmp_path: Path) -> None:
    run_dir = tmp_path / "summary"
    events = [
        _make_tool_event(
            event_type="request",
            tool="observe",
            wallclock=0.0,
            request={},
        ),
        _make_tool_event(
            event_type="response",
            tool="observe",
            wallclock=0.05,
            response={},
        ),
        _make_frame_event(wallclock=0.1, tool="observe", seen_by_agent=True, colour="green"),
        _make_tool_event(
            event_type="request",
            tool="move",
            wallclock=0.2,
            request={"direction": "MoveAhead"},
        ),
        _make_tool_event(
            event_type="response",
            tool="move",
            wallclock=0.25,
            response={},
        ),
        _make_frame_event(
            wallclock=0.3,
            tool="move",
            seen_by_agent=False,
            colour="red",
            decision_mode="fresh_observe",
            move_direction="MoveAhead",
        ),
        _make_tool_event(
            event_type="request",
            tool="observe",
            wallclock=0.4,
            request={},
        ),
        _make_tool_event(
            event_type="response",
            tool="observe",
            wallclock=0.45,
            response={"human_message": "check the overhead map"},
        ),
        _make_frame_event(
            wallclock=0.5,
            tool="observe",
            seen_by_agent=True,
            colour="blue",
            human_message="check the overhead map",
        ),
        _make_tool_event(
            event_type="request",
            tool="move",
            wallclock=0.6,
            request={"direction": "RotateLeft"},
        ),
        _make_tool_event(
            event_type="response",
            tool="move",
            wallclock=0.65,
            response={},
        ),
        _make_frame_event(
            wallclock=0.7,
            tool="move",
            seen_by_agent=False,
            colour="yellow",
            decision_mode="fresh_observe",
            move_direction="RotateLeft",
        ),
        _make_tool_event(
            event_type="request",
            tool="move",
            wallclock=0.8,
            request={"direction": "MoveAhead", "reason": "clear hallway continues"},
        ),
        _make_tool_event(
            event_type="response",
            tool="move",
            wallclock=0.85,
            response={},
        ),
        _make_frame_event(
            wallclock=0.9,
            tool="move",
            seen_by_agent=False,
            colour="purple",
            decision_mode="reasoned_batch",
            move_reason="clear hallway continues",
            move_direction="MoveAhead",
        ),
        _make_tool_event(
            event_type="request",
            tool="move",
            wallclock=1.0,
            request={"direction": "MoveRight"},
        ),
        _make_tool_event(
            event_type="response",
            tool="move",
            wallclock=1.05,
            response={},
        ),
        _make_frame_event(
            wallclock=1.1,
            tool="move",
            seen_by_agent=False,
            colour="orange",
            decision_mode="blind_batch",
            move_direction="MoveRight",
        ),
        _make_tool_event(
            event_type="request",
            tool="done",
            wallclock=1.2,
            request={"reason": "finished"},
        ),
    ]
    _write_trace(run_dir, events)

    _run_renderer(run_dir)

    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["total_tool_calls"] == 7
    assert summary["tool_calls_by_type"] == {"observe": 2, "move": 4, "done": 1}
    assert summary["observes_by_agent"] == 2
    assert summary["frames_unseen_by_agent"] == 4
    assert summary["moves"] == 4
    assert summary["human_messages_delivered"] == 1
    assert summary["decision_modes"] == {
        "fresh_observe": 2,
        "reasoned_batch": 1,
        "blind_batch": 1,
    }
    assert summary["terminated_by"] == "done"
    assert summary["transcript_message_count"] == 0
    assert summary["transcript_source"] == "none"


def test_html_is_well_formed(tmp_path: Path) -> None:
    run_dir = tmp_path / "html"
    events = [
        _make_tool_event(
            event_type="request",
            tool="observe",
            wallclock=0.0,
            request={},
        ),
        _make_frame_event(wallclock=0.1, tool="observe", seen_by_agent=True, colour="green"),
        _make_tool_event(
            event_type="request",
            tool="move",
            wallclock=0.2,
            request={"direction": "MoveAhead"},
        ),
        _make_frame_event(
            wallclock=0.3,
            tool="move",
            seen_by_agent=False,
            colour="red",
            decision_mode="fresh_observe",
            move_direction="MoveAhead",
        ),
    ]
    _write_trace(run_dir, events)

    _run_renderer(run_dir)
    report_text = (run_dir / "report.html").read_text(encoding="utf-8")

    class _Parser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.ok = True

        def error(self, message: str) -> None:
            self.ok = False

    parser = _Parser()
    parser.feed(report_text)

    assert parser.ok
    assert report_text.lstrip().lower().startswith("<!doctype html>")
    assert report_text.rstrip().lower().endswith("</html>")


def test_summary_prefers_run_result_wallclock(tmp_path: Path) -> None:
    run_dir = tmp_path / "wallclock"
    events = [
        _make_tool_event(
            event_type="request",
            tool="observe",
            wallclock=0.0,
            request={},
        ),
        _make_frame_event(wallclock=0.1, tool="observe", seen_by_agent=True, colour="green"),
    ]
    _write_trace(run_dir, events)
    (run_dir / "run_result.json").write_text(
        json.dumps(
            {
                "terminated_by": "wall_clock",
                "wallclock_s": 660.1,
                "final_message": "<wall-clock timeout - no final message>",
            }
        ),
        encoding="utf-8",
    )

    _run_renderer(run_dir)

    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["wallclock_seconds"] == 660.1
    assert summary["terminated_by"] == "wall_clock"


def test_renderer_renders_transcript_events_from_trace(tmp_path: Path) -> None:
    run_dir = tmp_path / "transcript-trace"
    events = [
        _make_tool_event(event_type="request", tool="observe", wallclock=0.0, request={}),
        _make_frame_event(wallclock=0.1, tool="observe", seen_by_agent=True, colour="green"),
        _make_transcript_event(
            wallclock=0.2,
            source="stream",
            content="Checking session",
            message_index=0,
            chunk_index=0,
        ),
        _make_transcript_event(
            wallclock=0.25,
            source="stream",
            content=" status.",
            message_index=0,
            chunk_index=1,
        ),
    ]
    _write_trace(run_dir, events)

    _run_renderer(run_dir)

    report_text = (run_dir / "report.html").read_text(encoding="utf-8")
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert "Transcript" in report_text
    assert "Checking session" in report_text
    assert "stream" in report_text
    assert summary["transcript_message_count"] == 2
    assert summary["transcript_source"] == "stream"


def test_renderer_falls_back_to_run_result_transcript_messages(tmp_path: Path) -> None:
    run_dir = tmp_path / "transcript-fallback"
    events = [
        _make_tool_event(event_type="request", tool="observe", wallclock=0.0, request={}),
        _make_frame_event(wallclock=0.1, tool="observe", seen_by_agent=True, colour="green"),
    ]
    _write_trace(run_dir, events)
    (run_dir / "run_result.json").write_text(
        json.dumps(
            {
                "terminated_by": "done",
                "wallclock_s": 12.0,
                "final_message": "done",
                "transcript_source": "terminal-body",
                "transcript_messages": [
                    {
                        "wallclock_s": 11.8,
                        "source": "terminal-body",
                        "content": "Done after checking the map.",
                        "message_index": 0,
                        "chunk_index": 0,
                        "is_final": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    _run_renderer(run_dir)

    report_text = (run_dir / "report.html").read_text(encoding="utf-8")
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert "Transcript" in report_text
    assert "terminal-body" in report_text
    assert "Done after checking the map." in report_text
    assert summary["transcript_message_count"] == 1
    assert summary["transcript_source"] == "terminal-body"


def test_transcript_free_runs_still_render_cleanly(tmp_path: Path) -> None:
    run_dir = tmp_path / "transcript-free"
    events = [
        _make_tool_event(event_type="request", tool="observe", wallclock=0.0, request={}),
        _make_frame_event(wallclock=0.1, tool="observe", seen_by_agent=True, colour="green"),
    ]
    _write_trace(run_dir, events)
    (run_dir / "run_result.json").write_text(
        json.dumps(
            {
                "terminated_by": "done",
                "wallclock_s": 1.0,
                "final_message": "done without transcript",
            }
        ),
        encoding="utf-8",
    )

    _run_renderer(run_dir)

    report_text = (run_dir / "report.html").read_text(encoding="utf-8")
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert "Final Message" in report_text
    assert "done without transcript" in report_text
    assert summary["transcript_message_count"] == 0
    assert summary["transcript_source"] == "none"
