# 0070. Render Placement Scene Diagnostics

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0069 proved the relaxed task-sampler robot-placement profile reaches the
actual upstream `place_robot_near` calls. The exact `Book_23` proof request
still fails after the effective mitigation is applied, so the next useful
evidence is not another profile flag. We need to see whether the scene map has
enough free robot-placement area around the requested pickup object.

The upstream placement function already computes occupancy-map free points near
the target, but its logs are not durable report evidence and are hard to review
inside proof-bundle artifacts.

## Decision

Record a probe-local placement scene diagnostic for each observed
`place_robot_near` call. The diagnostic captures the target position, sampling
radius, safety radius, total map free points, valid free points in the sampling
annulus, free-space fraction, nearest free point, and radius-band counts.

Render that data as a `Placement Scene Diagnostics` view in planner probe
reports, and surface compact free-space metrics in proof-bundle result cards.
The diagnostic remains explanatory evidence only; it does not change sampling,
cleanup semantics, or planner-backed readiness.

## Consequences

- Future `HouseInvalidForTask` artifacts can show whether the target-side
  blocker is free-space scarcity around the pickup object.
- The report keeps one shared visual underlay while adding a specific evidence
  panel for the active blocker.
- The next mitigation can be chosen from concrete map evidence instead of
  relying on stderr warnings or hidden upstream logs.

## Evidence

Phase 79 validates the new schema and report section with focused unit tests and
writes `output/debug-phase79-placement-scene-diagnostics/report.html`.

The warmed local artifact remains `blocked_capability`, but the report now
shows:

- 17 placement attempts and 17 `place_robot_near` calls;
- target `book_be4d759484637aeb579b28e6a954b18d_1_0_8`;
- sampling radius `[0.0, 1.2]`;
- 2,231 valid free map points in the annulus;
- free-space fraction `0.012326`;
- nearest free point distance `1.111824m`;
- zero free points in each radius band below `1.0m`.

Validation passed with:

```bash
uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py
./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py
.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase79-placement-scene-diagnostics --accept-blocked-capability --accept-rby1m-curobo-blocked
```
