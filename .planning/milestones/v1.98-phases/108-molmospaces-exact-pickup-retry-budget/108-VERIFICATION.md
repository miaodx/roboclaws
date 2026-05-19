# Phase 108 Verification: Phase 108-01: Exact Pickup Retry Budget

Date: 2026-05-11
Source plan: `108-01-exact-pickup-retry-budget-PLAN.md`
Backfill status: reconstructed from existing phase evidence.

## Verification Scope

This verification artifact repairs the missing GSD closeout file for Phase
108. It is based on the source plan's embedded status, tasks, acceptance
criteria, and recorded verification evidence. No fresh phase execution was run
as part of this backfill.

## Acceptance Evidence From Plan

- Exact pickup binding keeps only the requested planner object.
- The candidate pool length allows upstream's default `max_failures=2` path to
  cross on the third failed grasp.
- Reports show the exact pickup retry budget.
- Focused ruff, pytest, checker, and real local proof checks pass.

## Recorded Verification Evidence

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

## Artifact Integrity Checks

- Source plan exists: `108-01-exact-pickup-retry-budget-PLAN.md`.
- Source plan contains a completion date or result marker: `2026-05-10`.
- Backfilled summary exists: `108-01-exact-pickup-retry-budget-SUMMARY.md`.
- Backfilled verification exists: `108-VERIFICATION.md`.

## Verdict

GSD artifact closure is repaired for Phase 108 based on the existing
committed phase evidence. Treat this as a documentation repair. If a future
claim depends on real MolmoSpaces, real RBY1M/CuRobo, real VLM, Docker, GPU,
or API-key behavior, rerun the recorded commands or a current equivalent before
using the phase as fresh runtime proof.
