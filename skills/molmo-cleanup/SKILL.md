---
name: molmo-cleanup
description: Drive the MolmoSpaces current cleanup contract through roboclaws MCP tools.
metadata:
  openclaw:
    emoji: M
---

# Molmo Cleanup

Use only the `roboclaws__*` MCP tools. This is the current-contract bridge:
`scene_objects` returns the global public object/receptacle list so you can prove
the tool loop. Do not claim ADR-0003 robot-local perception or planner-backed
manipulation.

## Loop

1. First call `roboclaws__observe()`.
2. Call `roboclaws__scene_objects()` and choose object/receptacle pairs yourself.
   Use only pickupable `objects[*].object_id` values with a non-empty
   `location_id`. Receptacles are targets only; never pass a receptacle id or
   simulator-style id like `Sofa|...` to `navigate_to_object`, `pick`, or
   `object_done`.
   When several receptacles have the same suitable category, choose the first
   matching receptacle in the `scene_objects().receptacles` order.
3. For each misplaced pickupable object: `roboclaws__navigate_to_object(object_id)`,
   `roboclaws__pick(object_id)`, `roboclaws__navigate_to_receptacle(receptacle_id)`,
   then place it and call `roboclaws__object_done(object_id, receptacle_id)`.
4. Use `roboclaws__place_inside(receptacle_id)` for fridge/refrigerator and
   shelf/bookshelf/bookcase/shelving-unit targets. Fridge-like targets must be
   opened first with `roboclaws__open_receptacle(receptacle_id)` and closed
   afterward with `roboclaws__close_receptacle(receptacle_id)`. For table, sofa,
   bed, desk, sink, counter, or stand surfaces use `roboclaws__place(receptacle_id)`.
5. Call `roboclaws__done(reason)` only after every intended object has an
   `object_done` readback. If a tool returns `stale_reference` or another error,
   re-read `scene_objects` and repair the current object before continuing.

## Boundaries

Do not read private manifests, replay `public_heuristic`, inspect scoring code,
or bypass MCP with scripts. Your job is to use the public tool results to choose
and execute a reasonable cleanup sequence. The final artifacts are
`trace.jsonl`, `run_result.json`, and `report.html` under the server output dir.
