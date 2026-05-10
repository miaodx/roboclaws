# Phase 112-01: Grasp Cache Availability Preflight

## Goal

Make the `Bread_1` missing-cache route actionable by recording the exact
MolmoSpaces rigid grasp-cache files the upstream loader will check.

## Tasks

- Add a manifest-level grasp-cache availability preflight.
- Probe the three rigid loader paths used by
  `molmo_spaces.utils.grasp_sample.load_grasps_for_object`.
- Keep the droid joint file visible as a folder-probe-only path.
- Distinguish present object assets from missing rigid grasp cache files.
- Render the preflight in the shared planner proof-bundle report.
- Checker-gate the preflight when present.
- Regenerate a runner report from Phase 109 missing-cache evidence.

## Acceptance

- The Phase 112 artifact reports `status=missing_cache` for `Bread_1`.
- The report shows the droid, droid-objaverse, and RUM rigid loader paths.
- The report shows local `Bread_1` object assets are present.
- Focused ruff, pytest, checker, and artifact-derived report checks pass.

## Result

Completed on 2026-05-10. The Phase 112 dry-run report renders
`Grasp Cache Availability Preflight`, showing that `Bread_1` object XML/OBJ
assets exist under `objects/thor/...`, while all rigid loader files are absent:

- `grasps/droid/Bread_1/Bread_1_grasps_filtered.npz`
- `grasps/droid_objaverse/Bread_1/Bread_1_grasps_filtered.npz`
- `grasps/rum/Bread_1/Bread_1_grasps_filtered.json`

Artifact:
`output/debug-phase112-grasp-cache-availability-preflight/report.html`.
