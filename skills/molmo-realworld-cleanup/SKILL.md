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

1. Call `roboclaws__metric_map()` and `roboclaws__fixture_hints()` first.
2. Treat `inspection_waypoints` as static map/fixture coverage candidates, not
   mess hints. Build an exact checklist from
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
   In `camera-raw` runs, `observe()` returns raw FPV image evidence instead of
   structured labels. Inspect the image, then call
   `roboclaws__navigate_to_visual_candidate(source_observation_id, category,
   target_fixture_id, evidence_note, image_region, ...)` only when you intend to
   act on a visual candidate. Do not pre-register raw-FPV candidates with
   `roboclaws__declare_visual_candidates`; that producer-registration path is
   for `camera-labels`. Prefer broad cleanup categories when uncertain (`food`,
   `dish`, `book`, `linen`, `toy`, `electronics`, `pillow`) instead of
   over-specific guesses that are likely to miss the public grounding resolver.
   Use an `image_region` schema the tool accepts, such as
   `{"type":"bbox","value":[x,y,width,height]}` or
   `{"type":"verbal_region","value":"front of desk"}`; do not send a bare
   `{x,y,width,height}` object.
   Omit `source_fixture_id` when you are not confident which public fixture the
   image object is resting on. When `navigate_to_visual_candidate` resolves, use
   its returned `candidate_fixture_id` and `recommended_tool` for placement if
   present.
   Maintain a count of successful grounded cleanup actions. In `camera-raw`
   acceptance runs, do not call `done` before at least seven grounded visual
   candidates have been successfully cleaned. If grounding stays unresolved and
   the success count is still below seven, continue sweeping or reobserve from
   another public waypoint; retry at most once with a broader category or clearer
   verbal region before moving on.
   After a successful pick/place for an observed handle, do not act on that same
   handle again. If a later raw-FPV declaration resolves to an already-handled
   object, continue the waypoint sweep and observe for other objects instead of
   navigating to that handle again.
   If raw-FPV visual grounding is unresolved, continue the waypoint sweep; do
   not call `done` as a system-assessment shortcut while map waypoints remain
   unvisited.
   In `camera-labels` runs, use
   `roboclaws__declare_visual_candidates()` to register producer-labelled
   candidates before cleanup selection.
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
   `candidate_fixture_id`, then call `done` again. Do not stop because you
   guess the hidden target count.

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

## Skill Scratchpad

Use `skills/molmo-realworld-cleanup/scripts/scratchpad.py` when you need a
local memory file for strategy, retries, or current intent. The scratchpad is
only an agent aid; do not use it as scorer, checker, report, or `done` input.
When scratchpad notes disagree with `cleanup_worklist`, trust
`cleanup_worklist`.
