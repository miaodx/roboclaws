# Phase 106 Summary: Phase 106-01: Exact Pickup Candidate Binding

Completed: 2026-05-10
Backfilled: 2026-05-11
Source plan: `106-01-exact-pickup-candidate-binding-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Bind exact-scene planner probes to the requested pickup object before upstream
pickup selection, so candidate diagnostics reflect the requested cleanup
primitive instead of unrelated sampler candidates.

## Completed Tasks

- The source plan records completion in its Status/Result section.

## Recorded Status

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

[Backfill note: source section truncated; see the phase PLAN for full embedded evidence.]

## Evidence

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

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.
