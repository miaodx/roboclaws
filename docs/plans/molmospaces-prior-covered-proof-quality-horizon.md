# MolmoSpaces Prior-Covered Proof Quality Horizon

**Status:** Completed under GSD Phase 129 on 2026-05-10
**Created:** 2026-05-10
**Source:** ADR-0118, ADR-0119, `CONTEXT.md`, `docs/plans/molmospaces-manipulation-spike.md`
**Workflow:** `hybrid-phase-pipeline`

## Problem

Proof quality is now shared across cleanup, standalone probe, and
proof-bundle runner reports, but prior-covered proof selection still treated
any planner-backed cleanup-bound prior result as covered.

That is fine for the default one-step proof horizon, but it blocks the next
architecture step: requesting multi-step or containment-strength proofs without
having stale one-step proof memory suppress the command.

## Decision

Add a proof-quality-aware coverage horizon to prior-covered selection.

The proof-bundle runner now accepts `--prior-covered-min-proof-steps`. The
selection module only excludes a prior planner-backed cleanup-bound proof when
its shared proof quality reaches that horizon. Selected rows keep prior quality
evidence so reports explain why a prior proof was reselected.

## Non-Goals

- Do not execute new local RBY1M/CuRobo proofs.
- Do not raise the global checker horizon above one-step motion yet.
- Do not change cleanup primitive provenance.
- Do not create a second report implementation.

## Acceptance Criteria

- Prior-covered selection excludes one-step prior proofs at the default horizon.
- The same prior proof is reselected when the requested coverage horizon is
  stricter than the prior proof's executed steps.
- Runner manifests and reports render the coverage minimum and prior quality
  evidence.
- Focused lint, format, and pytest gates pass.

## Result

Complete.

`proof_request_selection_from_summary()` now carries
`prior_covered_min_proof_steps`, the runner exposes it as
`--prior-covered-min-proof-steps`, and proof-request reports show the coverage
minimum plus prior proof quality/steps. Legacy prior summaries still count as
covered at the default one-step horizon, but stricter horizons require shared
quality evidence.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py::test_proof_request_selection_reselects_prior_covered_below_quality_horizon tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_excludes_prior_covered_requests`
