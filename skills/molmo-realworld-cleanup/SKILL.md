---
name: molmo-realworld-cleanup
description: Drive the ADR-0003 MolmoSpaces real-world cleanup MCP contract.
metadata:
  openclaw:
    emoji: M
---

# Molmo Real-World Cleanup

Use only the `roboclaws__*` MCP tools. This is the ADR-0003 contract: there is
no `scene_objects` tool, no target list, and no hidden destination table.

## Loop

1. Call `roboclaws__metric_map()` first.
2. Treat `inspection_waypoints` as public coverage candidates, not mess hints.
   In the default minimal map mode, authored room and fixture labels are hidden:
   useful destination anchors come from `cleanup_worklist.candidate_fixture_id`,
   `runtime_metric_map.public_semantic_anchors`, `resolve_target_query`, and
   successful tool responses.
   For any named destination, stale fixture id, old label, or open-ended target
   request, call `roboclaws__resolve_target_query(query, operation=...)` or use
   the same public `runtime_metric_map.target_candidates` resolution logic
   before choosing a waypoint or anchor. A match may still be non-actionable:
   follow its `required_next_tool` and `target_actionability_status` instead of
   navigating, picking, or placing from the raw query text. A `not_found`
   answer is valid only when the returned `public_search_budget` shows the
   inspected viewpoints and remaining budget; otherwise continue the public
   waypoint/camera search.
   Build an exact checklist from
   `metric_map.inspection_waypoints`, then for each useful waypoint or
   current-room area, call
   `roboclaws__navigate_to_waypoint(waypoint_id)`, then
   `roboclaws__observe()`. Mark a waypoint complete only after an `observe`
   response at that `waypoint_id`; before `done`, compare the checklist against
   observed waypoint ids and visit any missing waypoint. Build your own semantic
   map from returned `observed_*` object handles and support estimates.
   `navigate_to_waypoint` may return `navigation_backend:
   sim_costmap_planner` with `route_validation`; treat `ok: false` /
   `blocked_capability` as a real navigation failure and choose another public
   waypoint instead of inventing hidden targets or reading map images directly.
   In `camera-raw-fpv` runs, `observe()` returns raw FPV image evidence instead of
   structured labels. Inspect the image, select at most one fresh
   high-confidence cleanup object from that source observation, then call
   `roboclaws__navigate_to_visual_candidate(source_observation_id, category,
   evidence_note, image_region, ...)` only when you intend to act on a visual
   candidate. Omit `target_fixture_id` in minimal map mode until grounding
   returns a public `candidate_fixture_id`; do not invent fixture ids from stale
   map labels. In minimal map mode, normally omit `source_fixture_id` too; do
   not guess it from room context. Do not pre-register raw-FPV candidates with
   `roboclaws__declare_visual_candidates`; that producer-registration path is
   for `camera-grounded-labels`. Prefer the exact visual class when the image makes it
   clear (`plate`, `cup`, `potato`, `remotecontrol`, `book`, `pillow`); use
   broad cleanup categories when uncertain (`food`, `dish`, `book`, `linen`,
   `toy`, `electronics`, `pillow`) instead of over-specific guesses that are
   likely to miss the public grounding resolver.
   Prefer objects with most of the item visible in the frame. Skip permanent
   fixtures, built-in appliances, wall decor, tiny slivers, reflections, and
   regions already cleaned or already tried from that same source observation.
   Use a reviewable bbox region for any candidate you need counted:
   `{"type":"bbox","value":[x,y,width,height]}`. A verbal region can clarify a
   bbox, but it is not enough for an actionable cleanup chain; do not send a bare
   `{x,y,width,height}` object. When `navigate_to_visual_candidate` resolves, use
   its returned `candidate_fixture_id` and `recommended_tool` for placement if
   present.
   Maintain a count of successful grounded cleanup actions. In `camera-raw-fpv`
   acceptance runs, use the target cleanup count from the kickoff prompt or
   public run configuration; do not call `done` before that many grounded visual
   candidates have been successfully cleaned. If grounding stays unresolved and
   the success count is still below that target, continue sweeping or reobserve
   from another public waypoint. You may `adjust_camera` once, observe again,
   and retry with the fresh `source_observation_id` and a tighter bbox; do not
   loop on the same source observation/category/region.
   After a successful pick/place for an observed handle, do not act on that same
   handle again. If a later raw-FPV declaration resolves to an already-handled
   object, continue the waypoint sweep and observe for other objects instead of
   navigating to that handle again.
   If raw-FPV visual grounding is unresolved, continue the waypoint sweep; do
   not call `done` as a system-assessment shortcut while map waypoints remain
   unvisited.
   In `camera-grounded-labels` runs, use
   `roboclaws__declare_visual_candidates()` to register producer-labelled
   candidates before cleanup selection.
   For `semantic-map-build`, use the same public map and target tools but do
   not run cleanup actions. Map-build waypoints are coverage candidates, not
   one-shot observations: when a target query, visual candidate, anchor, or
   waypoint observation is incomplete, use one bounded
   `roboclaws__adjust_camera()` -> `roboclaws__observe()` retry when public
   camera budget remains. If a target candidate is `visible_only`,
   `needs_observe`, or references a generated target-inspection candidate,
   convert it only through the public waypoint returned by
   `metric_map`, `resolve_target_query`, or tool recovery, then observe from
   that waypoint before calling it actionable. A `not_found` map-build answer
   must cite the public search budget, inspected viewpoints, and any camera
   adjustment attempts.
