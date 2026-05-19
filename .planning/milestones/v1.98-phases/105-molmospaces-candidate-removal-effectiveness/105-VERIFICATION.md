# Phase 105 Verification: Phase 105-01: Candidate Removal Effectiveness

Date: 2026-05-11
Source plan: `105-01-candidate-removal-effectiveness-PLAN.md`
Backfill status: reconstructed from existing phase evidence.

## Verification Scope

This verification artifact repairs the missing GSD closeout file for Phase
105. It is based on the source plan's embedded status, tasks, acceptance
criteria, and recorded verification evidence. No fresh phase execution was run
as part of this backfill.

## Acceptance Evidence From Plan

- Existing grasp-feasibility artifacts remain renderable.
- New diagnostics can distinguish removal calls from effective removals.
- Reports show candidate-name misses and effective-removal counts when present.
- Focused ruff and pytest checks pass.

## Recorded Verification Evidence

- `.venv/bin/ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/planner_task_feasibility.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_planner_task_feasibility.py`
- `.venv/bin/ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/planner_task_feasibility.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_planner_task_feasibility.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_planner_task_feasibility.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`

Runtime evidence:

- `output/debug-phase105-grasp-removal-effectiveness-probe/run_result.json`
- `output/debug-phase105-grasp-removal-effectiveness-probe/report.html`

Observed runtime result:

- status: `blocked_capability`
- blocker: `HouseInvalidForTask`
- grasp failures: 17
- candidate-removal calls: 15
- effective removals: 0
- candidate-name misses: 15
- threshold-exceeded rows: 15
- threshold-crossed rows: 1
- robot-placement failures: 0

## Artifact Integrity Checks

- Source plan exists: `105-01-candidate-removal-effectiveness-PLAN.md`.
- Source plan contains a completion date or result marker: `2026-05-10`.
- Backfilled summary exists: `105-01-candidate-removal-effectiveness-SUMMARY.md`.
- Backfilled verification exists: `105-VERIFICATION.md`.

## Verdict

GSD artifact closure is repaired for Phase 105 based on the existing
committed phase evidence. Treat this as a documentation repair. If a future
claim depends on real MolmoSpaces, real RBY1M/CuRobo, real VLM, Docker, GPU,
or API-key behavior, rerun the recorded commands or a current equivalent before
using the phase as fresh runtime proof.
