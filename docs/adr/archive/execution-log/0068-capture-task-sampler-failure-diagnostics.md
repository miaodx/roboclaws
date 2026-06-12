# 0068. Capture Task Sampler Failure Diagnostics

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0067 preserved exact sampler context through `HouseInvalidForTask`, proving
that the probe had applied the requested cleanup scene, pickup alias, and target
sampler adapter before upstream task sampling failed. The next question was
still hidden in upstream internals: did the sampler fail because of alias
selection, target adaptation, robot placement, grasp filtering, or some other
task-generation step?

The warmed artifact's stderr contained a useful clue, a dynamic blacklist line
for the book asset after repeated robot-placement failures. That clue should not
remain only as unstructured stderr archaeology.

## Decision

The planner manipulation probe will install a probe-local task-sampler
diagnostic adapter after constructing the upstream sampler. The adapter will
wrap sampler hooks that already participate in task feasibility:

- `_sample_and_place_robot` to record robot-placement attempts and exceptions;
- `report_asset_failure` to record asset-level failure reasons;
- `_remove_candidate_object` to record candidates removed from consideration.

The probe will persist these diagnostics in `run_result.json` as
`task_sampler_failure_diagnostics`, render them in the planner manipulation
report, carry them into proof-result summaries, and surface compact counts in
proof-bundle runner reports. Existing probe and runner checkers will validate
the report text when this evidence exists.

## Consequences

- Target-side `HouseInvalidForTask` artifacts now show the upstream sampler
  failure mode directly. For the current book/shelf request, the failure is
  repeated robot placement of `Book_23`, not lost aliases or missing sampler
  adaptation.
- The diagnostic adapter remains probe-local and does not patch the upstream
  checkout or change cleanup behavior.
- This still does not make the task feasible or promote planner-backed cleanup
  readiness. It only narrows the next mitigation choice.

## Evidence

Phase 77 wrote
`output/debug-phase77-task-sampler-failure-diagnostics/report.html` and
`run_result.json`.

The warmed local probe completed as `blocked_capability` with blocker
`HouseInvalidForTask`. Its task-sampler diagnostics reported:

- `robot_placement_attempt_count=17`;
- `robot_placement_failure_count=17`;
- `asset_failure_count=17`;
- `candidate_removal_count=17`;
- `asset_uid=Book_23`;
- final failure `RobotPlacementError: Failed to place robot near object:
  book_be4d759484637aeb579b28e6a954b18d_1_0_8`;
- robot-placement config included `base_pose_sampling_radius_range=[0.0, 0.7]`,
  `robot_safety_radius=0.35`, visibility checking enabled, and
  `max_robot_placement_attempts=10`.

Validation passed with:

```bash
uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py
uv run ruff check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py
./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py
.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase77-task-sampler-failure-diagnostics --accept-blocked-capability --accept-rby1m-curobo-blocked
```
