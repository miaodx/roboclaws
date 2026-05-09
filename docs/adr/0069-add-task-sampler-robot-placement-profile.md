# 0069. Add Task Sampler Robot Placement Profile

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0068 made the current `HouseInvalidForTask` blocker concrete: the exact
book/shelf proof request repeatedly fails while the upstream sampler tries to
place the RBY1M near `Book_23`. The default RBY1M task sampler uses a narrow
base-pose radius, a `0.35` safety radius, visibility checking, and a hardcoded
`place_robot_near(max_tries=10)` call.

That left an architectural ambiguity: changing only config fields would look
like a mitigation in `run_result.json`, but it would not necessarily affect the
actual upstream call that is failing.

## Decision

Add a probe-local `--task-sampler-robot-placement-profile` option with a
`relaxed` profile. The profile is explicit evidence, not an invisible upstream
patch. It records before/after task-sampler config and also wraps
`env.place_robot_near` during `_sample_and_place_robot` so the actual call
receives the effective mitigation:

- radius range `[0.0, 1.2]`;
- robot safety radius `0.15`;
- visibility checking disabled;
- `place_robot_near(max_tries=50)`.

Render the profile in planner manipulation reports, carry it through proof
result summaries, and allow proof-bundle commands to request the same profile.

## Consequences

- Future proof artifacts can distinguish "default sampler failed" from
  "relaxed robot-placement mitigation still failed."
- The profile remains probe-local. It does not mutate the MolmoSpaces checkout,
  change ADR-0003 cleanup semantics, or promote planner-backed cleanup
  readiness by itself.
- The Phase 78 warmed artifact proves the mitigation applies to the actual
  `place_robot_near` calls but still fails for the current `Book_23` request.
  The next blocker is therefore deeper scene/task feasibility around robot
  placement near that exact object, not the old hardcoded max-tries value.

## Evidence

Phase 78 wrote
`output/debug-phase78-task-sampler-placement-profile/report.html` and
`run_result.json`.

The warmed local probe completed as `blocked_capability` with blocker
`HouseInvalidForTask`. Its report shows:

- `Task Sampler Robot Placement Profile` with profile `relaxed`;
- before config `[0.0, 0.7]`, safety radius `0.35`, visibility `yes`,
  attempts `10`;
- after config `[0.0, 1.2]`, safety radius `0.15`, visibility `no`,
  attempts `50`;
- 17 `place_robot_near` calls where requested `max_tries=10` became effective
  `max_tries=50`;
- all 17 calls still returned `false` and ended in `RobotPlacementError` for
  `book_be4d759484637aeb579b28e6a954b18d_1_0_8`.

Validation passed with:

```bash
uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py
uv run ruff check scripts/run_molmo_planner_manipulation_probe.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py
./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py
.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase78-task-sampler-placement-profile --accept-blocked-capability --accept-rby1m-curobo-blocked
```
