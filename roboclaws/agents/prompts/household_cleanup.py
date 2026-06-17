"""Household live-agent kickoff prompts."""

from __future__ import annotations

import argparse

from roboclaws.household.raw_fpv_guidance import raw_fpv_inline_candidate_instruction
from roboclaws.household.task_intent import (
    TASK_INTENT_MODE_DEFAULT,
    household_intent_from_goal_contract,
    household_intent_is_open_ended,
    normalize_household_intent,
    normalize_task_intent_mode,
)
from roboclaws.household.visual_scan_guidance import visual_scan_prompt_rule
from roboclaws.launch.goals import GoalContract, goal_contract_from_json

TOOL_PROTOCOL_PREFIX = (
    "Use the cleanup MCP tool entries exactly as exposed by Codex; in text, "
    "refer to unprefixed tool names, and if the tool protocol requires a namespace "
    "use namespace cleanup, never mcp__cleanup__ or roboclaws__. "
)

COMMON_PREFIX = (
    "Use the bundled molmo-realworld-cleanup skill instructions. " + TOOL_PROTOCOL_PREFIX
)

CUSTOM_PREFIX = (
    "Use the bundled household-open-task skill instructions. "
    "Use the MCP tools as a bounded household robot capability surface. " + TOOL_PROTOCOL_PREFIX
)

