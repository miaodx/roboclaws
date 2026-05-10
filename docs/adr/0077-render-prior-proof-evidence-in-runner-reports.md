# 0077. Render Prior Proof Evidence in Runner Reports

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0076 lets the proof-bundle runner ingest standalone planner-probe
`run_result.json` artifacts and normalize them into prior proof result
summaries before request selection.

That solved selection memory, but it left a reviewability gap: the runner report
showed that a request was excluded by prior evidence, yet the normalized prior
probe itself was still only available through scattered report paths and
selection-table fields. For local-dev proof work, the reviewer needs one runner
report that shows the selected requests, excluded blockers, prior diagnostic
summary, and any prior planner-view images.

## Decision

Proof-bundle runner manifests will carry `prior_proof_result_summary` when prior
proof evidence is supplied. The runner `report.html` will render that summary as
a first-class **Prior Proof Evidence** section before new proof commands and new
proof results.

The section reuses the proof result card renderer, so prior evidence shows the
same status, blocker detail, worker-stage, stdout/stderr, proof report, sampler
diagnostics, and planner-view image rows as current proof results.

## Consequences

- Standalone probes and prior proof-bundle manifests remain private runner
  evidence, but they are visible in the report that used them for selection.
- Selection rows no longer have to be the only review surface for prior blocker
  evidence.
- If a prior proof result includes planner-view image artifacts, the runner
  report renders those images in the Prior Proof Evidence section.
- This does not claim new feasibility or planner-backed cleanup readiness; it
  only makes consumed prior evidence visually reviewable.

## Evidence

Phase 86 validates prior proof evidence reporting with focused tests for:

- carrying `prior_proof_result_summary` into proof-bundle runner manifests;
- rendering the `Prior Proof Evidence` section in runner reports;
- rendering prior proof report/run-result paths and prior planner-view image
  paths when present;
- checker coverage that validates prior proof evidence appears in `report.html`.

Verification on 2026-05-10:

- `uv run ruff check roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py::test_planner_proof_bundle_runner_report_renders_commands tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_ingests_standalone_prior_probe_run_result_by_cleanup_pair tests/test_check_molmo_planner_proof_bundle_runner_result.py::test_checker_accepts_partial_selection_with_exhausted_fallbacks`
- Manual dry-run at
  `output/debug-phase86-prior-proof-evidence-visual-report-dry-run/` passed the
  runner checker and rendered `Prior Proof Evidence`.