3. Prefer a local cleanup loop after each useful observation instead of a full
   up-front survey. Clean plausible misplaced objects with only observed
   object handles using the Trace-Preserving Skill Routine below.
   Keep run-local strategy notes in `cleanup_scratch.json` if useful, but treat
   that scratchpad as non-authoritative. The contract-derived
   `cleanup_worklist` in Agent View and `done` recovery payloads are the facts
   that decide pending work.
   If a visible detection or done recovery response includes
   `cleanup_recommended: true` or a `candidate_fixture_id` that differs from
   its `support_estimate.fixture_id`, treat that public candidate as cleanup
   work and use the `candidate_fixture_id` as the target. Do not leave such a
   handle pending just because the current surface looks plausible.
   In `world-public-labels`, detections intentionally omit
   `candidate_fixture_id`, `cleanup_recommended`, and `recommended_tool`.
   Treat `destination_policy` as public category/fixture-affordance guidance:
   resolve each preferred category through `resolve_target_query` with
   `operation=destination`, then match the returned public anchors against
   `runtime_metric_map.public_semantic_anchors` or other public fixture
   evidence. Use `destination_policy.placement_tool` unless a tool recovery
   response requires a different public tool. When
   `destination_policy.placement_tool_by_fixture_category` has an entry for the
   matched public fixture category, use that entry. This policy is not private
   destination truth; it only says which public fixture categories are
   semantically suitable. If no matching public anchor or
   `destination_options.candidate_fixture_id` is available yet, continue the
   waypoint sweep rather than inventing fixture ids.
   The server rejects skipped semantic phases: if you call `pick` before
   `navigate_to_object`, or `place` before `navigate_to_receptacle`, recover by
   calling the `required_tool` named in the error response.
4. Use the receptacle type to choose the placement tool:
   - For a fridge or refrigerator, call
     `roboclaws__open_receptacle(fixture_id)` before
     `roboclaws__place_inside(fixture_id)`, then
     `roboclaws__close_receptacle(fixture_id)`.
   - For a shelf, bookshelf, bookcase, or shelving unit, call
     `roboclaws__place_inside(fixture_id)` without open/close.
   - For table, sofa, bed, desk, sink, counter, or stand surfaces, call
     `roboclaws__place(fixture_id)`.
5. After any successful place/place_inside and required close, call
   `roboclaws__observe()` once in the current room/fixture area before choosing
   the next object or waypoint.
