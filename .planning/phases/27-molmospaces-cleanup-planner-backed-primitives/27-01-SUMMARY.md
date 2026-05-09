# Phase 27-01 Summary: Cleanup Primitive Gate

Completed: 2026-05-09

## What Changed

- Added `cleanup_primitive_evidence` for object-level cleanup subphases:
  `nav/object`, `pick/object`, `nav/target`, optional `open/target`, and
  `place/surface` or `place/inside`.
- Rendered the new evidence in the shared Cleanup Artifact Report as
  `Cleanup Primitive Gate`.
- Added checker modes for explicit blocked-capability acceptance and strict
  future planner-backed cleanup primitive proof.
- Preserved the ADR-0017 attached planner proof as separate evidence; it does
  not relabel cleanup-loop moves as planner-backed.

## Evidence

- Local artifact:
  `output/molmo-realworld-cleanup-primitive-gate/report.html`
- Run result:
  `output/molmo-realworld-cleanup-primitive-gate/run_result.json`
- Current gate state:
  `status=blocked_capability`, `primitive_provenance=blocked_capability`,
  `object_count=2`, `subphase_count=8`.
- Strict planner-backed cleanup primitive mode rejects the same artifact because
  cleanup subphases are still `api_semantic`.

## Follow-Ups

- Replace `api_semantic` cleanup-loop subphases with real planner-backed
  cleanup primitives.
- Resolve the RBY1M/CuRobo planner runtime path before claiming planner-backed
  cleanup execution on RBY1M.
- Keep camera-only model-policy cleanup as a separate phase from primitive
  proof.
