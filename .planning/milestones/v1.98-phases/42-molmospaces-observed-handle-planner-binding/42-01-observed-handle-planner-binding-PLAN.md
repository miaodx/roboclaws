# 42-01 Observed Handle Planner Binding Plan

## Goal

Bridge ADR-0003 observed handles to planner-facing sampled task names so
planner probe proof can match upstream task aliases while cleanup primitive
binding still matches the public cleanup subphase request.

## Status

Completed 2026-05-09.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context.
2. [x] Add an observed-handle planner binding helper/schema.
3. [x] Add backend runtime planner-name binding for semantic and MolmoSpaces
   subprocess backends.
4. [x] Extend planner probe cleanup binding requests with planner-facing object
   and target aliases.
5. [x] Ensure promoted cleanup primitive binding keeps public observed handle
   IDs for executor matching.
6. [x] Render/check planner alias binding evidence in reports.
7. [x] Add focused tests and run verification gates.

## Acceptance

- Observed handles resolve only after public observation registered the handle.
- Planner alias fields can match sampled upstream task names without replacing
  the cleanup-facing object/target IDs.
- Probe-backed executor accepts a promoted binding whose `object_id` is the
  observed handle and whose alias evidence matched the sampled planner task.
- Planner aliases remain artifact/private runtime evidence and are not added to
  Agent View.
- Generic Phase 41 no-alias behavior remains backward compatible.

## Verification

- Passed: `uv run ruff check roboclaws/molmo_cleanup/planner_observed_binding.py roboclaws/molmo_cleanup/backend.py roboclaws/molmo_cleanup/subprocess_backend.py roboclaws/molmo_cleanup/realworld_contract.py roboclaws/molmo_cleanup/__init__.py roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/planner_probe_primitive_executor.py scripts/run_molmo_planner_manipulation_probe.py tests/test_molmo_planner_observed_binding.py tests/test_molmo_planner_headless_renderer.py tests/test_molmo_planner_probe_primitive_executor.py tests/test_molmo_cleanup_report.py tests/test_molmo_realworld_contract.py`
- Passed: `uv run ruff format --check roboclaws/molmo_cleanup/planner_observed_binding.py roboclaws/molmo_cleanup/backend.py roboclaws/molmo_cleanup/subprocess_backend.py roboclaws/molmo_cleanup/realworld_contract.py roboclaws/molmo_cleanup/__init__.py roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/planner_probe_primitive_executor.py scripts/run_molmo_planner_manipulation_probe.py tests/test_molmo_planner_observed_binding.py tests/test_molmo_planner_headless_renderer.py tests/test_molmo_planner_probe_primitive_executor.py tests/test_molmo_cleanup_report.py tests/test_molmo_realworld_contract.py`
- Passed: `./scripts/run_pytest_standalone.sh -q tests/test_molmo_realworld_contract.py tests/test_molmo_planner_observed_binding.py tests/test_molmo_planner_headless_renderer.py tests/test_molmo_planner_probe_primitive_executor.py tests/test_molmo_cleanup_report.py`
- Passed: current real visual artifact checker against
  `output/molmospaces-planner-cleanup-bridge-readiness/run_result.json` with
  bridge accepted as blocked.

## Risks

- Leaking planner aliases through public ADR-0003 tool responses would violate
  the Agent View boundary.
- Treating a planner alias match as cleanup execution would overclaim. This
  phase should only make a proof consumable by the executor; the actual shared
  loop remains blocked until a later slice wires the executor into cleanup
  subphases.

## Completion Notes

`observed_handle_planner_binding_v1` now keeps public cleanup IDs and
planner-facing aliases in separate fields. The planner probe compares aliases to
sampled task names, but promoted cleanup primitive binding keeps the observed
handle so `ProbeBackedCleanupPrimitiveExecutor` can match the ADR-0003 cleanup
request.
