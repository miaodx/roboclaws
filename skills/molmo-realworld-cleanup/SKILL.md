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
2. Sweep public inspection waypoints. For each waypoint, call
   `roboclaws__navigate_to_waypoint(waypoint_id)`, then
   `roboclaws__observe()`. Build your own semantic map from returned
   `observed_*` object handles and support estimates.
3. Clean plausible misplaced objects. Use only observed object handles:
   `roboclaws__navigate_to_object(object_id)`, `roboclaws__pick(object_id)`,
   `roboclaws__navigate_to_receptacle(fixture_id)`, then place it.
   The server rejects skipped semantic phases: if you call `pick` before
   `navigate_to_object`, or `place` before `navigate_to_receptacle`, recover by
   calling the `required_tool` named in the error response.
4. If the fixture affordances/name indicate a fridge or refrigerator, call
   `roboclaws__open_receptacle(fixture_id)` before
   `roboclaws__place_inside(fixture_id)`. Otherwise call
   `roboclaws__place(fixture_id)`.
5. Call `roboclaws__done(reason)` only after you have swept the map and cleaned
   every plausible candidate you intend to handle. Do not stop because you
   guess the hidden target count.

## Boundaries

Do not call `scene_objects`, read private manifests, inspect scoring code,
replay deterministic baselines, or bypass MCP with scripts. The Scorer may show
Private Evaluation after the run, but that information is not agent input.
