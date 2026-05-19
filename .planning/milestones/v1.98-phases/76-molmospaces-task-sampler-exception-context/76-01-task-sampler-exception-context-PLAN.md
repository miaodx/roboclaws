# Phase 76 Plan: MolmoSpaces Task Sampler Exception Context

## Goal

Preserve exact cleanup task-sampler context when upstream task sampling raises
before normal planner-probe completion.

## Tasks

1. Add worker-exception context capture to the planner manipulation probe.
2. Record exact cleanup task config before task-sampler construction can fail.
3. Record exact task-sampler adapter state before `sample_task()` can fail.
4. Carry sampler adapter evidence into proof-result summaries.
5. Render sampler adapter evidence in proof-bundle runner reports.
6. Tighten probe and bundle checkers for sampler-context report text.
7. Validate with focused tests and a warmed local probe that reaches
   `HouseInvalidForTask`.

## Acceptance Checks

- Worker-exception probe outputs include `cleanup_task_config`,
  `cleanup_task_sampler_adapter`, and `requested_cleanup_primitive_binding`.
- Proof-result summaries preserve `cleanup_task_sampler_adapter`.
- Runner reports show exact sampler adapter applied/class/target rows.
- The warmed local probe checker passes on a `HouseInvalidForTask` artifact.
- Planner-backed cleanup readiness remains blocked until upstream task
  feasibility is solved.

## Result

Completed on 2026-05-10.

The warmed local probe at
`output/debug-phase76-task-sampler-context-probe-warmed/` reached
`execute_task_sample_start`, failed with `HouseInvalidForTask`, and preserved
the exact sampler adapter context:

- `cleanup_task_config.applied=true`
- `cleanup_task_sampler_adapter.applied=true`
- `cleanup_task_sampler_adapter.task_sampler_class=PickAndPlaceTaskSampler`
- `cleanup_task_sampler_adapter.planner_target_receptacle_id=shelf_140ccb7e1f5028c7d773229dfe6e1a04_1_1_2`
- `last_worker_stage=worker_exception`

The first direct attempt at
`output/debug-phase76-task-sampler-context-probe/` timed out during
`rby1m_config_import` and is not acceptance evidence for sampler context.

## Validation

- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py`
- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase76-task-sampler-context-probe-warmed --accept-blocked-capability --accept-rby1m-curobo-blocked`

## Status

Complete.
