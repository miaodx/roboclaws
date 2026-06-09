"""Household live-agent kickoff prompts."""

from __future__ import annotations

import argparse

from roboclaws.household.raw_fpv_guidance import raw_fpv_inline_candidate_instruction
from roboclaws.household.task_intent import (
    TASK_INTENT_MODE_CUSTOM,
    TASK_INTENT_MODE_DEFAULT,
    normalize_task_intent_mode,
)
from roboclaws.household.visual_scan_guidance import visual_scan_prompt_rule

TOOL_PROTOCOL_PREFIX = (
    "Use the cleanup MCP tool entries exactly as exposed by Codex; in text, "
    "refer to unprefixed tool names, and if the tool protocol requires a namespace "
    "use namespace cleanup, never mcp__cleanup__ or roboclaws__. "
)

COMMON_PREFIX = (
    "Use the bundled molmo-realworld-cleanup skill instructions. " + TOOL_PROTOCOL_PREFIX
)

CUSTOM_PREFIX = (
    "Use the MCP tools as a bounded household robot capability surface. " + TOOL_PROTOCOL_PREFIX
)

COMMON_WAYPOINT_RULES = (
    "Call metric_map and fixture_hints first, build an exact waypoint checklist "
    "from metric_map.inspection_waypoints, treat the selected Nav2 map bundle only "
    "through metric_map/fixture_hints and not raw occupancy images, sweep every "
    "waypoint with navigate_to_waypoint then observe, mark a waypoint complete only "
    "after that waypoint_id has an observe response, "
)

COMMON_CLEANUP_RULES = (
    "clean plausible observed objects only after their candidate_state is "
    f"navigation_authorized; {visual_scan_prompt_rule()} Clean with "
    "navigate->pick->navigate->open?->place/place_inside following required_tool "
    "if returned, use place_inside for "
    "shelf/bookshelf/bookcase/shelving/fridge targets, do not call scene_objects "
    "or read private scoring artifacts, compare the checklist before done, visit "
    "any missing waypoint_id, and call done only after every "
    "metric_map.inspection_waypoints waypoint_id has been observed so the report "
    "is generated."
)

CUSTOM_TASK_RULES = (
    "The operator task is the only goal. Do not start a room-cleanup routine, full "
    "waypoint sweep, visual-scan prerequisite, or pick/place chain unless the operator "
    "task itself requires it. Use metric_map, fixture_hints, navigate_to_waypoint, "
    "observe, and adjust_camera only as needed to gather enough public evidence for "
    "the operator task. If the task asks for information, report the answer and call "
    "done once satisfied. If the task requires manipulating an object, act only on "
    "task-relevant observed objects, use the public navigation/manipulation tools, "
    "and follow required_tool or public error responses. Do not call scene_objects or "
    "read private scoring artifacts. Do not treat unrelated pending cleanup candidates "
    "as part of the operator task. When the operator task is satisfied and you are not "
    "holding an object, call done so the report is generated."
)

HOUSEHOLD_CLEANUP_TASK_PREFIX = "This run is household-cleanup. User task: {task}. "
CUSTOM_HOUSEHOLD_TASK_PREFIX = (
    "This run is household-cleanup with a custom operator task. "
    "The following operator task is authoritative and overrides the default cleanup "
    "task: {task}. When this wrapper and the operator task conflict, follow the "
    "operator task subject to public tool safety and error responses. "
)

DEFAULT_HOUSEHOLD_CLEANUP_TASK = "clean up this room"


def _normalize_task(task: str) -> str:
    return " ".join(str(task or "").split()) or DEFAULT_HOUSEHOLD_CLEANUP_TASK


def _task_prefix(task: str, *, task_intent_mode: str = TASK_INTENT_MODE_DEFAULT) -> str:
    normalized = _normalize_task(task)
    if task_intent_mode == TASK_INTENT_MODE_CUSTOM:
        return CUSTOM_HOUSEHOLD_TASK_PREFIX.format(task=normalized)
    return HOUSEHOLD_CLEANUP_TASK_PREFIX.format(task=normalized)


def _normalize_task_intent_mode(task_intent_mode: str) -> str:
    return normalize_task_intent_mode(task_intent_mode)


def _with_task(
    prompt: str,
    task: str,
    *,
    task_intent_mode: str = TASK_INTENT_MODE_DEFAULT,
) -> str:
    prefix = CUSTOM_PREFIX if task_intent_mode == TASK_INTENT_MODE_CUSTOM else COMMON_PREFIX
    return prefix + _task_prefix(task, task_intent_mode=task_intent_mode) + prompt


def _custom_scope_suffix() -> str:
    return (
        " In custom operator task mode, do not infer additional cleanup goals from "
        "the household-cleanup route name."
    )


