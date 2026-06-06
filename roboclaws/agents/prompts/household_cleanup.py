"""Household live-agent kickoff prompts."""

from __future__ import annotations

import argparse

from roboclaws.household.raw_fpv_guidance import raw_fpv_inline_candidate_instruction

COMMON_PREFIX = (
    "Use the bundled molmo-realworld-cleanup skill instructions. "
    "Use the cleanup MCP tool entries exactly as exposed by Codex; in text, "
    "refer to unprefixed tool names, and if the tool protocol requires a namespace "
    "use namespace cleanup, never mcp__cleanup__ or roboclaws__. "
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
    "navigation_authorized; if a world-label object is visual_scan_required, call "
    "adjust_camera toward it, then observe, then use the refreshed same-handle "
    "source FPV bbox before navigate_to_object. Clean with "
    "navigate->pick->navigate->open?->place/place_inside following required_tool "
    "if returned, use place_inside for "
    "shelf/bookshelf/bookcase/shelving/fridge targets, do not call scene_objects "
    "or read private scoring artifacts, compare the checklist before done, visit "
    "any missing waypoint_id, and call done only after every "
    "metric_map.inspection_waypoints waypoint_id has been observed so the report "
    "is generated."
)

WORLD_LABELS_PROMPT = COMMON_PREFIX + COMMON_WAYPOINT_RULES + COMMON_CLEANUP_RULES

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
    COMMON_PREFIX
    + COMMON_WAYPOINT_RULES
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
    COMMON_PREFIX + "When the next action is an MCP tool call, make that tool call before "
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
        "Use the bundled molmo-realworld-cleanup skill instructions. This is the "
        "trace-preserving camera-raw-fpv skill lane. Use the cleanup MCP tool entries exactly "
        "as exposed by Codex; in text, refer to unprefixed tool names, and if the tool "
        "protocol requires a namespace use namespace cleanup, never mcp__cleanup__ or "
        "roboclaws__. Call metric_map and fixture_hints first, build an exact waypoint "
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


def render_kickoff_prompt(profile: str, *, target_cleanup_count: int = 7) -> str:
    """Render the live-agent kickoff prompt for a cleanup evidence lane."""

    if profile == "camera-raw-fpv":
        return _camera_raw_prompt(target_cleanup_count=target_cleanup_count)
    if profile == "camera-grounded-labels":
        return CAMERA_LABELS_PROMPT
    if profile == "world-public-labels":
        return WORLD_LABELS_SANITIZED_PROMPT
    return WORLD_LABELS_PROMPT


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
    parser.add_argument("--target-cleanup-count", type=int, default=7)
    args = parser.parse_args(argv)
    if args.task_name == "semantic-map-build":
        task = args.task or "build a semantic map of this room"
        print(render_semantic_map_build_prompt(args.profile, task))
    else:
        print(render_kickoff_prompt(args.profile, target_cleanup_count=args.target_cleanup_count))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
