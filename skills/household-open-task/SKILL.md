---
name: household-open-task
description: Complete open-ended household robot goals through public household MCP tools.
metadata:
  openclaw:
    emoji: H
---

# Household Open Task

Use the public household MCP tools as a bounded robot capability surface. The
operator goal is authoritative. Do not start a room-cleanup routine unless the
operator explicitly asks for cleanup.

## Loop

1. Call `roboclaws__metric_map()` when map context is needed. Use Base
   Navigation Map waypoints, public room labels, Runtime Metric Map evidence,
   and `roboclaws__resolve_target_query()` for named places, stale labels, or
   search terms. Do not read private manifests, scene inventory, generated mess
   truth, or scoring artifacts.
2. Inspect only as much as the goal needs. Navigate to public waypoints or
   target candidates with `roboclaws__navigate_to_waypoint()`, then call
   `roboclaws__observe()`. Use `roboclaws__adjust_camera()` only for bounded
   public recovery when a target or observation is incomplete.
3. For information, search, or inspection goals, tie the final answer to public
   observations, target candidates, and the inspected search budget. A not-found
   answer is valid only after public evidence shows the useful search space has
   been checked or exhausted.
4. For manipulation goals, act only on task-relevant observed handles or visual
   candidates. Follow public tool recovery responses such as `required_tool`,
   `required_next_tool`, `blocked_capability`, and actionability status. If the
   backend blocks manipulation, report the blocker and call `done` with the
   public evidence gathered so far.
5. Call `roboclaws__done(reason)` when the operator goal is satisfied, blocked
   by a public capability response, or exhausted by the public search budget.
   The reason must summarize the public evidence used and any remaining risk.

## Boundaries

- Do not call `scene_objects`, inspect private evaluator files, infer hidden
  mess targets, or treat cleanup candidates as part of the goal unless the
  operator asked for cleanup.
- Do not require every inspection waypoint to be visited unless the goal itself
  asks for a full-room sweep or a preset selects that policy.
- Do not promote this into one opaque MCP task tool. Keep search, navigation,
  observation, manipulation, and done visible in the trace.
