# 0096. Record Candidate Removal Effectiveness

Date: 2026-05-10

## Status

Accepted

## Context

Phase 102 and Phase 104 made the shared seed 10 blocker explicit:
`17 grasp failures; 15 candidate-removal calls`. That still left an important
debugging gap. The report showed many removal calls but did not explain whether
those calls actually removed the requested object from the upstream sampler's
candidate pool.

The upstream `PickTaskSampler.report_grasp_failure()` removes a candidate only
after the grasp-failure count exceeds `max_failures`, and
`_remove_candidate_object()` filters `candidate_objects` by exact object name.
The current evidence can therefore conflate:

- a grasp threshold being exceeded;
- `_remove_candidate_object()` being called;
- the named object actually being present in `candidate_objects`;
- the candidate list shrinking.

Without separating those, repeated grasp-feasibility signatures look like a
single opaque upstream failure instead of an actionable candidate-identity or
grasp-cache blocker.

## Decision

Extend the shared task-sampler failure diagnostics and shared report renderer
with **Candidate Removal Effectiveness** evidence.

New probe diagnostics record:

- grasp failure threshold state (`threshold_exceeded`, `threshold_crossed`);
- candidate-removal call deltas per grasp failure row;
- candidate counts before/after each removal call;
- whether the requested candidate name was present before/after removal;
- whether a removal call effectively shrank the candidate pool.

The shared report renderer surfaces this in standalone planner reports,
proof-bundle result cards, and the grouped grasp-feasibility signature matrix.
The task-feasibility summary may now include effective-removal and
candidate-name-miss counts when those fields are present. Older artifacts remain
renderable with the prior summary shape.

## Consequences

- Future exact-scene proof runs can show whether the shared RBY1M blocker is a
  real grasp candidate exhaustion path or an ineffective candidate-removal path.
- The Phase 105 bread-to-refrigerator rerun showed 17 grasp failures, 15
  candidate-removal calls, 0 effective removals, and 15 candidate-name misses.
- The report still uses the existing Cleanup Artifact Report / proof-bundle
  underlay; this is not a second renderer.
- Existing Phase 102 and Phase 104 artifacts keep their previous fields until
  regenerated or rerun.
- This does not make any cleanup primitive planner-backed and does not reduce
  the blocker by itself. It makes the next runtime intervention measurable.
