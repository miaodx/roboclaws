# 0013. Add Raw FPV Observation Mode For ADR-0003 Cleanup

Date: 2026-05-09

## Status

Accepted

## Context

ADR-0003 intentionally separated the Cleanup Agent's public view from private
scoring truth. The first implemented contract exposes robot-local visible object
detections: stable observed handles, categories, display names, image boxes, and
support estimates from the current inspection waypoint.

That is a useful v1 contract, but the broader context explicitly keeps raw
camera-only perception as a harder follow-up. In raw FPV mode, a model should
infer candidate objects from pixels rather than receiving structured movable
object detections. The project also needs this mode to reuse the shared cleanup
report underlay and the existing RBY1M visual artifact path, not create another
parallel report implementation.

## Decision

Add an explicit ADR-0003 perception mode:

- `visible_object_detections` remains the default and preserves existing clean
  cleanup behavior.
- `raw_fpv_only` is an evidence-mode public observation contract. `observe`
  returns no structured movable-object detections, no categories, no support
  estimates, and no target-ish metadata.
- Raw FPV observations are recorded in `agent_view.raw_fpv_observations` with
  waypoint, room, observation id, and artifact metadata.
- When robot views are recorded, the MCP/demo wrapper attaches the FPV image
  from the same `record_robot_view_step` underlay already used by Robot View
  Timeline reports.
- Reports render a dedicated `Raw FPV Observations` panel while retaining the
  shared Agent View, Robot View Timeline, Score, Advisory Review, and Private
  Evaluation sections.
- Checker support is opt-in through a raw-FPV requirement flag. Raw FPV evidence
  is allowed to be non-clean because this phase proves the perception boundary
  and artifacts, not camera-only object selection or planner-backed
  manipulation.

## Consequences

- The default ADR-0003 cleanup gates are unchanged.
- Raw FPV artifacts make the next model-policy step measurable without leaking
  structured detections into the agent view.
- A future phase still needs an object-selection/registration mechanism before a
  Cleanup Agent can manipulate objects from raw pixels alone.
- Planner-backed robot manipulation remains out of scope and continues to use
  existing provenance labels until separately proven.
