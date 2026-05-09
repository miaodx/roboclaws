# 0071. Add Wide Placement Profile Retry

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0070 made the exact `Book_23` placement blocker measurable. The relaxed
profile searched within `[0.0, 1.2]m`, but the local scene has no free map
points below `1.0m` and only about `1.23%` free area in that annulus. The
nearest free point is about `1.11m` away.

That means the next mitigation should be explicit and reportable: widen the
placement search radius enough to test whether the blocker is only the narrow
annulus or whether collision / reachability remains blocked even from farther
base poses.

## Decision

Add a probe-local `wide` task-sampler robot-placement profile:

- radius range `[0.0, 2.0]`;
- robot safety radius `0.15`;
- visibility checking disabled;
- `max_robot_placement_attempts=100`;
- actual `place_robot_near(max_tries=100)`.

The profile is available in both the planner probe and proof-bundle runner
command generation. It remains visible evidence only and does not promote
cleanup readiness by itself.

## Consequences

- The exact-scene retry can distinguish "narrow placement annulus" from deeper
  collision or reachability blockers.
- Reports continue to show the applied profile, effective placement calls, and
  placement scene diagnostics.
- If the wider profile clears task sampling, downstream planner or binding
  blockers must still be reported normally before any cleanup-readiness claim.

## Evidence

Phase 80 writes `output/debug-phase80-wide-placement-profile/`.

The warmed local artifact remains `blocked_capability`, but the blocker moved:

- profile `wide` rendered with radius `[0.0, 2.0]` and effective
  `place_robot_near(max_tries=100)`;
- 17 placement attempts;
- 17 successful `place_robot_near` calls;
- 0 robot-placement failures;
- 0 asset failures;
- 15 downstream candidate removals;
- final blocker remains `HouseInvalidForTask`.

Placement Scene Diagnostics now show 74,110 valid free points in the
`[0.0, 2.0]m` annulus and free-space fraction `0.147406`, while the nearest
free point is still `1.111824m` away and no free points exist below `1.0m`.

Validation passed with:

```bash
uv run ruff check scripts/run_molmo_planner_manipulation_probe.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_manipulation_probe.py
./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py
.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase80-wide-placement-profile --accept-blocked-capability --accept-rby1m-curobo-blocked
```
