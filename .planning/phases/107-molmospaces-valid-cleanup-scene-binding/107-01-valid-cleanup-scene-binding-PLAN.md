# Phase 107-01: Valid Cleanup Scene Binding

## Goal

Prevent stale cleanup scene paths from being accepted as exact-scene planner
proof evidence, then rerun the exact pickup binding probe against the canonical
cleanup scene.

## Tasks

- Render exact cleanup task config blocker codes in shared planner reports and
  proof-bundle result cards.
- Add `--require-cleanup-scene-bound` to the planner manipulation checker.
- Add focused checker/report tests.
- Rerun the seed-10 bread-to-refrigerator probe with the canonical scene XML.
- Record the decision and corrected runtime evidence in ADR, CONTEXT, the
  source plan, and GSD state.

## Acceptance

- Missing cleanup scene XML is visible in `report.html` when present.
- The stricter checker rejects stale-scene exact proof evidence.
- The valid-scene rerun passes the stricter checker.
- Focused ruff and pytest checks pass.

## Result

Complete on 2026-05-10.

Code changes:

- `scripts/check_molmo_planner_manipulation_probe.py`
- `scripts/check_molmo_planner_proof_bundle_runner_result.py`
- `roboclaws/molmo_cleanup/report.py`
- focused test coverage

Verification:

- `.venv/bin/ruff format --check scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff check scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked --require-cleanup-scene-bound output/debug-phase107-valid-cleanup-scene-pickup-binding/run_result.json`

Runtime evidence:

- `output/debug-phase107-valid-cleanup-scene-pickup-binding/run_result.json`
- `output/debug-phase107-valid-cleanup-scene-pickup-binding/report.html`

Observed runtime result:

- status: `blocked_capability`
- cleanup task config blockers: none
- exact pickup candidate action: `injected_requested_candidate_name`
- candidate count before: 17
- candidate count after: 1
- robot placement attempts: 1
- placement failures: 0
- grasp failures: 1
- candidate-removal calls: 0
