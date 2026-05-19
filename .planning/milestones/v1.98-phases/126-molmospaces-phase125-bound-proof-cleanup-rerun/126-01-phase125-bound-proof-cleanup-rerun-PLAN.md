# Phase 126 Plan: MolmoSpaces Phase 125 Bound Proof Cleanup Rerun

## Goal

Consume the Phase 125 planner-backed exact proof in the ADR-0003 cleanup
primitive path and verify the final cleanup artifact remains globally honest.

## Tasks

1. Patch bound-object checker validation so inside targets require
   `navigate_to_object`, `pick`, `navigate_to_receptacle`, `open_receptacle`,
   and `place_inside`.
2. Add focused checker coverage for inside-target bound cleanup objects.
3. Rerun `examples/molmospaces_realworld_cleanup.py` with the Phase 125 proof
   attached and `--use-planner-proof-for-cleanup-primitives`.
4. Validate the artifact with robot views, planner proof attachment, bound
   object evidence, mixed primitive evidence, and blocked bridge gates.
5. Record ADR-0117, this plan, `CONTEXT.md`,
   `docs/retrospectives/plans/molmospaces-manipulation-spike.md`, and `.planning/STATE.md`.

## Acceptance Checks

- Focused checker tests pass.
- Cleanup rerun artifact exists under
  `output/debug-phase126-phase125-bound-proof-cleanup-rerun/`.
- `observed_001` to refrigerator is strict planner-backed for the inside
  cleanup sequence.
- At least one unmatched cleanup object remains `api_semantic`, leaving the
  global cleanup primitive gate and bridge blocked.
- The cleanup report renders shared visual core, robot views, planner proof
  views, Cleanup Primitive Gate, and Planner Cleanup Bridge.

## Result

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
- `.venv/bin/ruff check scripts/check_molmo_realworld_cleanup_result.py tests/test_check_molmo_realworld_cleanup_result.py`
- `.venv/bin/ruff format --check scripts/check_molmo_realworld_cleanup_result.py tests/test_check_molmo_realworld_cleanup_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_realworld_cleanup_result.py::test_realworld_cleanup_can_use_proof_bundle_for_full_gate_readiness tests/test_check_molmo_realworld_cleanup_result.py::test_realworld_cleanup_can_use_matching_probe_backed_executor`
