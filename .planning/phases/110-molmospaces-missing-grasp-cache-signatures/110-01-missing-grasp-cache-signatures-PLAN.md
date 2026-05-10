# Phase 110-01: Missing Grasp Cache Signatures

## Goal

Make missing cached grasps a first-class grasp-feasibility subkind in proof
summaries and shared runner reports.

## Tasks

- Extend grasp-feasibility summaries with grasp-load failure detail.
- Add `grasp_cache_missing` signature subkind and failed asset UID fields.
- Render subkind, grasp-load failures, collision checks, zero non-colliding
  checks, and missing assets in the proof-bundle signature matrix.
- Update focused tests and checker coverage.
- Regenerate a runner report from the Phase 109 standalone artifact.

## Acceptance

- Phase 109 evidence summarizes as `grasp_cache_missing` while preserving
  `task_feasibility_blocker_kind=grasp_feasibility`.
- Shared runner reports show the subkind and `Bread_1` missing-grasp asset.
- Focused ruff, pytest, checker, and artifact-derived report checks pass.

## Result

Completed on 2026-05-10. The Phase 109 standalone evidence now rolls into a
Phase 110 runner dry-run with one grouped `grasp_cache_missing` signature:
`Bread_1` is the missing grasp asset, `ValueError` is the grasp-load exception
type, and the shared report renders those fields in both the prior-proof
signature matrix and the proof-result card.

Artifact: `output/debug-phase110-missing-grasp-cache-signatures/report.html`.
