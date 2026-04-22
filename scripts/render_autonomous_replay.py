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
TRANSCRIPT_EVENT = "assistant_transcript"
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


def extract_transcript_entries(
    events: list[dict[str, Any]],
    run_result: dict[str, Any],
) -> list[dict[str, Any]]:
    transcript: list[dict[str, Any]] = []
    for event in events:
        if event.get("event") != TRANSCRIPT_EVENT:
            continue
        content = str(event.get("content", ""))
        if not content:
            continue
        transcript.append(
            {
                "ts": float(event.get("wallclock_elapsed", 0.0)),
                "source": str(event.get("source", "unknown")),
                "content": content,
                "is_final": bool(event.get("is_final", False)),
                "message_index": int(event.get("message_index", 0)),
                "chunk_index": int(event.get("chunk_index", 0)),
            }
        )
    if transcript:
        return sorted(
            transcript,
            key=lambda entry: (entry["ts"], entry["message_index"], entry["chunk_index"]),
        )

    run_result_messages = run_result.get("transcript_messages")
    if not isinstance(run_result_messages, list):
        return []
    fallback: list[dict[str, Any]] = []
    for index, entry in enumerate(run_result_messages):
        if not isinstance(entry, dict):
            continue
        content = str(entry.get("content", ""))
        if not content:
            continue
        fallback.append(
            {
                "ts": float(entry.get("wallclock_s", 0.0)),
                "source": str(
                    entry.get("source")
                    or run_result.get("transcript_source")
                    or "unknown"
                ),
                "content": content,
                "is_final": bool(entry.get("is_final", False)),
                "message_index": int(entry.get("message_index", 0)),
                "chunk_index": int(entry.get("chunk_index", index)),
            }
        )
    return sorted(
        fallback,
        key=lambda entry: (entry["ts"], entry["message_index"], entry["chunk_index"]),
    )


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


def _embed_image(encoded: str, *, trim_border: bool = False) -> str:
    if not encoded:
        return ""
    image = _decode_jpeg(encoded, fallback_label="missing frame")
    if trim_border:
        image = _trim_uniform_border(image)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _format_panel_label(label: str) -> str:
    normalized = str(label).replace("-", "_").strip("_ ")
    if not normalized:
        return "View"
    parts = [part for part in normalized.split("_") if part]
    pretty: list[str] = []
    for part in parts:
        upper = part.upper()
        if upper in {"FPV", "VLM"}:
            pretty.append(upper)
        elif part.isdigit():
            pretty.append(part)
        else:
            pretty.append(part.capitalize())
    return " ".join(pretty)


def _normalize_panel_key(label: str) -> str:
    return str(label).replace("-", "_").strip("_ ").lower()


def _ordered_panel_labels(labels: list[str]) -> list[str]:
    preferred = {"fpv": 0, "chase": 1, "map_v2": 2, "overhead": 3}
    return sorted(labels, key=lambda value: (preferred.get(_normalize_panel_key(value), 50), value))


def _trim_uniform_border(image: Image.Image, tolerance: int = 10, padding: int = 2) -> Image.Image:
    rgb = image.convert("RGB")
    width, height = rgb.size
    if width < 3 or height < 3:
        return rgb

    arr = np.asarray(rgb, dtype=np.int16)
    corners = np.asarray(
        [arr[0, 0], arr[0, -1], arr[-1, 0], arr[-1, -1]],
        dtype=np.int16,
    )
    if np.abs(corners - corners[0]).max() > tolerance:
        return rgb

    background = corners.mean(axis=0)
    mask = np.abs(arr - background).max(axis=2) > tolerance
    if not mask.any():
        return rgb

    ys, xs = np.where(mask)
    top = max(0, int(ys.min()) - padding)
    bottom = min(height, int(ys.max()) + padding + 1)
    left = max(0, int(xs.min()) - padding)
    right = min(width, int(xs.max()) + padding + 1)
    if top == 0 and left == 0 and bottom == height and right == width:
        return rgb
    return rgb.crop((left, top, right, bottom))


def _frame_panels(frame: dict[str, Any]) -> list[tuple[str, str]]:
    image_labels = [str(label) for label in frame.get("image_labels", [])]
    panels: list[tuple[str, str]] = [("fpv", str(frame.get("fpv", "")))]

    primary_label = image_labels[1] if len(image_labels) > 1 else "overhead"
    panels.append((primary_label, str(frame.get("overhead", ""))))

    if frame.get("baseline_overhead") and primary_label != "overhead":
        panels.append(("overhead", str(frame.get("baseline_overhead", ""))))

    chase_label = image_labels[2] if len(image_labels) > 2 else "chase"
    if frame.get("chase"):
        existing_labels = {label for label, _ in panels}
        if chase_label not in existing_labels:
            panels.append((chase_label, str(frame.get("chase", ""))))

    return panels


