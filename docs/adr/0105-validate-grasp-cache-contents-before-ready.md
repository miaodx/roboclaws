# 0105. Validate Grasp Cache Contents Before Ready

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0104 bound grasp-cache preflight to the runtime assets root and exposed the
resolved cache target paths. Installing the upstream droid Bread package then
created:

`grasps/droid/Bread_1/Bread_1_grasps_filtered.npz`

However, upstream `has_valid_grasp_file("Bread_1")` remains false and
`load_grasps_for_object("Bread_1")` still raises. Inspecting the NPZ shows a
`transforms` array with zero rows.

Therefore, file existence is not a safe readiness signal.

## Decision

Treat rigid grasp-cache readiness as content validity, not path existence.

The preflight now parses rigid loader candidates:

- `.npz`: count the `transforms` array;
- `.json`: count the `transforms` list;
- valid only when `transform_count > 0`;
- `present_but_invalid` when a candidate exists but none are valid;
- `missing` when no rigid loader candidate exists.

Reports render `Valid`, `Transforms`, and `Validation` columns for loader file
probes. The checker validates those fields when present.

## Consequences

- Empty or placeholder grasp-cache files cannot satisfy cache mitigation.
- The installed droid Bread archive is visible but correctly remains blocked.
- The next mitigation slice should generate or restore a non-empty rigid
  `Bread_1` grasp cache, then rerun the exact proof.

## Evidence

Implemented in Phase 114 on 2026-05-10.

Artifact:

- `output/debug-phase114-grasp-cache-validity-preflight/proof_bundle_run_manifest.json`
- `output/debug-phase114-grasp-cache-validity-preflight/report.html`

Key result:

- `loader_file_status=present_but_invalid`
- `validation_status=empty`
- `transform_count=0`
- `valid=false`
