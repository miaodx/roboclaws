from __future__ import annotations

from pathlib import Path
from typing import Any

SEMANTIC_LOOP_VARIANT = "navigate-pick-navigate-open-place"
CURRENT_CONTRACT_SEMANTIC_LOOP_VARIANT = f"{SEMANTIC_LOOP_VARIANT}-object_done"
ROBOT_VIEW_VARIANT = "molmospaces-rby1m-fpv-map-chase-verify"


def record_robot_view_step(
    *,
    steps: list[dict[str, Any]],
    backend: Any,
    output_dir: Path,
    index: int,
    action: str,
    label_suffix: str,
    focus_object_id: str | None = None,
    focus_receptacle_id: str | None = None,
    semantic_phase: str | None = None,
) -> int:
    writer = getattr(backend, "write_robot_views", None)
    if not callable(writer):
        raise RuntimeError("robot view capture requires backend.write_robot_views")
    label = f"{index:04d}_{label_suffix}"
    result = writer(
        output_dir / "robot_views",
        label=label,
        focus_object_id=focus_object_id,
        focus_receptacle_id=focus_receptacle_id,
    )
    if not result.get("ok"):
        raise RuntimeError(f"robot view capture failed: {result}")
    steps.append(
        {
            "label": label,
            "action": action,
            "robot_pose": result.get("robot_pose"),
            "robot_trajectory_count": len(result.get("robot_trajectory", [])),
            "view_variant": result.get("view_variant"),
            "view_provenance": result.get("view_provenance"),
            "focus": result.get("focus"),
            "semantic_phase": semantic_phase,
            "room_outline_count": result.get("room_outline_count"),
            "views": relative_view_paths(output_dir, result["views"]),
        }
    )
    return index + 1


def robot_view_capture_for_tool(
    tool: str,
    request: dict[str, Any],
    response: dict[str, Any],
) -> dict[str, str | None] | None:
    if tool == "observe":
        return {
            "action": "observe",
            "label_suffix": "observe",
            "focus_object_id": None,
            "focus_receptacle_id": None,
            "semantic_phase": None,
        }
    if tool == "scene_objects":
        return {
            "action": "scene_objects",
            "label_suffix": "scene_objects",
            "focus_object_id": None,
            "focus_receptacle_id": None,
            "semantic_phase": None,
        }
    if tool == "navigate_to_object":
        object_id = optional_str(response.get("object_id") or request.get("object_id"))
        return {
            "action": f"navigate_to_object {object_id}",
            "label_suffix": label_suffix("navigate_object", object_id),
            "focus_object_id": object_id,
            "focus_receptacle_id": optional_str(
                response.get("source_receptacle_id") or response.get("location_id")
            ),
            "semantic_phase": "navigate_to_object",
        }
    if tool == "pick":
        object_id = optional_str(response.get("object_id") or request.get("object_id"))
        return {
            "action": f"pick {object_id}",
            "label_suffix": label_suffix("pick", object_id),
            "focus_object_id": object_id,
            "focus_receptacle_id": optional_str(
                response.get("previous_location_id") or response.get("source_receptacle_id")
            ),
            "semantic_phase": "pick",
        }
    if tool == "navigate_to_receptacle":
        object_id = optional_str(response.get("object_id"))
        receptacle_id = optional_str(response.get("receptacle_id") or request.get("receptacle_id"))
        return {
            "action": f"navigate_to_receptacle {receptacle_id}",
            "label_suffix": label_suffix("navigate_receptacle", receptacle_id),
            "focus_object_id": object_id,
            "focus_receptacle_id": receptacle_id,
            "semantic_phase": "navigate_to_receptacle",
        }
    if tool == "open_receptacle":
        object_id = optional_str(response.get("object_id"))
        receptacle_id = optional_str(response.get("receptacle_id") or request.get("receptacle_id"))
        return {
            "action": f"open_receptacle {receptacle_id}",
            "label_suffix": label_suffix("open_receptacle", receptacle_id),
            "focus_object_id": object_id,
            "focus_receptacle_id": receptacle_id,
            "semantic_phase": "open_receptacle",
        }
    if tool in {"place", "place_inside"}:
        object_id = optional_str(response.get("object_id"))
        receptacle_id = optional_str(response.get("receptacle_id") or request.get("receptacle_id"))
        return {
            "action": f"{tool} {object_id}",
            "label_suffix": label_suffix(tool, object_id),
            "focus_object_id": object_id,
            "focus_receptacle_id": receptacle_id,
            "semantic_phase": tool,
        }
    return None


