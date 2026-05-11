# Phase 125 Plan: MolmoSpaces CuRobo Policy Exception Context

## Goal

Preserve the real CuRobo pre-grasp failure state in the planner-probe artifact,
report, and checker after the valid `Bread_1` grasp cache has cleared the prior
blocker.

## Context

Phase 123 reached `execute_policy_run` with a valid exact cleanup binding, 9
cached `Bread_1` grasps, and 2 non-colliding grasps. The run then failed at
CuRobo pre-grasp trajectory execution with no planned trajectory. The worker
stdout had useful staged evidence, but top-level `manipulation_evidence` dropped
the CuRobo memory profile, sampled binding, cleanup binding, and primitive
phase state on the exception path.

## Scope

- Preserve worker exception fields for CuRobo memory profile, sampled task
  binding, cleanup primitive binding, binding blockers, and policy exception
  context.
- Classify the known no-planned-trajectory failure as
  `curobo_no_planned_trajectory`.
- Render `Policy Exception Diagnostics` in the shared planner manipulation
  report.
- Add a checker gate for policy exception context.
- Add focused tests for exception-context preservation, policy failure
  classification, report rendering, and checker enforcement.
- Record ADR-0116, this source plan, `CONTEXT.md`, and `.planning/STATE.md`.

## Acceptance Criteria

- Top-level `manipulation_evidence` preserves the policy failure context after a
  worker exception.
- The report shows failure kind, exception, policy class, policy phase, action
  primitive phase, planned trajectory presence/length, and trajectory index.
- The checker can reject artifacts missing the `Policy Exception Diagnostics`
  panel when policy context is required.
- Focused lint, format, and pytest pass.

## Verification

- `.venv/bin/ruff check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_molmo_planner_headless_renderer.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff format --check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_molmo_planner_headless_renderer.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_headless_renderer.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`

## Result

Complete on 2026-05-10.

The artifact/report/checker seam is implemented and focused tests pass. The
real warmed exact proof rerun at
`output/debug-phase125-curobo-pregrasp-exception-context/run_result.json`
returned `planner_backed` with `steps_executed=1`,
`max_abs_qpos_delta=0.018310936580938183`, preserved CuRobo profile, sampled
task binding, cleanup primitive binding, and no cleanup binding blockers.
Because the real run succeeded, `policy_exception_context` was not emitted by
that artifact; the exception branch is covered by the focused unit tests.
