# MolmoSpaces Phase 125 Bound Proof Cleanup Rerun

**Status:** Completed under GSD Phase 126 on 2026-05-10
**Created:** 2026-05-10
**Source:** ADR-0116, Phase 125 proof artifact, ADR-0082, `CONTEXT.md`, `docs/plans/molmospaces-manipulation-spike.md`
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 125 proved the exact `observed_001` to refrigerator planner probe can
execute one RBY1M/CuRobo step with nonzero robot-state movement. The broader
cleanup plan still needs to show that this proof can be consumed by the
ADR-0003 cleanup primitive path and rendered in the cleanup report without
claiming full cleanup bridge readiness.

The bound object is an inside target. The checker must validate
`nav, pick, nav, open, place_inside`, not only surface `nav, pick, nav, place`.

## Decision

Use the existing probe-backed cleanup primitive executor and rerun the
real-world cleanup harness with:

- seed `7`;
- `molmospaces_subprocess`;
- RBY1M robot inclusion;
- robot views;
- generated mess count `10`;
- Phase 125 `run_result.json` as the attached proof;
- `--use-planner-proof-for-cleanup-primitives`.

Patch the bound-object checker to accept inside-target canonical phases. Keep
the strict global bridge behavior unchanged.

## Non-Goals

- Do not claim full planner-backed cleanup from one object proof.
- Do not execute new planner proofs in this phase.
- Do not change the shared semantic cleanup loop.
- Do not hide remaining `api_semantic` subphases.

## Acceptance Criteria

- The cleanup rerun succeeds and records robot views.
- The report renders shared visual core, attached planner proof views, Cleanup
  Primitive Gate, and Planner Cleanup Bridge.
- `observed_001` to refrigerator is strict planner-backed for
  `navigate_to_object`, `pick`, `navigate_to_receptacle`, `open_receptacle`,
  and `place_inside`.
- At least one unmatched object remains `api_semantic`.
- Global cleanup primitive gate and planner cleanup bridge remain blocked.
- Focused lint, format, pytest, and artifact checker gates pass.

## Result

Complete.

The cleanup rerun at
`output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json`
completed with `cleanup_status=success`, `generated_mess_count=10`, 44 robot
timeline steps, and a mixed primitive summary of `planner_backed=5` and
`api_semantic=37`.

`observed_001` to
`refrigerator_5e0d26d670a75ae0a52f2ceb08914b0e_1_0_2` is strict
planner-backed for the inside sequence `nav, pick, nav, open, place`. The full
cleanup artifact remains globally honest: `primitive_provenance=api_semantic`
and `planner_cleanup_bridge_evidence.status=blocked_capability`.

Verification:

- `.venv/bin/python examples/molmospaces_realworld_cleanup.py --output-dir output/debug-phase126-phase125-bound-proof-cleanup-rerun --seed 7 --backend molmospaces_subprocess --fixture-hint-mode room_only --perception-mode visible_object_detections --include-robot --robot-name rby1m --record-robot-views --generated-mess-count 10 --planner-proof-run-result output/debug-phase125-curobo-pregrasp-exception-context/run_result.json --use-planner-proof-for-cleanup-primitives`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json --expect-backend molmospaces_subprocess --min-generated-mess-count 10 --require-robot-views --require-planner-proof-attachment --accept-blocked-planner-cleanup-primitives --require-bound-planner-cleanup-object observed_001:refrigerator_5e0d26d670a75ae0a52f2ceb08914b0e_1_0_2 --require-mixed-planner-cleanup-primitives --accept-blocked-planner-cleanup-bridge`
- `.venv/bin/ruff check scripts/check_molmo_realworld_cleanup_result.py tests/test_check_molmo_realworld_cleanup_result.py`
- `.venv/bin/ruff format --check scripts/check_molmo_realworld_cleanup_result.py tests/test_check_molmo_realworld_cleanup_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_realworld_cleanup_result.py::test_realworld_cleanup_can_use_proof_bundle_for_full_gate_readiness tests/test_check_molmo_realworld_cleanup_result.py::test_realworld_cleanup_can_use_matching_probe_backed_executor`
