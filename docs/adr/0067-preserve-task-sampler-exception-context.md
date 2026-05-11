# 0067. Preserve Task Sampler Exception Context

Date: 2026-05-10

## Status

Accepted

## Context

Phase 75 made the target-feasibility blocker matrix reviewable, but the linked
Phase 65 target-side fallback proof reports still required guesswork. The proof
outputs failed with upstream `HouseInvalidForTask` during `sample_task()`, before
the normal policy-execution evidence path returned sampled-task and cleanup
binding data.

That exception path kept the requested cleanup binding and exact task config,
but it did not preserve whether the exact task-sampler adapter had already been
applied. Reviewers could see a target feasibility block, but not prove from the
artifact that the target planner alias was forced into the sampler before the
upstream feasibility rejection.

## Decision

The planner manipulation probe will keep a worker-exception context while the
worker configures exact cleanup task sampling. When an exception occurs before
normal probe completion, the worker result will still include:

- exact cleanup task config;
- exact cleanup task sampler adapter state;
- requested cleanup primitive binding;
- worker stage and runtime diagnostics already emitted by the probe.

The proof-result summary and proof-bundle runner report will carry and render
that sampler adapter context. The probe checker and bundle checker will validate
that report text when sampler-context evidence exists.

## Consequences

- `HouseInvalidForTask` is no longer a context-free task-sampling failure.
  Reports can show that the exact target sampler adapter was applied before the
  upstream feasibility blocker fired.
- The shared report architecture remains intact: probe evidence flows into the
  proof-result summary and the existing proof-bundle runner report instead of
  creating a separate target-feasibility report implementation.
- This improves the next upstream task-feasibility slice, but does not solve
  robot placement feasibility or claim planner-backed cleanup readiness.

## Evidence

Phase 76 wrote a warmed local probe artifact at
`output/debug-phase76-task-sampler-context-probe-warmed/report.html`.

The warmed retry used the Phase 65 Torch extension cache and completed as
`blocked_capability` with real `HouseInvalidForTask`. The worker reached
`execute_task_sample_start`, then preserved:

- `cleanup_task_config.applied=true`;
- `cleanup_task_sampler_adapter.applied=true`;
- `cleanup_task_sampler_adapter.task_sampler_class=PickAndPlaceTaskSampler`;
- `cleanup_task_sampler_adapter.planner_target_receptacle_id=shelf_140ccb7e1f5028c7d773229dfe6e1a04_1_1_2`;
- `requested_cleanup_primitive_binding` for the same cleanup object/target;
- `last_worker_stage=worker_exception` and `worker_returncode=3`.

The first direct local attempt at
`output/debug-phase76-task-sampler-context-probe` timed out during
`rby1m_config_import`; it is retained only as failed warmup/cache evidence, not
as acceptance evidence for sampler context.

Validation passed with:

```bash
uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py
uv run ruff check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py
./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py
.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase76-task-sampler-context-probe-warmed --accept-blocked-capability --accept-rby1m-curobo-blocked
```
