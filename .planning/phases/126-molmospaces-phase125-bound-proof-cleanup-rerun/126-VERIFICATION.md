# Phase 126 Verification: MolmoSpaces Phase 125 Bound Proof Cleanup Rerun

Date: 2026-05-11
Source plan: `126-01-phase125-bound-proof-cleanup-rerun-PLAN.md`
Backfill status: reconstructed from existing phase evidence.

## Verification Scope

This verification artifact repairs the missing GSD closeout file for Phase
126. It is based on the source plan's embedded status, tasks, acceptance
criteria, and recorded verification evidence. No fresh phase execution was run
as part of this backfill.

## Acceptance Evidence From Plan

- Focused checker tests pass.
- Cleanup rerun artifact exists under
  `output/debug-phase126-phase125-bound-proof-cleanup-rerun/`.
- `observed_001` to refrigerator is strict planner-backed for the inside
  cleanup sequence.
- At least one unmatched cleanup object remains `api_semantic`, leaving the
  global cleanup primitive gate and bridge blocked.
- The cleanup report renders shared visual core, robot views, planner proof
  views, Cleanup Primitive Gate, and Planner Cleanup Bridge.

## Recorded Verification Evidence

- `.venv/bin/python examples/molmospaces_realworld_cleanup.py --output-dir output/debug-phase126-phase125-bound-proof-cleanup-rerun --seed 7 --backend molmospaces_subprocess --fixture-hint-mode room_only --perception-mode visible_object_detections --include-robot --robot-name rby1m --record-robot-views --generated-mess-count 10 --planner-proof-run-result output/debug-phase125-curobo-pregrasp-exception-context/run_result.json --use-planner-proof-for-cleanup-primitives`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json --expect-backend molmospaces_subprocess --min-generated-mess-count 10 --require-robot-views --require-planner-proof-attachment --accept-blocked-planner-cleanup-primitives --require-bound-planner-cleanup-object observed_001:refrigerator_5e0d26d670a75ae0a52f2ceb08914b0e_1_0_2 --require-mixed-planner-cleanup-primitives --accept-blocked-planner-cleanup-bridge`
- `.venv/bin/ruff check scripts/check_molmo_realworld_cleanup_result.py tests/test_check_molmo_realworld_cleanup_result.py`
- `.venv/bin/ruff format --check scripts/check_molmo_realworld_cleanup_result.py tests/test_check_molmo_realworld_cleanup_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_realworld_cleanup_result.py::test_realworld_cleanup_can_use_proof_bundle_for_full_gate_readiness tests/test_check_molmo_realworld_cleanup_result.py::test_realworld_cleanup_can_use_matching_probe_backed_executor`

## Artifact Integrity Checks

- Source plan exists: `126-01-phase125-bound-proof-cleanup-rerun-PLAN.md`.
- Source plan contains a completion date or result marker: `2026-05-10`.
- Backfilled summary exists: `126-01-phase125-bound-proof-cleanup-rerun-SUMMARY.md`.
- Backfilled verification exists: `126-VERIFICATION.md`.

## Verdict

GSD artifact closure is repaired for Phase 126 based on the existing
committed phase evidence. Treat this as a documentation repair. If a future
claim depends on real MolmoSpaces, real RBY1M/CuRobo, real VLM, Docker, GPU,
or API-key behavior, rerun the recorded commands or a current equivalent before
using the phase as fresh runtime proof.