def _task_aware_prompt(prompt: str, *, task_intent_mode: str) -> str:
    if task_intent_mode == TASK_INTENT_MODE_CUSTOM:
        return prompt + _custom_scope_suffix()
    return prompt


def _legacy_task_prefix(task: str) -> str:
    """Compatibility shim for callers/tests that imported the old helper."""

    normalized = " ".join(str(task or "").split()) or DEFAULT_HOUSEHOLD_CLEANUP_TASK
    return HOUSEHOLD_CLEANUP_TASK_PREFIX.format(task=normalized)


_task_prefix_legacy = _legacy_task_prefix


SEMANTIC_MAP_BUILD_RULES = (
    "This run is semantic-map-build, not household-cleanup. User task: {task}. "
    "Do not pick, place, place_inside, open_receptacle, close_receptacle, or clean any "
    "object. Call metric_map first, then fixture_hints, build an exact waypoint "
    "checklist from metric_map.inspection_waypoints, and sweep every inspection "
    "waypoint with navigate_to_waypoint then observe. Mark a waypoint complete only "
    "after that waypoint_id has an observe response. For camera-grounded-labels, call "
    "declare_visual_candidates for each raw FPV observation with observation_id only "
    "and omit candidates so the configured camera labeler labels the "
    "frame. Use the returned observations and runtime_metric_map public anchors as "
    "map evidence only. Compare the checklist before done, visit any missing "
    "waypoint_id, and call done only after every metric_map.inspection_waypoints "
    "waypoint_id has been observed so runtime_metric_map.json and report.html are "
    "generated."
)

WORLD_LABELS_SANITIZED_PROMPT = (
    COMMON_WAYPOINT_RULES
    + "treat visible_object_detections as perfect structured detections without "
    "cleanup destination oracle fields; do not wait for or rely on "
    "cleanup_recommended, and treat every observed detection as a cleanup "
    "candidate to evaluate. If destination_policy_status is policy_required, "
    "use destination_policy.preferred_fixture_categories and "
    "destination_policy.placement_tool_by_fixture_category to select a matching "
    "public semantic anchor or fixture instead of skipping the object. If no "
    "matching public anchor or destination_options entry is available yet, "
    "continue the waypoint sweep rather than inventing fixture ids. After a "
    "successful placement, do not re-clean observed handles from that completed "
    "area. Treat public tool responses as authoritative: if done returns "
    "pending_cleanup_candidates, clean those listed handles using their "
    "candidate_fixture_id or destination_options and then call done again; if "
    "any tool returns required_tool, call that public tool next. Use metric_map, "
    "fixture_hints, runtime_metric_map.public_semantic_anchors, "
    "destination_policy, destination_options, and tool recovery hints to choose "
    "where to place observed objects. " + COMMON_CLEANUP_RULES
)

CAMERA_LABELS_PROMPT = (
    "When the next action is an MCP tool call, make that tool call before "
    "writing progress text and never end a turn by saying you will call a tool "
    "later. After every successful place/place_inside, immediately call observe "
    "before ending the turn or choosing another object. "
    + COMMON_WAYPOINT_RULES
    + "call declare_visual_candidates for each raw FPV observation before choosing "
    "cleanup candidates with observation_id only and omit candidates so the "
    "configured camera labeler produces labels, and treat returned "
    "candidates as coming from that pipeline without asking for service URLs, "
    "credentials, image paths, or model hosts. Clean plausible observed_* camera "
    "candidates with navigate->pick->navigate->open?->place/place_inside following "
    "required_tool if returned, use place_inside for shelf/bookshelf/bookcase/"
    "shelving/fridge targets, do not call scene_objects or read private scoring "
    "artifacts, compare the checklist before done, visit any missing waypoint_id, "
    "and call done only after every metric_map.inspection_waypoints waypoint_id "
    "has been observed so the report is generated."
)


