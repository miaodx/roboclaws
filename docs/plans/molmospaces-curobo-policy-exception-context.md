# MolmoSpaces CuRobo Policy Exception Context

**Status:** Completed under GSD Phase 125 on 2026-05-10
**Created:** 2026-05-10
**Source:** `CONTEXT.md`, ADR-0114, ADR-0115, `output/debug-phase123-cache-ready-proof001-warmed-rerun/run_result.json`, user architecture review
**Workflow:** `hybrid-phase-pipeline`

## Problem

The cache-ready exact proof cleared the `Bread_1` grasp-cache blocker, but the
next RBY1M/CuRobo failure collapsed into a generic `ValueError` blocker at the
top-level artifact. The stdout worker timeline showed more state than
`manipulation_evidence`: the low-memory CuRobo profile was applied, the sampled
task matched the requested cleanup binding, and execution reached the policy run
before failing at pre-grasp trajectory execution.

That is a report and architecture gap. The shared planner-probe artifact should
be the stable interface for failures; stdout should remain supporting evidence,
not the only place where target-runtime state survives.

## Zoomed-Out Module Map

- `scripts/run_molmo_planner_manipulation_probe.py` owns the planner probe
  subprocess, target-runtime adapters, worker exception context, and
  `run_result.json` artifact.
- `roboclaws/molmo_cleanup/report.py` owns the shared planner manipulation
  report underlay consumed by both current-contract and ADR-0003 proof review.
- `scripts/check_molmo_planner_manipulation_probe.py` owns artifact/report
  validation and strict readiness gates.
- `tests/test_molmo_planner_headless_renderer.py`,
  `tests/test_molmo_cleanup_report.py`, and
  `tests/test_check_molmo_planner_manipulation_probe.py` are the focused test
  surface for this seam.

## Decision

Deepen the worker exception context interface instead of adding another report
path. The exception context now preserves the CuRobo memory profile, sampled
task binding, cleanup primitive binding, empty-or-nonempty binding blockers, and
a structured policy exception context.

The report renders `Policy Exception Diagnostics`; the checker can require the
same panel via `--require-policy-exception-context`.

## Non-Goals

- Do not change the semantic cleanup subphase vocabulary
  `nav, pick, nav, open?, place`.
- Do not claim planner-backed cleanup success.
- Do not rewrite the CuRobo planner or invent a second trajectory interface.
- Do not create a new report renderer.

## Acceptance Criteria

- A worker exception after task sampling preserves `curobo_memory_profile`,
  `sampled_task_binding`, `cleanup_primitive_binding`,
  `cleanup_primitive_binding_blockers`, and `policy_exception_context` in
  `manipulation_evidence`.
- Policy exceptions classify the current failure as
  `curobo_no_planned_trajectory` and record primitive phase/trajectory state.
- Planner reports render `Policy Exception Diagnostics`.
- The checker can require the policy exception context and report panel.
- Focused lint, format, and pytest pass.

## Result

Complete.

The implementation is complete for the artifact/report/checker seam. The worker
exception path is unit-covered, including the
`curobo_no_planned_trajectory` classification and report/checker rendering.

The local warmed exact proof rerun no longer reproduced the pre-grasp failure:
`output/debug-phase125-curobo-pregrasp-exception-context/run_result.json`
returned `planner_backed` with `steps_executed=1` and
`max_abs_qpos_delta=0.018310936580938183`. The top-level artifact now preserves
the low-memory CuRobo profile, sampled task binding, cleanup primitive binding,
and empty cleanup binding blockers. Because the real run succeeded, it did not
emit `policy_exception_context`; that branch remains covered by focused unit
tests.

Verification completed:

- `.venv/bin/ruff check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_molmo_planner_headless_renderer.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff format --check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_molmo_planner_headless_renderer.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_headless_renderer.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase125-curobo-pregrasp-exception-context/run_result.json --require-planner-backed --accept-rby1m-curobo-blocked --require-curobo-extension-cache --require-warp-compatibility --require-cuda-memory --require-curobo-memory-profile --require-cleanup-scene-bound`
