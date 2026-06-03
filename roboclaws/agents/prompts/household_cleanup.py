"""Household live-agent kickoff prompts."""

from __future__ import annotations

import argparse

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
    "clean plausible observed objects with navigate->pick->navigate->open?->"
    "place/place_inside following required_tool if returned, use place_inside for "
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
    "after that waypoint_id has an observe response. For camera-labels, call "
    "declare_visual_candidates for each raw FPV observation with observation_id only "
    "and omit candidates so the configured visual-grounding pipeline labels the "
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
    "public semantic anchor or fixture instead of skipping the object. After a "
    "successful placement, do not re-clean observed handles from that completed "
    "area. Once every metric_map.inspection_waypoints waypoint has been observed "
    "and held_object_id is empty, call done as the authoritative closeout probe "
    "before starting another optional cleanup chain; if done returns "
    "pending_cleanup_candidates, clean exactly those listed handles and then "
    "call done again. Use metric_map, fixture_hints, "
    "runtime_metric_map.public_semantic_anchors, destination_policy, and tool "
    "recovery hints to choose where to place observed objects. "
    + COMMON_CLEANUP_RULES
)

CAMERA_LABELS_PROMPT = (
    COMMON_PREFIX
    + "When the next action is an MCP tool call, make that tool call before "
    "writing progress text and never end a turn by saying you will call a tool "
    "later. After every successful place/place_inside, immediately call observe "
    "before ending the turn or choosing another object. "
    + COMMON_WAYPOINT_RULES
    + "call declare_visual_candidates for each raw FPV observation before choosing "
    "cleanup candidates with observation_id only and omit candidates so the "
    "configured visual-grounding pipeline produces labels, and treat returned "
    "candidates as coming from that pipeline without asking for service URLs, "
    "credentials, image paths, or model hosts. Clean plausible observed_* camera "
    "candidates with navigate->pick->navigate->open?->place/place_inside following "
    "required_tool if returned, use place_inside for shelf/bookshelf/bookcase/"
    "shelving/fridge targets, do not call scene_objects or read private scoring "
    "artifacts, compare the checklist before done, visit any missing waypoint_id, "
    "and call done only after every metric_map.inspection_waypoints waypoint_id "
    "has been observed so the report is generated."
)

CAMERA_RAW_PROMPT = (
    "Use the bundled molmo-realworld-cleanup skill instructions. This is the "
    "trace-preserving RAW_FPV skill lane. Use the cleanup MCP tool entries exactly "
    "as exposed by Codex; in text, refer to unprefixed tool names, and if the tool "
    "protocol requires a namespace use namespace cleanup, never mcp__cleanup__ or "
    "roboclaws__. Call metric_map and fixture_hints first, build an exact waypoint "
    "checklist from metric_map.inspection_waypoints, sweep every inspection "
    "waypoint with navigate_to_waypoint then observe, and mark a waypoint complete "
    "only after that waypoint_id has an observe response. Inspect each raw FPV "
    "image block returned by observe, do not expect structured labels, and when "
    "you see a plausible cleanup object call navigate_to_visual_candidate with "
    "source_observation_id, a broad category when uncertain (food, dish, book, "
    "linen, toy, electronics, pillow), evidence_note, and image_region before "
    "pick. In minimal map mode, do not invent fixture ids from empty fixture_hints; "
    "omit target_fixture_id and use the candidate_fixture_id/recommended_tool "
    "returned by navigate_to_visual_candidate plus runtime_metric_map."
    "public_semantic_anchors. In explicit rich legacy/debug mode only, "
    "target_fixture_id may come from non-empty fixture_hints. Prefer "
    "image_region={type:verbal_region,value:front of desk}; use "
    "image_region={type:bbox,value:[x,y,width,height]} only when you can estimate "
    'it confidently. Never send bbox_normalized, bare x/y/width/height fields, '
    'target_fixture_id="", target_fixture_id="None", or target_fixture_id=null. '
    "Omit source_fixture_id unless you are confident. If visual candidate grounding "
    "is unresolved, continue the waypoint sweep instead of calling done; if your "
    "successful cleanup count is still below seven, reobserve from another public "
    "waypoint or retry the candidate at most once with a broader category or "
    "clearer verbal_region. When grounding succeeds, pick the returned object and "
    "place it using candidate_fixture_id and recommended_tool from the response "
    "when present, use place_inside for shelf/bookshelf/bookcase/shelving/fridge "
    "targets, and increment your successful cleanup count only after the "
    "place/place_inside succeeds. Do not pre-register raw-FPV candidates with "
    "declare_visual_candidates. Clean at least seven grounded visual candidates "
    "with navigate_to_visual_candidate->pick->navigate_to_receptacle->open?->"
    "place/place_inside when grounding succeeds, do not call scene_objects or "
    "read private scoring artifacts, compare the checklist before done, visit any "
    "missing waypoint_id, and call done only after every "
    "metric_map.inspection_waypoints waypoint_id has been observed and at least "
    "seven grounded cleanup chains have succeeded so the report is generated."
)


def render_kickoff_prompt(profile: str) -> str:
    """Render the live-agent kickoff prompt for a cleanup input lane."""

    if profile == "camera-raw":
        return CAMERA_RAW_PROMPT
    if profile == "camera-labels":
        return CAMERA_LABELS_PROMPT
    if profile == "world-labels-sanitized":
        return WORLD_LABELS_SANITIZED_PROMPT
    return WORLD_LABELS_PROMPT


def render_semantic_map_build_prompt(profile: str, task: str) -> str:
    """Render the live-agent kickoff prompt for a semantic-map-build lane."""

    prompt = COMMON_PREFIX + SEMANTIC_MAP_BUILD_RULES.format(task=task)
    if profile == "camera-raw":
        return (
            prompt
            + " This is the raw-FPV map-build lane: inspect each raw FPV image block "
            "returned by observe, record only public map evidence, and do not declare "
            "cleanup candidates."
        )
    if profile == "world-labels-sanitized":
        return (
            prompt
            + " Treat visible_object_detections as structured public detections without "
            "destination oracle fields; use them only as map labels."
        )
    return prompt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a household live-agent kickoff prompt.")
    parser.add_argument("--profile", default="world-labels")
    parser.add_argument("--task-name", default="household-cleanup")
    parser.add_argument("--task", default="")
    args = parser.parse_args(argv)
    if args.task_name == "semantic-map-build":
        task = args.task or "build a semantic map of this room"
        print(render_semantic_map_build_prompt(args.profile, task))
    else:
        print(render_kickoff_prompt(args.profile))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
