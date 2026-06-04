from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

FRAME_CAPTURE_EVENT = "frame_capture"
ASSISTANT_TRANSCRIPT_EVENT = "assistant_transcript"
SNAPSHOT_ARCHIVE_VIEW_NAMES = ("fpv", "map", "chase")
SNAPSHOT_IMAGE_LABEL_TO_VIEWER_NAME: dict[str, str] = {
    "fpv": "fpv",
    "overhead": "map",
    "map_v2": "map",
    "chase": "chase",
}


@dataclass(frozen=True)
class ReplayReportContext:
    metadata: dict[str, Any]
    summary: dict[str, Any]
    steps: list[dict[str, Any]]
    provider_status: dict[str, Any]


def jsonify(obj: Any) -> Any:
    """Recursively convert numpy values to plain JSON-compatible objects."""
    if isinstance(obj, dict):
        return {k: jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonify(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def build_replay_step(
    *,
    step: int,
    agent_id: int,
    game_state: dict[str, Any],
    vlm_prompt_state: dict[str, Any],
    vlm_response: dict[str, Any],
    provider_status: dict[str, Any] | None = None,
    turn_metrics: dict[str, Any] | None = None,
    overhead_label: str = "overhead",
    extra_views: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return the durable replay.json step record."""
    return {
        "step": int(step),
        "agent_id": int(agent_id),
        "game_state": jsonify(game_state),
        "vlm_prompt_state": jsonify(vlm_prompt_state),
        "vlm_response": jsonify(vlm_response),
        "provider_status": jsonify(provider_status or {}),
        "turn_metrics": jsonify(turn_metrics or {}),
        "overhead_label": str(overhead_label),
        "extra_views": jsonify(extra_views or []),
    }


def build_replay_manifest(
    *,
    game: str,
    agent_count: int,
    duration_seconds: float,
    vlm_cost_usd: float,
    final_scores: dict[str, Any] | None = None,
    termination_reason: str = "unknown",
    provider_status: dict[str, Any] | None = None,
    steps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return the durable replay.json manifest."""
    resolved_steps = [jsonify(step) for step in (steps or [])]
    total_steps = len(resolved_steps)
    duration = round(float(duration_seconds), 2)
    cost = round(float(vlm_cost_usd), 6)
    return {
        "metadata": {
            "game": str(game),
            "agent_count": int(agent_count),
            "total_steps": total_steps,
            "duration_seconds": duration,
            "vlm_cost_usd": cost,
        },
        "summary": {
            "final_scores": jsonify(final_scores or {}),
            "total_steps": total_steps,
            "vlm_cost_usd": cost,
            "step_count": total_steps,
            "game_duration_seconds": duration,
            "termination_reason": str(termination_reason),
            "provider_status": jsonify(provider_status or {}),
        },
        "steps": resolved_steps,
    }


def build_replay_report_context(manifest: dict[str, Any]) -> ReplayReportContext:
    """Normalize replay manifest sections consumed by HTML reports."""
    metadata = manifest.get("metadata", {})
    summary = manifest.get("summary", {})
    steps = manifest.get("steps", [])
    if not isinstance(metadata, dict):
        metadata = {}
    if not isinstance(summary, dict):
        summary = {}
    if not isinstance(steps, list):
        steps = []
    provider_status = summary.get("provider_status", {}) or {}
    if not isinstance(provider_status, dict):
        provider_status = {}
    return ReplayReportContext(
        metadata=dict(metadata),
        summary=dict(summary),
        steps=[step for step in steps if isinstance(step, dict)],
        provider_status=dict(provider_status),
    )


def build_trace_event(
    *,
    tool: str,
    event: str,
    ts: float,
    wallclock_elapsed: float,
    **data: Any,
) -> dict[str, Any]:
    """Return one durable trace.jsonl event payload."""
    return {
        "ts": float(ts),
        "tool": str(tool),
        "event": str(event),
        "wallclock_elapsed": round(float(wallclock_elapsed), 6),
        **jsonify(data),
    }


def build_frame_capture_payload(
    *,
    seen_by_agent: bool,
    fpv: str,
    overhead: str,
    agent_state: dict[str, Any],
    view_variant: str | None = None,
    image_labels: list[str] | tuple[str, ...] | None = None,
    baseline_overhead: str | None = None,
    chase: str | None = None,
    decision_mode: str | None = None,
    human_message: str | None = None,
    move_direction: str | None = None,
    move_reason: str | None = None,
) -> dict[str, Any]:
    """Return the common frame_capture payload used by MCP traces and reports."""
    payload: dict[str, Any] = {
        "seen_by_agent": bool(seen_by_agent),
        "fpv": str(fpv),
        "overhead": str(overhead),
        "agent_state": jsonify(agent_state),
    }
    if view_variant is not None:
        payload["view_variant"] = str(view_variant)
    if image_labels is not None:
        payload["image_labels"] = [str(label) for label in image_labels]
    if baseline_overhead is not None:
        payload["baseline_overhead"] = str(baseline_overhead)
    if chase is not None:
        payload["chase"] = str(chase)
    if decision_mode is not None:
        payload["decision_mode"] = str(decision_mode)
    if human_message is not None:
        payload["human_message"] = str(human_message)
    if move_direction is not None:
        payload["move_direction"] = str(move_direction)
    if move_reason is not None:
        payload["move_reason"] = str(move_reason)
    return payload


def snapshot_view_name(image_label: str) -> str | None:
    """Map a prompt-image label to the stable viewer/snapshot file stem."""
    return SNAPSHOT_IMAGE_LABEL_TO_VIEWER_NAME.get(str(image_label))


def snapshot_png_filename(archive_stem: str, view_name: str) -> str:
    """Return the filename for one archived PNG."""
    return f"{archive_stem}.{view_name}.png"


def build_snapshot_archive_paths(
    *,
    container_dir: str,
    archive_stem: str,
    view_names: tuple[str, ...] = SNAPSHOT_ARCHIVE_VIEW_NAMES,
) -> dict[str, str]:
    """Return container-side MEDIA paths for archived observation PNGs."""
    normalized_dir = str(container_dir).rstrip("/")
    return {
        view_name: f"{normalized_dir}/{snapshot_png_filename(archive_stem, view_name)}"
        for view_name in view_names
    }


def build_snapshot_metrics(
    *,
    runtime_s: float,
    last_trace_age_s: float,
    queued_human_messages: int,
    observed_once: bool,
    moves_since_observe: int,
    done_event_set: bool,
    done_reason: str | None,
    tool_event_counts: dict[str, int],
) -> dict[str, Any]:
    """Return the frozen snapshot_metrics contract used in run_result.json."""
    return {
        "runtime_s": round(float(runtime_s), 3),
        "last_trace_age_s": round(float(last_trace_age_s), 3),
        "queued_human_messages": int(queued_human_messages),
        "observed_once": bool(observed_once),
        "moves_since_observe": int(moves_since_observe),
        "done_event_set": bool(done_event_set),
        "done_reason": done_reason,
        "tool_event_counts": dict(tool_event_counts),
    }


def build_run_result(
    *,
    terminated_by: str,
    wallclock_s: float,
    final_message: str | None,
    view_variant: str,
    model: str | None,
    bridge_metrics: dict[str, Any] | None,
    sim_server_metrics: dict[str, Any] | None,
    transcript_source: str | None,
    transcript_messages: list[dict[str, Any]] | None,
    diagnostics_files: dict[str, str] | None,
) -> dict[str, Any]:
    """Return the durable autonomous run_result.json payload."""
    return {
        "terminated_by": str(terminated_by),
        "wallclock_s": float(wallclock_s),
        "final_message": final_message,
        "view_variant": str(view_variant),
        "model": model,
        "bridge_metrics": jsonify(bridge_metrics or {}),
        "sim_server_metrics": jsonify(sim_server_metrics or {}),
        "transcript_source": transcript_source,
        "transcript_messages": jsonify(transcript_messages or []),
        "diagnostics_files": jsonify(diagnostics_files or {}),
    }


def extract_frame_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return frame_capture events from a trace."""
    return [event for event in events if event.get("event") == FRAME_CAPTURE_EVENT]


def extract_transcript_entries(
    events: list[dict[str, Any]],
    run_result: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return transcript entries from trace events, falling back to run_result.json."""
    transcript: list[dict[str, Any]] = []
    for event in events:
        if event.get("event") != ASSISTANT_TRANSCRIPT_EVENT:
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
                    entry.get("source") or run_result.get("transcript_source") or "unknown"
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


def build_autonomous_summary(
    *,
    events: list[dict[str, Any]],
    frames: list[dict[str, Any]],
    run_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the report summary for an autonomous MCP/OpenClaw run."""
    result = run_result or {}
    transcript_entries = extract_transcript_entries(events, result)
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
    done_count = len(done_request_events) or int(result.get("terminated_by") == "done")
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

    wallclock_seconds = float(result.get("wallclock_s", 0.0))
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
    elif result.get("transcript_source"):
        transcript_source = str(result.get("transcript_source"))

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
        "terminated_by": result.get("terminated_by") or ("done" if done_count else "wall_clock"),
        "human_messages_delivered": human_delivered,
        "transcript_message_count": len(transcript_entries),
        "transcript_source": transcript_source,
        "final_message": result.get("final_message"),
    }
