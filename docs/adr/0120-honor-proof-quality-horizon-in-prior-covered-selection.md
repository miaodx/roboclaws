# 0120. Honor Proof Quality Horizon In Prior Covered Selection

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0083 let the proof-bundle runner skip proof requests that were already
covered by a prior planner-backed proof with promoted cleanup binding. ADR-0118
and ADR-0119 then introduced **Planner Proof Quality Evidence**, making proof
strength explicit across cleanup, standalone probe, and proof-bundle reports.

That created a stale-memory gap: a one-step planner-backed proof could still
mark a request as covered even when the next runner invocation wanted a stricter
multi-step proof horizon.

## Decision

Prior-covered proof selection now has an explicit proof-quality horizon:
`prior_covered_min_proof_steps`.

When `--exclude-prior-covered` is enabled, a prior result only counts as covered
when it is planner-backed, promoted to cleanup binding, and its shared proof
quality has nonzero motion with at least the requested executed-step count.

Legacy prior summaries without proof-quality fields keep the previous behavior
for the default one-step horizon, but they do not satisfy stricter horizons.
Runner manifests and reports render the configured coverage minimum plus prior
quality/step evidence for both selected and excluded rows.

## Consequences

- A future stricter proof run can reselect one-step prior proofs instead of
  being suppressed by stale coverage memory.
- The proof-bundle runner now uses the same proof-strength vocabulary as the
  standalone and cleanup report surfaces.
- Existing one-step coverage workflows remain compatible by default.
- This does not generate a stricter proof by itself; it makes the selection
  layer ready for one.

## Evidence

Implemented in Phase 129 on 2026-05-10.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py::test_proof_request_selection_reselects_prior_covered_below_quality_horizon tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_excludes_prior_covered_requests`
