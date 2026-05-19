# Phase 106-01: Exact Pickup Candidate Binding

## Goal

Bind exact-scene planner probes to the requested pickup object before upstream
pickup selection, so candidate diagnostics reflect the requested cleanup
primitive instead of unrelated sampler candidates.

## Tasks

- Move pickup candidate binding from reset-time into the exact sampler adapter's
  `_select_pickup_object()` hook.
- Record exact pickup binding action, before/after candidate counts, candidate
  names, and requested-name presence.
- Render exact pickup binding in standalone planner reports and proof-bundle
  result cards using the shared report underlay.
- Update checker gates and focused tests.
- Rerun the real local RBY1M proof probe and record the outcome in ADR,
  CONTEXT, the source plan, and GSD state.

## Acceptance

- Existing exact target adapter behavior remains intact.
- The live pickup candidate pool is filtered or injected before upstream
  selection.
- Reports show the exact pickup candidate action and before/after counts when
  binding evidence exists.
- Focused ruff, pytest, checker, and real local probe checks pass.

## Result

Complete on 2026-05-10.

Code changes:

- `scripts/run_molmo_planner_manipulation_probe.py`
- `roboclaws/molmo_cleanup/report.py`
- planner probe and proof-bundle checker updates
- focused test coverage

Verification:

- `.venv/bin/ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked output/debug-phase106-exact-pickup-candidate-binding-fixed/run_result.json`

Runtime evidence:

- `output/debug-phase106-exact-pickup-candidate-binding-fixed/run_result.json`
- `output/debug-phase106-exact-pickup-candidate-binding-fixed/report.html`

Observed runtime result:

- status: `blocked_capability`
- exact pickup action: `injected_requested_candidate_name`
- candidate count before: 4
- candidate count after: 1
- requested present before: false
- requested present after: true
- grasp failures: 0
- candidate-removal calls: 0
- remaining blocker: direct `KeyError` invalid planner object name for the
  requested bread alias
