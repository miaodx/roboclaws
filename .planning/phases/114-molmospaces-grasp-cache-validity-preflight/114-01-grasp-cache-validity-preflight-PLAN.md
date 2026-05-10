# Phase 114-01: Grasp Cache Validity Preflight

## Goal

Prevent proof-bundle reports from treating an existing but empty rigid grasp
cache file as a ready `Bread_1` mitigation.

## Tasks

- Validate rigid loader files by parsing `.npz`/`.json` transform counts.
- Mark assets ready only when at least one rigid loader file contains transforms.
- Report `present_but_invalid` when a candidate file exists but has no valid
  transforms.
- Render `Valid`, `Transforms`, and `Validation` columns in the shared
  proof-bundle report.
- Checker-gate validation fields when present.
- Regenerate a report after the upstream droid Bread package install.

## Acceptance

- The Phase 114 artifact reports `Bread_1` as `missing_cache`.
- The droid candidate file reports `exists=True`, `valid=False`,
  `validation_status=empty`, and `transform_count=0`.
- Focused ruff, pytest, checker, and artifact-derived report checks pass.

## Result

Completed on 2026-05-10. The Phase 114 dry-run report renders the installed
droid `Bread_1` loader file as `present_but_invalid`: the file exists at the
runtime loader path, but contains zero transforms, so exact proof retry remains
blocked until a non-empty rigid grasp cache is generated or restored.

Artifact:
`output/debug-phase114-grasp-cache-validity-preflight/report.html`.