COMMON_WAYPOINT_RULES = (
    "Call metric_map first, build an exact waypoint checklist "
    "from metric_map.inspection_waypoints, treat the selected Nav2 map bundle only "
    "through metric_map and runtime_metric_map, not raw occupancy images, sweep every "
    "waypoint with navigate_to_waypoint then observe, mark a waypoint complete only "
    "after that waypoint_id has an observe response, "
    "and resolve named targets, stale fixture ids, destination categories, or "
    "open-ended search terms through resolve_target_query and "
    "runtime_metric_map.target_candidates before acting on them; "
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

OPEN_ENDED_TASK_RULES = (
    "The operator task is the only goal. Do not start a room-cleanup routine, full "
    "waypoint sweep, visual-scan prerequisite, or pick/place chain unless the operator "
    "task itself requires it. Use metric_map, navigate_to_waypoint, "
    "resolve_target_query, observe, and adjust_camera only as needed to gather enough "
    "public evidence for the operator task. If the task names a target or stale label, "
    "resolve it through public target_candidates first; if no actionable match exists, "
    "continue public inspection while budget remains and include the public search "
    "budget in any not-found answer. If the task asks for information, report the "
    "answer and call "
    "done once satisfied. If the task requires manipulating an object, act only on "
    "task-relevant observed objects, use the public navigation/manipulation tools, "
    "and follow required_tool or public error responses. Do not call scene_objects or "
    "read private scoring artifacts. Do not treat unrelated pending cleanup candidates "
    "as part of the operator task. When the operator task is satisfied and you are not "
    "holding an object, call done so the report is generated."
)
HOUSEHOLD_CLEANUP_TASK_PREFIX = (
    "This run is surface=household-world intent=cleanup. User task: {task}. "
)
OPEN_ENDED_HOUSEHOLD_TASK_PREFIX = (
    "This run is surface=household-world with no task preset. "
    "The following operator task is authoritative: {task}. When this wrapper "
    "and the operator task conflict, follow the "
    "operator task subject to public tool safety and error responses. "
)
DEFAULT_HOUSEHOLD_CLEANUP_TASK = "clean up this room"
PROMPT_MODE_FULL = "full"
PROMPT_MODE_COMPACT = "compact"
PROMPT_MODE_RAW_FPV_COMPACT = "raw_fpv_compact"
PROMPT_MODES = {PROMPT_MODE_FULL, PROMPT_MODE_COMPACT, PROMPT_MODE_RAW_FPV_COMPACT}


def _normalize_task(task: str) -> str:
    return " ".join(str(task or "").split()) or DEFAULT_HOUSEHOLD_CLEANUP_TASK


def _task_prefix(
    task: str,
    *,
    task_intent_mode: str = TASK_INTENT_MODE_DEFAULT,
    household_intent: str = "",
    goal_contract: GoalContract | None = None,
) -> str:
    normalized = _normalize_task(task)
    if goal_contract is not None:
        return (
            f"This run is surface={goal_contract.surface} intent={goal_contract.intent}. "
            f"Normalized goal: {goal_contract.normalized_goal}. "
            f"Goal scope: {goal_contract.goal_scope}. Raw user goal: "
            f"{goal_contract.raw_prompt or normalized}. "
        )
    if household_intent_is_open_ended(household_intent):
        return OPEN_ENDED_HOUSEHOLD_TASK_PREFIX.format(task=normalized)
    return HOUSEHOLD_CLEANUP_TASK_PREFIX.format(task=normalized)


def _normalize_task_intent_mode(task_intent_mode: str) -> str:
    return normalize_task_intent_mode(task_intent_mode)


def _with_task(
    prompt: str,
    task: str,
    *,
    task_intent_mode: str = TASK_INTENT_MODE_DEFAULT,
    household_intent: str = "",
    goal_contract: GoalContract | None = None,
) -> str:
    prefix = CUSTOM_PREFIX if household_intent_is_open_ended(household_intent) else COMMON_PREFIX
    return (
        prefix
        + _task_prefix(
            task,
            task_intent_mode=task_intent_mode,
            household_intent=household_intent,
            goal_contract=goal_contract,
        )
        + prompt
    )


def _open_ended_scope_suffix() -> str:
    return (
        " In the no-preset household open-task mode, do not infer additional "
        "cleanup goals from cleanup implementation details."
    )


def _task_aware_prompt(
    prompt: str,
    *,
    task_intent_mode: str,
    household_intent: str,
) -> str:
    if household_intent_is_open_ended(household_intent):
        return prompt + _open_ended_scope_suffix()
    return prompt


def _normalize_prompt_mode(prompt_mode: str) -> str:
    mode = str(prompt_mode or PROMPT_MODE_FULL).strip() or PROMPT_MODE_FULL
    if mode not in PROMPT_MODES:
        raise ValueError(f"unsupported household cleanup prompt mode: {prompt_mode}")
    return mode


def _legacy_task_prefix(task: str) -> str:
    """Compatibility shim for callers/tests that imported the old helper."""

    normalized = " ".join(str(task or "").split()) or DEFAULT_HOUSEHOLD_CLEANUP_TASK
    return HOUSEHOLD_CLEANUP_TASK_PREFIX.format(task=normalized)


_task_prefix_legacy = _legacy_task_prefix


SEMANTIC_MAP_BUILD_RULES = (
    "This run is surface=household-world intent=map-build. "
    "This is not a cleanup run. User task: {task}. "
    "Do not pick, place, place_inside, open_receptacle, close_receptacle, or clean any "
    "object. Call metric_map first, build an exact waypoint "
    "checklist from metric_map.inspection_waypoints, and sweep every inspection "
    "waypoint with navigate_to_waypoint then observe. Mark a waypoint complete only "
    "after that waypoint_id has an observe response; do not treat one empty observation "
    "as enough to complete an ambiguous waypoint or target search. If a target query, "
    "visual candidate, anchor, or waypoint observation has incomplete public evidence, "
    "call adjust_camera within the public budget, observe again, and use the fresh "
    "observation before moving on. Use resolve_target_query for any target-search, "
    "stale label, or open-ended map question and leave not-found claims tied to the "
    "returned public search budget. If a public tool returns required_next_tool or "
    "required_tool, call that tool before continuing. If a target candidate is "
    "visible_only, needs_observe, or names a generated target-inspection candidate, "
    "navigate only to the public inspection waypoint returned by metric_map, "
    "resolve_target_query, or tool recovery, then observe again. For camera-grounded-labels, "
    "call declare_visual_candidates for each raw FPV observation with observation_id only "
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
    "runtime_metric_map.public_semantic_anchors, resolve_target_query, "
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

WORLD_LABELS_COMPACT_PROMPT = (
    "Compact action cadence for world-public-labels. Call metric_map, "
    "build the exact inspection_waypoints checklist, and for each unchecked waypoint call "
    "navigate_to_waypoint then observe. Treat visible_object_detections as public structured "
    "detections without destination oracle fields. Clean only public observed candidates whose "
    "candidate_state or tool response authorizes navigation. Use destination_policy, "
    "destination_options, runtime_metric_map.public_semantic_anchors, required_tool, and public "
    "recovery hints to choose placement; when the destination is named or stale, call "
    "resolve_target_query with operation=destination before choosing the public anchor. "
    "Prefer one short chain at a time: "
    "observe -> candidate decision -> navigate_to_object -> pick -> navigate_to_receptacle -> "
    "open? -> place/place_inside -> observe. Use place_inside for shelf/bookshelf/bookcase/"
    "shelving/fridge targets. If done reports pending_cleanup_candidates, clean only those "
    "public handles before another broad sweep. Call done when every public waypoint has an "
    "observe response and public pending candidates are resolved. Do not call scene_objects, "
    "read private scoring artifacts, invent fixture ids, or treat SDK turn completion as task "
    "success; only MCP done producing run_result.json counts."
)

CAMERA_LABELS_COMPACT_PROMPT = (
    "Compact action cadence for camera-grounded-labels. Call metric_map, "
    "build the exact inspection_waypoints checklist, and for each unchecked waypoint call "
    "navigate_to_waypoint then observe. For each raw FPV observation, call "
    "declare_visual_candidates with observation_id only and omit candidates so the configured "
    "camera labeler produces labels; do not ask for service URLs, credentials, image paths, or "
    "model hosts. Clean only returned public camera candidates whose candidate_state is "
    "navigation_authorized. Prefer one short chain at a time: observe -> declare labels -> "
    "candidate decision -> navigate_to_object -> pick -> navigate_to_receptacle -> open? -> "
    "place/place_inside -> observe. Use place_inside for shelf/bookshelf/bookcase/shelving/"
    "fridge targets. If done reports pending_cleanup_candidates, clean only those public "
    "handles before another broad sweep. Call done when every public waypoint has an observe "
    "response and public pending candidates are resolved. Do not call scene_objects, read "
    "private scoring artifacts, or treat SDK turn completion as task success; only MCP done "
    "producing run_result.json counts."
)

CAMERA_LABELS_COMPOSITE_COMPACT_PROMPT = (
    "Compact action cadence for camera-grounded-labels with the private SDK "
    "composite observation tool enabled. Call metric_map, build the exact "
    "inspection_waypoints checklist, and for each unchecked waypoint call "
    "navigate_to_waypoint then observe_camera_grounded_candidates instead of a "
    "separate observe plus declare_visual_candidates pair. Treat the response "
    "observation as the waypoint observe evidence and the response declaration "
    "as the camera-labeler candidate output; do not call "
    "declare_visual_candidates again for the same source_observation_id unless "
    "a public tool explicitly asks for it. Do not ask for service URLs, "
    "credentials, image paths, or model hosts. Clean only returned public camera "
    "candidates whose candidate_state is navigation_authorized. Prefer one "
    "short chain at a time: observe_camera_grounded_candidates -> candidate "
    "decision -> navigate_to_object -> pick -> navigate_to_receptacle -> "
    "open? -> place/place_inside -> observe_camera_grounded_candidates. Use "
    "place_inside for shelf/bookshelf/bookcase/shelving/fridge targets. If done "
    "reports pending_cleanup_candidates, clean only those public handles before "
    "another broad sweep. Call done when every public waypoint has observation "
    "evidence and public pending candidates are resolved. Do not call "
    "scene_objects, read private scoring artifacts, or treat SDK turn completion "
    "as task success; only MCP done producing run_result.json counts."
)


def _camera_raw_prompt(*, target_cleanup_count: int = 7) -> str:
    cleanup_count = max(1, int(target_cleanup_count))
    cleanup_count_text = str(cleanup_count)
    return (
        "This is the trace-preserving camera-raw-fpv skill lane. Call metric_map first, build "
        "an exact waypoint checklist from metric_map.inspection_waypoints, sweep every inspection "
        "waypoint with navigate_to_waypoint then observe, and mark a waypoint complete "
        "only after that waypoint_id has an observe response. Inspect each raw FPV "
        "image block returned by observe, do not expect structured labels, and choose "
        "at most one fresh high-confidence cleanup object from a source observation "
        "before moving, adjusting the camera, or observing again. Prefer objects with "
        "most of the item visible in the frame; skip tiny slivers, permanent fixtures, "
        "ambiguous decor, and areas already cleaned or already tried from that same "
        "source observation. " + raw_fpv_inline_candidate_instruction() + " "
        "Omit source_fixture_id with Base Navigation Map context. If visual candidate grounding is "
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


def _camera_raw_compact_prompt(
    *,
    target_cleanup_count: int = 7,
    raw_fpv_candidate_budget: int = 24,
    max_observe_per_waypoint: int = 1,
    done_retry_budget: int = 1,
) -> str:
    cleanup_count = max(1, int(target_cleanup_count))
    candidate_budget = max(1, int(raw_fpv_candidate_budget))
    observe_budget = max(1, int(max_observe_per_waypoint))
    done_budget = max(0, int(done_retry_budget))
    return (
        "Compact action cadence for camera-raw-fpv. Call metric_map, build "
        "the exact inspection_waypoints checklist, and sweep public waypoints with "
        "navigate_to_waypoint then observe. Inspect raw FPV image blocks directly; do not expect "
        "structured labels. At each waypoint, use at most "
        f"{observe_budget} observe response(s) before moving on unless a public tool error asks "
        "for a bounded camera adjustment. Choose at most one fresh high-confidence cleanup "
        "candidate per raw FPV observation and stay within the run budget of "
        f"{candidate_budget} raw-FPV candidate attempts. Never retry the same "
        "source_observation_id/category/region or visual-candidate id after a public failure. "
        + raw_fpv_inline_candidate_instruction()
        + " Omit source_fixture_id with Base Navigation Map context. Use "
        "navigate_to_visual_candidate -> pick -> navigate_to_receptacle -> open? -> "
        "place/place_inside when grounding succeeds, then observe once before choosing another "
        "candidate. Use place_inside for shelf/bookshelf/bookcase/shelving/fridge targets. If "
        "grounding is unresolved, record the public failure, move to another waypoint, or stop "
        "after the budget is exhausted; do not loop until provider context failure. Do not "
        "pre-register raw-FPV candidates with declare_visual_candidates. "
        f"Clean up to {cleanup_count} grounded visual candidates when possible. Call done only "
        "after every public waypoint has an observe response and successful cleanup chains meet "
        "the public gate, or after the bounded raw-FPV profile has no safe public candidate "
        f"remaining. If done reports blockers, retry done at most {done_budget} time(s) after "
        "resolving public blockers. Do not call scene_objects, read private scoring artifacts, "
        "persist raw image payloads, or treat SDK turn completion as task success; only MCP done "
        "producing run_result.json counts."
    )


def render_kickoff_prompt(
    profile: str,
    *,
    task: str = "",
    target_cleanup_count: int = 7,
    task_intent_mode: str = TASK_INTENT_MODE_DEFAULT,
    intent: str = "",
    goal_contract: GoalContract | None = None,
    prompt_mode: str = PROMPT_MODE_FULL,
    raw_fpv_candidate_budget: int = 24,
    max_observe_per_waypoint: int = 1,
    done_retry_budget: int = 1,
    camera_grounded_composite_tools: bool = False,
) -> str:
    """Render the live-agent kickoff prompt for a cleanup evidence lane."""

    intent_mode = _normalize_task_intent_mode(task_intent_mode)
    household_intent = household_intent_from_goal_contract(goal_contract, fallback=intent)
    household_intent = normalize_household_intent(household_intent)
    open_ended = household_intent_is_open_ended(household_intent)
    mode = _normalize_prompt_mode(prompt_mode)
    if profile == "camera-raw-fpv":
        prompt = _camera_raw_prompt(target_cleanup_count=target_cleanup_count)
        if mode == PROMPT_MODE_RAW_FPV_COMPACT:
            prompt = _camera_raw_compact_prompt(
                target_cleanup_count=target_cleanup_count,
                raw_fpv_candidate_budget=raw_fpv_candidate_budget,
                max_observe_per_waypoint=max_observe_per_waypoint,
                done_retry_budget=done_retry_budget,
            )
        return _with_task(
            _task_aware_prompt(
                OPEN_ENDED_TASK_RULES if open_ended else prompt,
                task_intent_mode=intent_mode,
                household_intent=household_intent,
            ),
            task,
            task_intent_mode=intent_mode,
            household_intent=household_intent,
            goal_contract=goal_contract,
        )
    if profile == "camera-grounded-labels":
        prompt = (
            CAMERA_LABELS_COMPACT_PROMPT if mode == PROMPT_MODE_COMPACT else CAMERA_LABELS_PROMPT
        )
        if mode == PROMPT_MODE_COMPACT and camera_grounded_composite_tools:
            prompt = CAMERA_LABELS_COMPOSITE_COMPACT_PROMPT
        return _with_task(
            _task_aware_prompt(
                OPEN_ENDED_TASK_RULES if open_ended else prompt,
                task_intent_mode=intent_mode,
                household_intent=household_intent,
            ),
            task,
            task_intent_mode=intent_mode,
            household_intent=household_intent,
            goal_contract=goal_contract,
        )
    if profile == "world-public-labels":
        prompt = (
            WORLD_LABELS_COMPACT_PROMPT
            if mode == PROMPT_MODE_COMPACT
            else WORLD_LABELS_SANITIZED_PROMPT
        )
        return _with_task(
            _task_aware_prompt(
                OPEN_ENDED_TASK_RULES if open_ended else prompt,
                task_intent_mode=intent_mode,
                household_intent=household_intent,
            ),
            task,
            task_intent_mode=intent_mode,
            household_intent=household_intent,
            goal_contract=goal_contract,
        )
    return _with_task(
        _task_aware_prompt(
            OPEN_ENDED_TASK_RULES if open_ended else COMMON_WAYPOINT_RULES + COMMON_CLEANUP_RULES,
            task_intent_mode=intent_mode,
            household_intent=household_intent,
        ),
        task,
        task_intent_mode=intent_mode,
        household_intent=household_intent,
        goal_contract=goal_contract,
    )


def render_semantic_map_build_prompt(profile: str, task: str) -> str:
    """Render the live-agent kickoff prompt for intent=map-build."""

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
    parser.add_argument("--intent", default="")
    parser.add_argument("--goal-contract-json", default="")
    parser.add_argument("--target-cleanup-count", type=int, default=7)
    parser.add_argument("--prompt-mode", default=PROMPT_MODE_FULL)
    parser.add_argument("--raw-fpv-candidate-budget", type=int, default=24)
    parser.add_argument("--max-observe-per-waypoint", type=int, default=1)
    parser.add_argument("--done-retry-budget", type=int, default=1)
    parser.add_argument("--camera-grounded-composite-tools", action="store_true")
    args = parser.parse_args(argv)
    goal_contract = goal_contract_from_json(args.goal_contract_json)
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
                intent=args.intent,
                goal_contract=goal_contract,
                prompt_mode=args.prompt_mode,
                raw_fpv_candidate_budget=args.raw_fpv_candidate_budget,
                max_observe_per_waypoint=args.max_observe_per_waypoint,
                done_retry_budget=args.done_retry_budget,
                camera_grounded_composite_tools=args.camera_grounded_composite_tools,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
