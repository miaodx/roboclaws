# MolmoSpaces Planner Failure Diagnostic Views

**Status:** Completed under GSD Phase 96 on 2026-05-10
**Created:** 2026-05-10
**Source:** `CONTEXT.md`, ADR-0003, ADR-0087, Phase95 proof execution
**Workflow:** `hybrid-phase-pipeline`

## Problem

The shared cleanup and proof reports now use the same report underlay, but
blocked planner probes can still produce a visually weak result. Phase 95
proofs failed after robot placement and before policy execution, so the normal
initial/final planner screenshots were never created. The bundle report showed
good diagnostics tables but no visual proof surface.

## Decision

Add a shared blocked-proof visual evidence path:

- capture one post-placement camera artifact during task-sampler diagnostics
  when a probe reaches robot placement;
- propagate that artifact through `image_artifacts` for blocked probes;
- render all planner image artifacts generically in standalone probe reports;
- render inline task-sampler diagnostic views when old blocked artifacts have
  diagnostics but no image files.

## Non-Goals

- Do not change proof selection.
- Do not rerun the Phase 95 proof bundle in this phase.
- Do not claim any blocked proof is planner-backed.
- Do not commit ignored `output/` artifacts.

## Acceptance Criteria

- The runner can capture and record a diagnostic post-placement camera image
  through the same `image_artifacts` interface used by successful probes.
- Standalone planner reports render non-initial/final image artifacts.
- Proof-bundle result cards no longer collapse diagnostic-only blocked results
  to an empty "no views" state.
- The checker validates planner probe reports when image artifacts are present.
- Focused tests pass for runner capture, report rendering, and checker behavior.

## Result

Complete on 2026-05-10.

The planner probe runner now captures at most one post-placement diagnostic
camera view during task-sampler placement diagnostics and records it under
`image_artifacts`. Blocked probe results propagate those artifacts to the
shared standalone planner report and proof-bundle result summary path.

The report renderer also handles older diagnostic-only artifacts: if a blocked
probe has task-sampler failure diagnostics but no image files, the report shows
a `Planner Probe Diagnostic Views` panel with a compact placement/grasp visual
instead of an empty no-view note.

Verification:

- `.venv/bin/ruff format --check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
