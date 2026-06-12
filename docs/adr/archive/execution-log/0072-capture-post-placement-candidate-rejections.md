# 0072. Capture Post-Placement Candidate Rejections

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0071 showed the wide placement profile clears robot placement for the exact
`Book_23` request: all 17 `place_robot_near` calls succeeded. The task still
ended in `HouseInvalidForTask` after downstream candidate removals.

The existing task-sampler diagnostics showed candidate removals but not the
post-placement cause. The upstream sampler can reject a placed candidate during
grasp-feasibility checks, and `report_grasp_failure` removes an object after a
threshold. That needs to be rendered explicitly before choosing another
mitigation.

## Decision

Wrap `report_grasp_failure` in the probe-local task-sampler diagnostics
adapter. Record object name, failure count before and after, threshold,
candidate pool size before and after, and whether that call removed the
candidate.

Render the data as `Post-Placement Candidate Rejections` in planner probe
reports and surface compact counts in proof-bundle result cards.

## Consequences

- Wide-profile artifacts can distinguish robot-placement success from later
  grasp/candidate rejection.
- The next mitigation can target grasp feasibility or candidate selection
  rather than continuing to tune robot placement.
- The diagnostic remains report evidence only and does not change cleanup
  semantics or planner-backed readiness.

## Evidence

Phase 81 writes `output/debug-phase81-post-placement-rejections/`.

The warmed local artifact remains `blocked_capability`, but it now explains the
moved blocker:

- profile `wide`;
- 17 successful robot-placement calls;
- 0 robot-placement failures;
- 17 grasp-failure reports for
  `book_be4d759484637aeb579b28e6a954b18d_1_0_8`;
- 15 candidate-removal calls;
- final blocker remains `HouseInvalidForTask`.

The candidate pool size did not decrease during the recorded
`report_grasp_failure` calls, which suggests the exact forced alias is not being
removed from the upstream candidate list even after thresholded grasp failures.

Validation passed with:

```bash
uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py
./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py
.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase81-post-placement-rejections --accept-blocked-capability --accept-rby1m-curobo-blocked
```