6. Call `roboclaws__done(reason)` only after every
   `metric_map.inspection_waypoints` waypoint id has an `observe` response and
   you have cleaned every public recommended candidate. If `done` returns
   `pending_cleanup_candidates`, clean those listed observed handles with their
   `candidate_fixture_id`, then call `done` again. If all waypoints are
   observed and you are not holding an object, call `done` as the authoritative
   closeout probe before starting another optional cleanup chain; when `done`
   returns pending candidates, clean exactly those listed handles using their
   `candidate_fixture_id` or `destination_options`, then call `done` again. If
   a tool returns top-level `required_tool` or
   `completion.blockers[*].required_tool`, call that public tool next for the
   same object or fixture before choosing new optional work. Re-observed
   visible objects can be stale evidence after a
   successful placement; do not retry handles that tool recovery marks
   `already_handled`, and do not switch to another handle from the same stale
   area just because it appeared in the same observation. Do not stop because
   you guess the hidden target count.

## Boundaries

Do not call `scene_objects`, read private manifests, inspect scoring code,
replay deterministic baselines, or bypass MCP with scripts. The Scorer may show
Private Evaluation after the run, but that information is not agent input.

Metric maps are shaped like a real-robot map bundle. In simulator rehearsals,
waypoint navigation is checked against a static Nav2-shaped costmap and labelled
`sim_costmap_planner`, while manipulation remains semantic unless explicitly
planner-backed in the report. Chase or third-person views may appear in the
report as `report_only_simulation_view`; they are not policy inputs.

## Trace-Preserving Skill Routine

For each observed cleanup handle, run this fixed public tool chain:

```text
navigate_to_object(object_id)
pick(object_id)
navigate_to_receptacle(candidate_fixture_id)
open_receptacle(candidate_fixture_id)      # only for fridge/refrigerator targets
place_inside(candidate_fixture_id)         # for fridge/refrigerator/shelf targets
close_receptacle(candidate_fixture_id)     # only after opening fridge-like targets
place(candidate_fixture_id)                # for normal surfaces instead of place_inside
observe()
```

Choose `place_inside` when the observation or fixture hints recommend it, or
when the target fixture affordances/category indicate fridge, refrigerator,
shelf, bookcase, or shelving. Choose `place` for table, sofa, bed, desk, sink,
counter, stand, hamper, and other surface-like fixtures. If any tool returns
`error_reason: semantic_order`, call its `required_tool` with the same public
object or fixture id, then retry the failed step once. If the retry still fails,
continue the waypoint sweep and leave the blocker visible in the trace rather
than inventing hidden destinations.

The reference routine lives at
`skills/molmo-realworld-cleanup/scripts/trace_preserving_cleanup.py`. Treat it
as executable documentation for the public call order and recovery shape. It
delegates to the repo canonical routine engine and is not permission to bypass
MCP or read private backend state.

## Target Query Recovery

Use `resolve_target_query` for map-build target search, cleanup destination
discovery, and custom/open-ended household goals. The tool and helper script
read only public Runtime Metric Map target candidates:

```text
resolve_target_query(query="sink_01", operation="destination")
```

The helper script for offline artifact review is
`skills/molmo-realworld-cleanup/scripts/target_query_recovery.py`. It is useful
for inspecting a saved `runtime_metric_map.json`; it is not permission to read
private manifests or simulator inventory. A stale id such as `sink_01` must
recover to a public anchor or waypoint when one exists. If it does not, report
the returned `public_search_budget` and continue public inspection while budget
remains.

## Skill Scratchpad

Use `skills/molmo-realworld-cleanup/scripts/scratchpad.py` when you need a
local memory file for strategy, retries, or current intent. The scratchpad is
only an agent aid; do not use it as scorer, checker, report, or `done` input.
When scratchpad notes disagree with `cleanup_worklist`, trust
`cleanup_worklist`.
