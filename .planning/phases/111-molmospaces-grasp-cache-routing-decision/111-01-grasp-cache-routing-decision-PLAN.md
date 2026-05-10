# Phase 111-01: Grasp Cache Routing Decision

## Goal

Make the source-rotation versus missing-grasp-cache choice explicit in
proof-bundle manifests and reports before another runtime attempt.

## Tasks

- Add a manifest-level grasp-feasibility mitigation decision.
- Route `grasp_cache_missing` evidence to `grasp_cache_mitigation`.
- Keep source-rotation availability visible as a separate decision field.
- Render a visual decision panel in the shared runner report.
- Checker-gate the panel when the decision is present.
- Regenerate a runner report from Phase 109 missing-cache evidence.

## Acceptance

- The Phase 111 artifact reports `primary_route=grasp_cache_mitigation`.
- The report shows `Bread_1`, `ValueError`, and
  `available_for_unproven_requests`.
- Focused ruff, pytest, checker, and artifact-derived report checks pass.

## Result

Completed on 2026-05-10. The Phase 111 dry-run report renders a
`Grasp Feasibility Mitigation Decision` panel. It routes the known `Bread_1`
missing-cache blocker to `grasp_cache_mitigation` before retry while preserving
source rotation as available only for separate unproven requests.

Artifact: `output/debug-phase111-grasp-cache-routing-decision/report.html`.