def _camera_raw_prompt(*, target_cleanup_count: int = 7) -> str:
    cleanup_count = max(1, int(target_cleanup_count))
    cleanup_count_text = str(cleanup_count)
    return (
        "This is the trace-preserving camera-raw-fpv skill lane. Call metric_map and "
        "fixture_hints first, build an exact waypoint "
        "checklist from metric_map.inspection_waypoints, sweep every inspection "
        "waypoint with navigate_to_waypoint then observe, and mark a waypoint complete "
        "only after that waypoint_id has an observe response. Inspect each raw FPV "
        "image block returned by observe, do not expect structured labels, and choose "
        "at most one fresh high-confidence cleanup object from a source observation "
        "before moving, adjusting the camera, or observing again. Prefer objects with "
        "most of the item visible in the frame; skip tiny slivers, permanent fixtures, "
        "ambiguous decor, and areas already cleaned or already tried from that same "
        "source observation. " + raw_fpv_inline_candidate_instruction() + " "
        "Omit source_fixture_id in minimal map mode. If visual candidate grounding is "
        "unresolved, continue the waypoint sweep instead of calling done; if your "
        f"successful cleanup count is still below {cleanup_count_text}, reobserve from "
        "another public waypoint or adjust_camera once, observe again, and retry only "
        "with the fresh source_observation_id and a tighter bbox. Do not retry the same "
        "source_observation_id/category/region combination, and do not use a plain "
        "verbal_region as the evidence for a chain you need counted. When grounding "
        "succeeds, pick the returned object and place it using candidate_fixture_id and "
        "recommended_tool from the response when present, use place_inside for shelf/"
        "bookshelf/bookcase/shelving/fridge targets, and increment your successful "
        "cleanup count only after the place/place_inside succeeds. Immediately observe "
        "after each placement before selecting the next object. Do not pre-register "
        "raw-FPV candidates with declare_visual_candidates. "
        f"Clean at least {cleanup_count_text} grounded visual candidates with "
        "navigate_to_visual_candidate->pick->navigate_to_receptacle->open?->"
        "place/place_inside when grounding succeeds, do not call scene_objects or "
        "read private scoring artifacts, compare the checklist before done, visit any "
        "missing waypoint_id, and call done only after every "
        "metric_map.inspection_waypoints waypoint_id has been observed and at least "
        f"{cleanup_count_text} grounded cleanup chains have succeeded so the report is generated."
    )


def render_kickoff_prompt(
    profile: str,
    *,
    task: str = "",
    target_cleanup_count: int = 7,
    task_intent_mode: str = TASK_INTENT_MODE_DEFAULT,
) -> str:
    """Render the live-agent kickoff prompt for a cleanup evidence lane."""

    intent_mode = _normalize_task_intent_mode(task_intent_mode)
    if profile == "camera-raw-fpv":
        return _with_task(
            _task_aware_prompt(
                CUSTOM_TASK_RULES
                if intent_mode == TASK_INTENT_MODE_CUSTOM
                else _camera_raw_prompt(target_cleanup_count=target_cleanup_count),
                task_intent_mode=intent_mode,
            ),
            task,
            task_intent_mode=intent_mode,
        )
    if profile == "camera-grounded-labels":
        return _with_task(
            _task_aware_prompt(
                CUSTOM_TASK_RULES
                if intent_mode == TASK_INTENT_MODE_CUSTOM
                else CAMERA_LABELS_PROMPT,
                task_intent_mode=intent_mode,
            ),
            task,
            task_intent_mode=intent_mode,
        )
    if profile == "world-public-labels":
        return _with_task(
            _task_aware_prompt(
                CUSTOM_TASK_RULES
                if intent_mode == TASK_INTENT_MODE_CUSTOM
                else WORLD_LABELS_SANITIZED_PROMPT,
                task_intent_mode=intent_mode,
            ),
            task,
            task_intent_mode=intent_mode,
        )
    return _with_task(
        _task_aware_prompt(
            CUSTOM_TASK_RULES
            if intent_mode == TASK_INTENT_MODE_CUSTOM
            else COMMON_WAYPOINT_RULES + COMMON_CLEANUP_RULES,
            task_intent_mode=intent_mode,
        ),
        task,
        task_intent_mode=intent_mode,
    )


def render_semantic_map_build_prompt(profile: str, task: str) -> str:
    """Render the live-agent kickoff prompt for a semantic-map-build lane."""

    prompt = COMMON_PREFIX + SEMANTIC_MAP_BUILD_RULES.format(task=task)
    if profile == "camera-raw-fpv":
        return (
            prompt + " This is the raw-FPV map-build lane: inspect each raw FPV image block "
            "returned by observe, record only public map evidence, and do not declare "
            "cleanup candidates."
        )
    if profile == "world-public-labels":
        return (
            prompt + " Treat visible_object_detections as structured public detections without "
            "destination oracle fields; use them only as map labels."
        )
    return prompt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a household live-agent kickoff prompt.")
    parser.add_argument(
        "--profile",
        "--evidence-lane",
        dest="profile",
        default="world-oracle-labels",
    )
    parser.add_argument("--task-name", default="household-cleanup")
    parser.add_argument("--task", default="")
    parser.add_argument("--task-intent-mode", default=TASK_INTENT_MODE_DEFAULT)
    parser.add_argument("--target-cleanup-count", type=int, default=7)
    args = parser.parse_args(argv)
    if args.task_name == "semantic-map-build":
        task = args.task or "build a semantic map of this room"
        print(render_semantic_map_build_prompt(args.profile, task))
    else:
        print(
            render_kickoff_prompt(
                args.profile,
                task=args.task,
                target_cleanup_count=args.target_cleanup_count,
                task_intent_mode=args.task_intent_mode,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
