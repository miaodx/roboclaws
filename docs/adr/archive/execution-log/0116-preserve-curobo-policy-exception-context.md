# 0116. Preserve CuRobo Policy Exception Context

Date: 2026-05-10

## Status

Accepted

## Context

Phase 123 proved the installed droid `Bread_1` loader cache was valid for the
exact `observed_001` refrigerator proof: the task sampler loaded 9 cached
grasps, found 2 non-colliding grasps, and cleared the previous missing-cache
blocker.

The next blocker moved to RBY1M/CuRobo pre-grasp execution:
`_execute_trajectory was called with no planned trajectory or trajectory index >= len(planned_trajectory)`.
The worker stdout timeline contained useful state before that exception, but the
top-level `manipulation_evidence` artifact dropped several fields on the
exception path: the CuRobo memory profile, sampled task binding, promoted
cleanup primitive binding, and the policy primitive phase that failed.

That made the planner probe interface too shallow. Reviewers had to reconstruct
target-runtime state from stdout events instead of reading the stable artifact
contract consumed by reports, checkers, and cleanup proof selection.

## Decision

Preserve target-runtime policy failure state through the worker exception
context and expose it in the shared planner manipulation report.

The worker exception context now carries:

- `curobo_memory_profile`;
- `sampled_task_binding`;
- `cleanup_primitive_binding`;
- `cleanup_primitive_binding_blockers`, including an empty list when the binding
  succeeded;
- `policy_exception_context` with the exception type/message, failure kind,
  policy class, policy phase, action primitive phases, planned-trajectory
  presence/length, and trajectory index.

The report underlay renders this as `Policy Exception Diagnostics`, and the
planner-probe checker can require it with
`--require-policy-exception-context`.

## Consequences

- The artifact interface has better locality: target-runtime failure evidence is
  preserved in `manipulation_evidence`, not split between stdout and HTML.
- ADR-0003 and current-contract report paths keep one planner report underlay;
  no new renderer or one-off report implementation is introduced.
- Future CuRobo fixes can compare the failing primitive phase and trajectory
  state directly from `run_result.json`.
- This does not claim planner-backed cleanup success; the proof remains
  `blocked_capability` until CuRobo generates and executes a valid trajectory.

## Evidence

Implemented in Phase 125 on 2026-05-10.

The local warmed exact proof rerun at
`output/debug-phase125-curobo-pregrasp-exception-context/run_result.json`
returned `planner_backed` with `steps_executed=1`,
`max_abs_qpos_delta=0.018310936580938183`, the low-memory CuRobo profile,
sampled task binding, cleanup primitive binding, and empty cleanup binding
blockers preserved at top level. Because the target-runtime run succeeded, it
did not emit `policy_exception_context`; that exception path is covered by
focused unit tests.

Verification:

- `.venv/bin/ruff check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_molmo_planner_headless_renderer.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff format --check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_molmo_planner_headless_renderer.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_headless_renderer.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase125-curobo-pregrasp-exception-context/run_result.json --require-planner-backed --accept-rby1m-curobo-blocked --require-curobo-extension-cache --require-warp-compatibility --require-cuda-memory --require-curobo-memory-profile --require-cleanup-scene-bound`
