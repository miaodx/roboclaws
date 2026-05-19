# Phase 96-01: Planner Failure Diagnostic Views

## Goal

Make blocked MolmoSpaces planner proof reports visually reviewable even when
the proof fails during task sampling before normal initial/final planner views
exist.

## Tasks

- Add bounded post-placement camera capture to task-sampler failure diagnostics.
- Propagate blocked-probe diagnostic images through the existing
  `image_artifacts` interface.
- Render generic planner image artifacts in standalone probe reports.
- Render inline task-sampler diagnostic views when blocked artifacts have
  diagnostics but no image files.
- Add focused tests for runner capture, report rendering, and checker coverage.
- Update ADR, plan, CONTEXT, and planning state with the result.

## Acceptance

- Future blocked proof probes can emit at least one visual artifact after robot
  placement.
- Existing diagnostic-only blocked reports render an inline diagnostic view
  instead of an empty no-view surface.
- Focused lint and pytest pass.
- The phase is committed with code, tests, and docs.

## Result

Complete on 2026-05-10.

Implemented:

- task-sampler failure diagnostics capture one bounded post-placement camera
  artifact under `image_artifacts`;
- blocked probe results carry those artifacts into the shared report path;
- planner reports render arbitrary image artifacts instead of only
  `initial`/`final`;
- diagnostic-only blocked artifacts render an inline task-sampler visual view;
- the planner probe checker verifies image artifact report coverage when
  image artifacts are present.

Verification:

- `.venv/bin/ruff format --check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
