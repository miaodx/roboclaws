#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import io
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


GIF_DURATION_MS = 150
FRAME_EVENT = "frame_capture"
SEEN_BADGE = "👁"
UNSEEN_BADGE = "🚶"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-dir",
        type=Path,
        required=True,
        help="Directory containing trace.jsonl",
    )
    parser.add_argument(
        "--thumbnail-size",
        type=int,
        default=160,
        help="Max width of each frame thumbnail in report.html",
    )
    return parser.parse_args(argv)


def load_events(trace_path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        events.append(json.loads(stripped))
    return events


def extract_frame_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for event in events if event.get("event") == FRAME_EVENT]


def _strip_data_url(encoded: str) -> str:
    if encoded.startswith("data:") and "," in encoded:
        return encoded.split(",", 1)[1]
    return encoded


def _decode_jpeg(encoded: str, *, fallback_label: str) -> Image.Image:
    try:
        decoded = base64.b64decode(_strip_data_url(encoded))
        return Image.open(io.BytesIO(decoded)).convert("RGB")
    except Exception:
        return _placeholder_image(fallback_label)


def _placeholder_image(label: str) -> Image.Image:
    image = Image.new("RGB", (320, 240), (244, 244, 244))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, image.width - 1, image.height - 1), outline=(180, 180, 180), width=2)
    draw.text((12, 12), label, fill=(80, 80, 80))
    return image


def _image_to_array(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("RGB"), dtype=np.uint8)


def build_composite_images(frames: list[dict[str, Any]]) -> list[Image.Image]:
    from roboclaws.core.replay import _make_composite

    composite_images: list[Image.Image] = []
    for index, frame in enumerate(frames):
        fpv = _decode_jpeg(frame.get("fpv", ""), fallback_label=f"missing fpv #{index}")
        overhead = _decode_jpeg(
            frame.get("overhead", ""),
            fallback_label=f"missing overhead #{index}",
        )
        composite = _make_composite([_image_to_array(fpv)], _image_to_array(overhead))
        composite_images.append(composite)
    if composite_images:
        return composite_images
    return [_placeholder_image("No frame_capture events")]


def write_replay_gif(images: list[Image.Image], gif_path: Path) -> None:
    frames = [image.convert("P", palette=Image.Palette.ADAPTIVE) for image in images]
    first, rest = frames[0], frames[1:]
    first.save(
        gif_path,
        format="GIF",
        save_all=True,
        append_images=rest,
        duration=GIF_DURATION_MS,
        loop=0,
    )


def build_summary(events: list[dict[str, Any]], frames: list[dict[str, Any]]) -> dict[str, Any]:
    observe_events = [
        event
        for event in events
        if event.get("tool") == "observe" and event.get("event") == "request"
    ]
    move_events = [
        event for event in events if event.get("tool") == "move" and event.get("event") == "request"
    ]
    done_events = [
        event for event in events if event.get("tool") == "done" and event.get("event") == "request"
    ]
    seen_frames = [frame for frame in frames if frame.get("seen_by_agent") is True]
    unseen_frames = [frame for frame in frames if frame.get("seen_by_agent") is False]
    human_delivered = sum(
        1
        for event in events
        if event.get("event") == "response" and event.get("response", {}).get("human_message")
    )

    if move_events:
        observe_to_move_ratio = len(observe_events) / len(move_events)
    elif observe_events:
        observe_to_move_ratio = math.inf
    else:
        observe_to_move_ratio = 0.0

    wallclock_seconds = 0.0
    if frames:
        wallclock_seconds = max(
            0.0,
            float(frames[-1].get("wallclock_elapsed", 0.0))
            - float(frames[0].get("wallclock_elapsed", 0.0)),
        )

    return {
        "total_tool_calls": len(observe_events) + len(move_events) + len(done_events),
        "tool_calls_by_type": {
            "observe": len(observe_events),
            "move": len(move_events),
            "done": len(done_events),
        },
        "moves": len(move_events),
        "observes_by_agent": len(seen_frames),
        "frames_unseen_by_agent": len(unseen_frames),
        "observe_to_move_ratio": observe_to_move_ratio,
        "wallclock_seconds": wallclock_seconds,
        "terminated_by": "done" if done_events else "wall_clock",
        "human_messages_delivered": human_delivered,
    }


