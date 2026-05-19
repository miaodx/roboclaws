# Phase 124 Plan: MolmoSpaces Focused Report Timeline

## Goal

Make ADR-0003 cleanup reports match the current-contract visual bridge rhythm
more closely by keeping the primary Robot View Timeline focused on semantic
cleanup subphases.

## Context

The shared underlay and artifact regeneration adapter already removed the
duplicated renderer problem. The remaining visual difference is that
camera-model ADR-0003 artifacts include raw FPV scan robot-view captures before
the cleanup actions, while the desired bridge artifact foregrounds the cleanup
loop itself: `nav, pick, nav, open?, place`.

## Scope

- Filter raw FPV observation capture cards from the visual-core Robot View
  Timeline when Raw FPV Observations are present.
- Keep raw FPV evidence in `run_result.json`, Agent View, and Raw FPV
  Observations.
- Let the report-regeneration CLI accept multiple run-result paths through the
  existing Cleanup Report Artifact Adapter.
- Record ADR-0115, this source plan, `CONTEXT.md`, and `.planning/STATE.md`.

## Acceptance Criteria

- Raw FPV scan cards are absent from the Robot View Timeline slice between
  `Robot View Timeline` and `Score` when a Raw FPV Observations panel exists.
- The same raw FPV observation IDs and images still appear in Raw FPV
  Observations.
- Semantic cleanup action views still show compact subphase labels.
- Focused lint, format, and pytest pass.

## Verification

- `.venv/bin/ruff check roboclaws/molmo_cleanup/artifact_report.py roboclaws/molmo_cleanup/report.py scripts/regenerate_molmo_cleanup_report.py tests/test_molmo_cleanup_artifact_report.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/artifact_report.py roboclaws/molmo_cleanup/report.py scripts/regenerate_molmo_cleanup_report.py tests/test_molmo_cleanup_artifact_report.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_artifact_report.py tests/test_molmo_cleanup_report.py tests/test_molmo_report_visual_core.py`

## Result

Complete on 2026-05-10.

The report keeps raw FPV perception evidence but moves it out of the
first-pass Robot View Timeline. The visual core now reviews semantic cleanup
actions before the post-score ADR-0003 evidence panels.
