# 43-01 Bounded Planner Cleanup Executor Plan

## Goal

Make the ADR-0003 cleanup harness able to run a bounded shared-loop cleanup
attempt through the probe-backed planner executor when attached proof binding
matches the observed handle and target fixture.

## Status

Completed 2026-05-09.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context.
2. [x] Add an opt-in harness flag/parameter for planner proof cleanup
   primitive execution.
3. [x] Attach strict planner proof before cleanup when the opt-in is enabled.
4. [x] Wrap only matching observed-handle/target cleanup attempts with
   `PlannerBackedCleanupContractAdapter`.
5. [x] Preserve normal semantic cleanup for default and mismatched proof paths.
6. [x] Add focused tests for matching proof, fallback behavior, checker/report
   evidence, and default behavior.
7. [x] Run focused verification gates.

## Acceptance

- Default ADR-0003 cleanup runs remain `api_semantic`.
- With matching bound proof and the opt-in enabled, at least the bounded object
  subphases emit `primitive_provenance=planner_backed` with executor evidence.
- Mismatched proof does not relabel subphases and does not block normal cleanup.
- Cleanup Primitive Gate and Planner Cleanup Bridge visual report sections show
  the new planner-backed evidence.
- The Agent View remains free of planner aliases and private mapping details.

## Verification

- Passed: `uv run ruff check examples/molmospaces_realworld_cleanup.py tests/test_check_molmo_realworld_cleanup_result.py`
- Passed: `uv run ruff format --check examples/molmospaces_realworld_cleanup.py tests/test_check_molmo_realworld_cleanup_result.py`
- Passed: `./scripts/run_pytest_standalone.sh -q tests/test_molmospaces_realworld_cleanup.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_molmo_planner_probe_primitive_executor.py`
- Passed: current real visual artifact checker against
  `output/molmospaces-planner-cleanup-bridge-readiness/run_result.json` with
  bridge accepted as blocked.

## Risks

- Relabeling semantic sync as planner execution would overclaim. The adapter
  must only produce `planner_backed` after the probe-backed executor accepts the
  matching proof binding.
- Applying one proof to every detected object would produce false positives.
  Matching must be object/target specific.

## Completion Notes

`examples/molmospaces_realworld_cleanup.py` now has an opt-in
`--use-planner-proof-for-cleanup-primitives` path. The harness attaches planner
proof before cleanup, builds a `ProbeBackedCleanupPrimitiveExecutor`, and wraps
only the cleanup object whose observed handle and target fixture match the
proof binding.

Default cleanup and mismatched proof stay on the normal `api_semantic` semantic
loop. In the synthetic regression, `observed_001 -> toy_bin_01` emits
planner-backed subphase evidence while later objects remain `api_semantic`, so
the run still does not claim full multi-object planner-backed cleanup.