def build_composite_images(frames: list[dict[str, Any]]) -> list[Image.Image]:
    from roboclaws.core.replay import _make_composite

    composite_images: list[Image.Image] = []
    for index, frame in enumerate(frames):
        panels = _frame_panels(frame)
        fpv = _decode_jpeg(panels[0][1], fallback_label=f"missing fpv #{index}")
        if len(panels) >= 2:
            primary = _decode_jpeg(
                panels[1][1],
                fallback_label=f"missing {panels[1][0]} #{index}",
            )
            extra_frames = [
                _image_to_array(_decode_jpeg(encoded, fallback_label=f"missing {label} #{index}"))
                for label, encoded in panels[2:]
            ]
        else:
            primary = _placeholder_image(f"missing overhead #{index}")
            extra_frames = []
        composite = _make_composite(
            [_image_to_array(fpv)],
            _image_to_array(primary),
            extra_frames=extra_frames,
        )
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
    return _build_summary_from_events(events, frames, {})


def _build_summary_from_events(
    events: list[dict[str, Any]],
    frames: list[dict[str, Any]],
    run_result: dict[str, Any],
) -> dict[str, Any]:
    transcript_entries = extract_transcript_entries(events, run_result)
    observe_request_events = [
        event
        for event in events
        if event.get("tool") == "observe" and event.get("event") == "request"
    ]
    move_request_events = [
        event for event in events if event.get("tool") == "move" and event.get("event") == "request"
    ]
    done_request_events = [
        event for event in events if event.get("tool") == "done" and event.get("event") == "request"
    ]
    seen_frames = [frame for frame in frames if frame.get("seen_by_agent") is True]
    unseen_frames = [frame for frame in frames if frame.get("seen_by_agent") is False]
    observe_count = len(observe_request_events) or sum(
        1 for frame in frames if frame.get("tool") == "observe"
    )
    move_count = len(move_request_events) or sum(
        1 for frame in frames if frame.get("tool") == "move"
    )
    done_count = len(done_request_events) or int(run_result.get("terminated_by") == "done")
    decision_modes = {
        "fresh_observe": 0,
        "reasoned_batch": 0,
        "blind_batch": 0,
    }
    for frame in frames:
        if frame.get("tool") != "move":
            continue
        decision_mode = str(frame.get("decision_mode", ""))
        if decision_mode in decision_modes:
            decision_modes[decision_mode] += 1
    human_delivered = sum(
        1
        for event in events
        if event.get("event") == "response" and event.get("response", {}).get("human_message")
    )

    if move_count:
        observe_to_move_ratio = observe_count / move_count
    elif observe_count:
        observe_to_move_ratio = math.inf
    else:
        observe_to_move_ratio = 0.0

    wallclock_seconds = float(run_result.get("wallclock_s", 0.0))
    if wallclock_seconds <= 0.0 and frames:
        wallclock_seconds = max(
            0.0,
            float(frames[-1].get("wallclock_elapsed", 0.0))
            - float(frames[0].get("wallclock_elapsed", 0.0)),
        )

    latest_frame = frames[-1] if frames else {}
    transcript_source = "none"
    if transcript_entries:
        transcript_source = str(transcript_entries[0].get("source", "none"))
    elif run_result.get("transcript_source"):
        transcript_source = str(run_result.get("transcript_source"))

    return {
        "total_tool_calls": observe_count + move_count + done_count,
        "tool_calls_by_type": {
            "observe": observe_count,
            "move": move_count,
            "done": done_count,
        },
        "moves": move_count,
        "observes_by_agent": len(seen_frames),
        "frames_unseen_by_agent": len(unseen_frames),
        "observe_to_move_ratio": observe_to_move_ratio,
        "decision_modes": decision_modes,
        "wallclock_seconds": wallclock_seconds,
        "frame_count": len(frames),
        "view_variant": latest_frame.get("view_variant", "baseline"),
        "terminated_by": (
            run_result.get("terminated_by") or ("done" if done_count else "wall_clock")
        ),
        "human_messages_delivered": human_delivered,
        "transcript_message_count": len(transcript_entries),
        "transcript_source": transcript_source,
        "final_message": run_result.get("final_message"),
    }


