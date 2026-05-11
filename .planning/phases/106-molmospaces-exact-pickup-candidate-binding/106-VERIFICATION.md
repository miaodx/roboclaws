# Phase 106 Verification: Phase 106-01: Exact Pickup Candidate Binding

Date: 2026-05-11
Source plan: `106-01-exact-pickup-candidate-binding-PLAN.md`
Backfill status: reconstructed from existing phase evidence.

## Verification Scope

This verification artifact repairs the missing GSD closeout file for Phase
106. It is based on the source plan's embedded status, tasks, acceptance
criteria, and recorded verification evidence. No fresh phase execution was run
as part of this backfill.

## Acceptance Evidence From Plan

- Existing exact target adapter behavior remains intact.
- The live pickup candidate pool is filtered or injected before upstream
  selection.
- Reports show the exact pickup candidate action and before/after counts when
  binding evidence exists.
- Focused ruff, pytest, checker, and real local probe checks pass.

## Recorded Verification Evidence

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

## Artifact Integrity Checks

- Source plan exists: `106-01-exact-pickup-candidate-binding-PLAN.md`.
- Source plan contains a completion date or result marker: `2026-05-10`.
- Backfilled summary exists: `106-01-exact-pickup-candidate-binding-SUMMARY.md`.
- Backfilled verification exists: `106-VERIFICATION.md`.

## Verdict

GSD artifact closure is repaired for Phase 106 based on the existing
committed phase evidence. Treat this as a documentation repair. If a future
claim depends on real MolmoSpaces, real RBY1M/CuRobo, real VLM, Docker, GPU,
or API-key behavior, rerun the recorded commands or a current equivalent before
using the phase as fresh runtime proof.
