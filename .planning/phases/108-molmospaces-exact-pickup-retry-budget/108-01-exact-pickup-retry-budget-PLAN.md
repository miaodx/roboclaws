# Phase 108-01: Exact Pickup Retry Budget

## Goal

Preserve upstream grasp-failure retry semantics after exact pickup candidate
binding, without reintroducing unrelated candidate retries.

## Tasks

- Repeat the exact requested pickup candidate to a retry budget of 3 inside the
  exact sampler adapter.
- Record retry-budget evidence in the exact pickup binding payload.
- Render retry-budget evidence in shared planner reports and proof-bundle
  result cards.
- Update checker gates and focused tests.
- Rerun the valid-scene bread-to-refrigerator proof and record the outcome.

## Acceptance

- Exact pickup binding keeps only the requested planner object.
- The candidate pool length allows upstream's default `max_failures=2` path to
  cross on the third failed grasp.
- Reports show the exact pickup retry budget.
- Focused ruff, pytest, checker, and real local proof checks pass.

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
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked --require-cleanup-scene-bound output/debug-phase108-exact-pickup-retry-budget/run_result.json`

Runtime evidence:

- `output/debug-phase108-exact-pickup-retry-budget/run_result.json`
- `output/debug-phase108-exact-pickup-retry-budget/report.html`

Observed runtime result:

- status: `blocked_capability`
- retry budget: 3
- candidate count after exact binding: 3
- robot placement attempts: 3
- grasp failures: 3
- candidate-removal calls: 1
- effective removals: 1
- candidate-name misses: 0
