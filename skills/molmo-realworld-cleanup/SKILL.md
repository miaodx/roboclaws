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
   mess hints. For each useful waypoint or current-room area, call
   `roboclaws__navigate_to_waypoint(waypoint_id)`, then
   `roboclaws__observe()`. Build your own semantic map from returned
   `observed_*` object handles and support estimates.
   In `camera-raw` runs, `observe()` returns raw FPV image evidence instead of
   structured labels. Inspect the image, then call
   `roboclaws__navigate_to_visual_candidate(source_observation_id, category,
   target_fixture_id, evidence_note, image_region, ...)` only when you intend to
   act on a visual candidate. Prefer broad cleanup categories when uncertain
   (`food`, `dish`, `book`, `linen`, `toy`, `electronics`, `pillow`) instead of
   over-specific guesses that are likely to miss the public grounding resolver.
   In `camera-labels` runs, use
   `roboclaws__declare_visual_candidates()` to register producer-labelled
   candidates before cleanup selection.
3. Prefer a local cleanup loop after each useful observation instead of a full
   up-front survey. Clean plausible misplaced objects with only observed
   object handles:
   `roboclaws__navigate_to_object(object_id)`, `roboclaws__pick(object_id)`,
   `roboclaws__navigate_to_receptacle(fixture_id)`, then place it.
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
6. Call `roboclaws__done(reason)` only after you have swept the map and cleaned
   every public recommended candidate. If `done` returns
   `pending_cleanup_candidates`, clean those listed observed handles with their
   `candidate_fixture_id`, then call `done` again. Do not stop because you
   guess the hidden target count.

## Boundaries

Do not call `scene_objects`, read private manifests, inspect scoring code,
replay deterministic baselines, or bypass MCP with scripts. The Scorer may show
Private Evaluation after the run, but that information is not agent input.

Metric maps are shaped like a real-robot map bundle, but this phase still labels
semantic simulator navigation as `api_semantic`. Chase or third-person views may
appear in the report as `report_only_simulation_view`; they are not policy
inputs.
