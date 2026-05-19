# Phase 92-01: Prior Covered Proof Selection Memory

## Goal

Exclude already-covered planner proof requests from broader proof-bundle
selection so local proof execution expands coverage instead of retrying the
one passing `proof_008` object.

## Tasks

- Add a runner option to exclude prior results with both `planner_backed` and
  cleanup binding promotion.
- Render covered exclusions in the existing proof-bundle runner report.
- Add checker gates for prior covered exclusions and selected-count bounds.
- Add focused tests for runner selection and checker validation.
- Produce a dry-run artifact against the current broader source and Phase90
  prior bundle.

## Acceptance

- `prior_planner_proof_covered` appears in the runner manifest/report for
  `proof_008`.
- The dry-run selects zero commands from the current broader source.
- The runner report still renders consumed prior proof evidence and planner
  views.
- Lint, format, focused pytest, and runner checker gates pass.

## Result

Complete on 2026-05-10.

Artifact:
`output/debug-phase92-covered-proof-memory-dry-run/proof_bundle_run_manifest.json`

Key evidence:

- `proof_request_count=10`
- `selected_count=0`
- `excluded_count=10`
- `covered_request_count=1`
- `grasp_feasibility_blocker_count=9`
- `fallback_generation.status=exhausted`

Verification:

- preflight dependency install passed;
- AI2-THOR import passed;
- focused ruff check passed;
- focused ruff format check passed;
- focused pytest passed;
- runner checker passed with `--max-selected-requests 0` and
  `--require-prior-covered-exclusion`.