def _format_position(agent_state: dict[str, Any]) -> str:
    position = agent_state.get("position") or {}
    if isinstance(position, dict):
        x = position.get("x", "?")
        y = position.get("y", "?")
        z = position.get("z", "?")
        return f"x={x}, y={y}, z={z}"
    return str(position)


def build_timeline(frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    unseen_run = 0

    for frame in frames:
        seen_by_agent = bool(frame.get("seen_by_agent"))
        if not seen_by_agent:
            unseen_run += 1
        else:
            if unseen_run >= 5:
                timeline.append({"kind": "batched_warning", "count": unseen_run})
            unseen_run = 0

        agent_state = frame.get("agent_state", {})
        tooltip_lines = [
            f"t={float(frame.get('wallclock_elapsed', 0.0)):.1f}s",
            f"position={_format_position(agent_state if isinstance(agent_state, dict) else {})}",
        ]
        human_message = frame.get("human_message")
        if human_message:
            tooltip_lines.append(f"human_message={human_message}")

        timeline.append(
            {
                "kind": "frame",
                "seen_by_agent": seen_by_agent,
                "ts": float(frame.get("wallclock_elapsed", 0.0)),
                "fpv": frame.get("fpv", ""),
                "agent_state": agent_state,
                "human_message": human_message,
                "tooltip": "\n".join(tooltip_lines),
                "badge": SEEN_BADGE if seen_by_agent else UNSEEN_BADGE,
            }
        )

    if unseen_run >= 5:
        timeline.append({"kind": "batched_warning", "count": unseen_run})

    return timeline


def build_tool_log(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tool_log: list[dict[str, Any]] = []

    for event in events:
        event_type = event.get("event")
        tool = event.get("tool")

        if event_type == "request" and tool:
            request = event.get("request", {})
            summary = ""
            if tool == "move":
                summary = f"direction={request.get('direction', '?')}"
            elif tool == "done":
                summary = f"reason={request.get('reason', '?')}"
            elif tool == "observe":
                summary = "observe"

            tool_log.append(
                {
                    "ts": float(event.get("wallclock_elapsed", 0.0)),
                    "tool": tool,
                    "summary": summary,
                    "human_message": None,
                }
            )
            continue

        if event_type == "response" and tool:
            response = event.get("response", {})
            human_message = response.get("human_message")
            server_warning = response.get("server_warning")

            if human_message and tool_log and tool_log[-1]["tool"] == tool:
                tool_log[-1]["human_message"] = human_message

            if server_warning:
                tool_log.append(
                    {
                        "ts": float(event.get("wallclock_elapsed", 0.0)),
                        "tool": tool,
                        "summary": f"server_warning={server_warning}",
                        "human_message": human_message,
                    }
                )

    return tool_log


def render_report(
    *,
    run_dir: Path,
    summary: dict[str, Any],
    timeline: list[dict[str, Any]],
    tool_log: list[dict[str, Any]],
    thumbnail_size: int,
) -> Path:
    try:
        from jinja2 import Environment, FileSystemLoader
    except ImportError as exc:
        raise RuntimeError(
            "Jinja2 is required to render report.html. Install `jinja2` in the runtime "
            "environment before running this renderer."
        ) from exc

    template_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("autonomous_report.html.j2")
    html = template.render(
        run_id=run_dir.name,
        summary=summary,
        timeline=timeline,
        tool_log=tool_log,
        thumbnail_size=thumbnail_size,
    )
    report_path = run_dir / "report.html"
    report_path.write_text(html, encoding="utf-8")
    return report_path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    trace_path = args.run_dir / "trace.jsonl"
    if not trace_path.is_file():
        raise FileNotFoundError(f"trace.jsonl not found at {trace_path}")

    events = load_events(trace_path)
    frames = extract_frame_events(events)
    composite_images = build_composite_images(frames)
    write_replay_gif(composite_images, args.run_dir / "replay.gif")

    summary = build_summary(events, frames)
    (args.run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    render_report(
        run_dir=args.run_dir,
        summary=summary,
        timeline=build_timeline(frames),
        tool_log=build_tool_log(events),
        thumbnail_size=args.thumbnail_size,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