def _format_position(agent_state: dict[str, Any]) -> str:
    position = agent_state.get("position") or {}
    if isinstance(position, dict):
        x = position.get("x", "?")
        y = position.get("y", "?")
        z = position.get("z", "?")
        return f"x={x}, y={y}, z={z}"
    return str(position)


def _decision_descriptor(frame: dict[str, Any]) -> tuple[str, str]:
    if frame.get("tool") == "observe":
        return ("fresh observation", "observe")

    decision_mode = frame.get("decision_mode")
    if decision_mode == "fresh_observe":
        return ("fresh observe-driven move", "fresh-observe")
    if decision_mode == "reasoned_batch":
        reason = str(frame.get("move_reason", "")).strip()
        if reason:
            return (f"reasoned continuation: {reason}", "reasoned-batch")
        return ("reasoned continuation", "reasoned-batch")
    if decision_mode == "blind_batch":
        return ("blind batch", "blind-batch")
    return ("move", "move")


def build_frame_data(frames: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    panel_labels: list[str] = []
    frame_data: list[dict[str, Any]] = []
    for index, frame in enumerate(frames):
        seen_by_agent = bool(frame.get("seen_by_agent"))
        decision_label, decision_class = _decision_descriptor(frame)
        agent_state = frame.get("agent_state", {})
        tool = str(frame.get("tool", "frame"))
        move_direction = frame.get("move_direction")
        tooltip_lines = [
            f"t={float(frame.get('wallclock_elapsed', 0.0)):.1f}s",
            f"tool={tool}",
            f"decision={decision_label}",
            f"position={_format_position(agent_state if isinstance(agent_state, dict) else {})}",
        ]
        if move_direction:
            tooltip_lines.append(f"direction={move_direction}")
        human_message = frame.get("human_message")
        if human_message:
            tooltip_lines.append(f"human_message={human_message}")

        panel_map: dict[str, str] = {}
        for label, encoded in _frame_panels(frame):
            panel_map[label] = _embed_image(
                encoded,
                trim_border=_normalize_panel_key(label) == "overhead",
            )
            if label not in panel_labels:
                panel_labels.append(label)

        frame_data.append(
            {
                "index": index,
                "seen_by_agent": seen_by_agent,
                "ts": float(frame.get("wallclock_elapsed", 0.0)),
                "_panel_map": panel_map,
                "agent_state": agent_state,
                "human_message": human_message,
                "tooltip": "\n".join(tooltip_lines),
                "badge": SEEN_BADGE if seen_by_agent else UNSEEN_BADGE,
                "decision_label": decision_label,
                "decision_class": decision_class,
                "tool": tool,
                "move_direction": move_direction,
                "position": _format_position(agent_state if isinstance(agent_state, dict) else {}),
            }
        )
    if not panel_labels:
        panel_labels = ["fpv", "overhead"]
    panel_labels = _ordered_panel_labels(panel_labels)
    for frame in frame_data:
        panel_map = frame.pop("_panel_map")
        frame["panel_images"] = [panel_map.get(label, "") for label in panel_labels]
    return panel_labels, frame_data


def build_tool_log(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tool_log: list[dict[str, Any]] = []

    for event in events:
        event_type = event.get("event")
        tool = event.get("tool")

        if event_type == "request" and tool:
            request = event.get("request", {})
            summary = ""
            if tool == "move":
                summary_parts = [f"direction={request.get('direction', '?')}"]
                reason = str(request.get("reason", "")).strip()
                if reason:
                    summary_parts.append(f"reason={reason}")
                summary = " ".join(summary_parts)
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
    transcript: list[dict[str, Any]],
    panel_labels: list[str],
    frame_data: list[dict[str, Any]],
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
        transcript=transcript,
        panel_headers=[_format_panel_label(label) for label in panel_labels],
        panel_count=len(panel_labels),
        frames_json=json.dumps(frame_data),
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

    run_result_path = args.run_dir / "run_result.json"
    run_result = {}
    if run_result_path.is_file():
        run_result = json.loads(run_result_path.read_text(encoding="utf-8"))
    summary = _build_summary_from_events(events, frames, run_result)
    (args.run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    transcript = extract_transcript_entries(events, run_result)
    panel_labels, frame_data = build_frame_data(frames)

    render_report(
        run_dir=args.run_dir,
        summary=summary,
        transcript=transcript,
        panel_labels=panel_labels,
        frame_data=frame_data,
        tool_log=build_tool_log(events),
        thumbnail_size=args.thumbnail_size,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