def semantic_substeps(
    trace_events: list[dict[str, Any]],
    receptacles_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    steps_by_object: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    active_object_id: str | None = None

    for event in trace_events:
        if event.get("event") != "response":
            continue
        tool = str(event.get("tool", ""))
        if tool not in {
            "navigate_to_object",
            "pick",
            "navigate_to_receptacle",
            "open_receptacle",
            "place",
            "place_inside",
            "object_done",
        }:
            continue
        response = event.get("response")
        if not isinstance(response, dict):
            continue
        object_id = response.get("object_id") or active_object_id
        if tool == "navigate_to_object" and response.get("object_id"):
            object_id = str(response["object_id"])
            active_object_id = object_id
        elif tool == "pick" and response.get("ok") and response.get("object_id"):
            object_id = str(response["object_id"])
            active_object_id = object_id
        elif tool in {"place", "place_inside"} and response.get("ok"):
            active_object_id = None
        elif tool == "object_done" and response.get("object_id"):
            object_id = str(response["object_id"])

        if not object_id:
            continue
        object_id = str(object_id)
        if object_id not in steps_by_object:
            order.append(object_id)
            steps_by_object[object_id] = {
                "object_id": object_id,
                "source_receptacle_id": "",
                "target_receptacle_id": "",
                "target_receptacle_category": "",
                "steps": [],
            }
        item = steps_by_object[object_id]
        if response.get("source_receptacle_id"):
            item["source_receptacle_id"] = str(response["source_receptacle_id"])
        if response.get("receptacle_id"):
            target_id = str(response["receptacle_id"])
            item["target_receptacle_id"] = target_id
            item["target_receptacle_category"] = receptacle_category(
                receptacles_by_id,
                target_id,
            )
        item["steps"].append(semantic_step(tool, response))

    return [steps_by_object[object_id] for object_id in order]


def semantic_step(phase: str, response: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": phase,
        "tool": response.get("tool"),
        "ok": response.get("ok"),
        "status": response.get("status"),
        "error_reason": response.get("error_reason"),
        "object_id": response.get("object_id"),
        "receptacle_id": response.get("receptacle_id"),
        "source_receptacle_id": response.get("source_receptacle_id"),
        "location_id": response.get("location_id"),
        "contained_in": response.get("contained_in"),
        "location_relation": response.get("location_relation"),
        "opened": response.get("opened"),
        "matches_expected_location": response.get("matches_expected_location"),
        "primitive_provenance": response.get("primitive_provenance"),
    }


def cleanup_plan_from_semantic_substeps(
    substeps: list[dict[str, Any]],
) -> list[dict[str, str]]:
    plan = []
    for item in substeps:
        target = str(item.get("target_receptacle_id") or "")
        if not target:
            continue
        plan.append(
            {
                "object_id": str(item["object_id"]),
                "receptacle_id": target,
                "reason": "external agent selected semantic cleanup target",
            }
        )
    return plan


def semantic_diagnostics(
    trace_events: list[dict[str, Any]],
    substeps: list[dict[str, Any]],
    done_response: dict[str, Any],
) -> dict[str, Any]:
    stale_reference_errors = 0
    attempted_semantic_substeps = 0
    object_done_count = 0
    fridge_inside_sequence_ok = True
    complete_objects = 0
    for item in substeps:
        phases = [str(step.get("phase")) for step in item.get("steps", [])]
        attempted_semantic_substeps += len(phases)
        if "object_done" in phases:
            object_done_count += 1
        if has_complete_semantic_sequence(phases):
            complete_objects += 1
        if item.get("target_receptacle_category") == "Fridge":
            fridge_inside_sequence_ok = fridge_inside_sequence_ok and fridge_sequence_ok(phases)

    for event in trace_events:
        response = event.get("response")
        if (
            event.get("event") == "response"
            and isinstance(response, dict)
            and response.get("error_reason") == "stale_reference"
        ):
            stale_reference_errors += 1
    score = done_response.get("score", {})
    return {
        "stale_reference_errors": stale_reference_errors,
        "premature_done": int(score.get("restored_count", 0)) < int(score.get("total_targets", 0)),
        "object_done_count": object_done_count,
        "attempted_semantic_substeps": attempted_semantic_substeps,
        "complete_semantic_substep_objects": complete_objects,
        "fridge_inside_sequence_ok": fridge_inside_sequence_ok,
    }


def has_complete_semantic_sequence(phases: list[str]) -> bool:
    if phases[:3] != ["navigate_to_object", "pick", "navigate_to_receptacle"]:
        return False
    if phases[-1:] == ["object_done"]:
        return "place" in phases or "place_inside" in phases
    return phases[-1:] in (["place"], ["place_inside"])


def fridge_sequence_ok(phases: list[str]) -> bool:
    try:
        open_index = phases.index("open_receptacle")
        place_index = phases.index("place_inside")
    except ValueError:
        return False
    return open_index < place_index


def primitive_provenance_counts(trace_events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in trace_events:
        response = event.get("response")
        if not isinstance(response, dict):
            continue
        provenance = response.get("primitive_provenance")
        if provenance:
            counts[str(provenance)] = counts.get(str(provenance), 0) + 1
    return counts


def receptacle_category(receptacles_by_id: dict[str, dict[str, Any]], receptacle_id: str) -> str:
    receptacle = receptacles_by_id.get(receptacle_id, {})
    category = str(receptacle.get("category", ""))
    if category:
        return category
    name = str(receptacle.get("name", "")).lower()
    if "fridge" in name or "refrigerator" in name or "fridge" in receptacle_id.lower():
        return "Fridge"
    return ""


def label_suffix(prefix: str, value: str | None) -> str:
    if not value:
        return prefix
    safe_value = "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in value)
    return f"{prefix}_{safe_value}"


def optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def relative_view_paths(output_dir: Path, views: dict[str, str]) -> dict[str, str]:
    relative = {}
    for key, value in views.items():
        path = Path(value)
        try:
            relative[key] = str(path.relative_to(output_dir))
        except ValueError:
            relative[key] = str(path)
    return relative
