# Phase 126 Summary: MolmoSpaces Phase 125 Bound Proof Cleanup Rerun

Completed: 2026-05-10
Backfilled: 2026-05-11
Source plan: `126-01-phase125-bound-proof-cleanup-rerun-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Consume the Phase 125 planner-backed exact proof in the ADR-0003 cleanup
primitive path and verify the final cleanup artifact remains globally honest.

## Completed Tasks

- The source plan records completion in its Status/Result section.

## Recorded Status

Complete on 2026-05-10.

The Phase 126 cleanup rerun consumed
`output/debug-phase125-curobo-pregrasp-exception-context/run_result.json`.
The final artifact lives at
`output/debug-phase126-phase125-bound-proof-cleanup-rerun/`.

The rerun completed with `cleanup_status=success`, 10 generated mess objects,
44 robot timeline steps, and attached planner proof views. `observed_001` to
`refrigerator_5e0d26d670a75ae0a52f2ceb08914b0e_1_0_2` is strict
planner-backed for `nav`, `pick`, `nav`, `open`, and `place_inside`.

The rest of the run remains honest: primitive summary is `planner_backed=5` and
`api_semantic=37`, so the global cleanup primitive gate and planner cleanup
bridge both remain `blocked_capability`.

Verification:

- `.venv/bin/python examples/molmospaces_realworld_cleanup.py --output-dir output/debug-phase126-phase125-bound-proof-cleanup-rerun --seed 7 --backend molmospaces_subprocess --fixture-hint-mode room_only --perception-mode visible_object_detections --include-robot --robot-name rby1m --record-robot-views --generated-mess-count 10 --planner-proof-run-result output/debug-phase125-curobo-pregrasp-exception-context/run_result.json --use-planner-proof-for-cleanup-primitives`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json --expect-backend molmospaces_subprocess --min-generated-mess-count 10 --require-robot-views --require-planner-proof-attachment --accept-blocked-planner-cleanup-primitives --require-bound-planner-cleanup-object observed_001:refrigerator_5e0d26d670a75ae0a52f2ceb08914b0e_1_0_2 --require-mixed-planner-cleanup-primitives --accept-blocked-planner-cleanup-bridge`

[Backfill note: source section truncated; see the phase PLAN for full embedded evidence.]

## Evidence

- `.venv/bin/python examples/molmospaces_realworld_cleanup.py --output-dir output/debug-phase126-phase125-bound-proof-cleanup-rerun --seed 7 --backend molmospaces_subprocess --fixture-hint-mode room_only --perception-mode visible_object_detections --include-robot --robot-name rby1m --record-robot-views --generated-mess-count 10 --planner-proof-run-result output/debug-phase125-curobo-pregrasp-exception-context/run_result.json --use-planner-proof-for-cleanup-primitives`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json --expect-backend molmospaces_subprocess --min-generated-mess-count 10 --require-robot-views --require-planner-proof-attachment --accept-blocked-planner-cleanup-primitives --require-bound-planner-cleanup-object observed_001:refrigerator_5e0d26d670a75ae0a52f2ceb08914b0e_1_0_2 --require-mixed-planner-cleanup-primitives --accept-blocked-planner-cleanup-bridge`
- `.venv/bin/ruff check scripts/check_molmo_realworld_cleanup_result.py tests/test_check_molmo_realworld_cleanup_result.py`
- `.venv/bin/ruff format --check scripts/check_molmo_realworld_cleanup_result.py tests/test_check_molmo_realworld_cleanup_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_realworld_cleanup_result.py::test_realworld_cleanup_can_use_proof_bundle_for_full_gate_readiness tests/test_check_molmo_realworld_cleanup_result.py::test_realworld_cleanup_can_use_matching_probe_backed_executor`

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.
