# MolmoSpaces Focused Report Timeline

**Status:** Completed under GSD Phase 124 on 2026-05-10
**Created:** 2026-05-10
**Source:** User visual review of `output/molmo-agent-bridge-visual-codex/report.html`, ADR-0003, ADR-0009, ADR-0021, ADR-0084, ADR-0111, `CONTEXT.md`
**Workflow:** `hybrid-phase-pipeline`

## Problem

The shared report underlay is now the right architecture, but ADR-0003
camera-model artifacts can still look different from the current-contract visual
bridge because raw FPV scan captures are mixed into the primary Robot View
Timeline. That makes the semantic cleanup sequence harder to review even though
the report has a dedicated Raw FPV Observations section.

The remaining issue is view modeling, not another HTML implementation.

## Decision

Keep the Cleanup Artifact Report visual core focused on semantic cleanup
subphases:

- Before/After;
- Object Moves;
- Semantic Substeps with `nav, pick, nav, open?, place`;
- Robot View Timeline for before/after and semantic cleanup action views;
- Score;
- contract-specific evidence, including Raw FPV Observations.

When raw FPV observations exist, raw scan robot-view captures stay in
`run_result.json` and the Raw FPV Observations panel, but they are filtered from
the first-pass Robot View Timeline. The regeneration CLI now accepts multiple
`run_result.json` paths so stale local artifacts can be repaired through the
same adapter in one command.

## Non-Goals

- Do not remove raw FPV scan artifacts from `run_result.json` or Agent View.
- Do not change ADR-0003 public/private information separation.
- Do not claim planner-backed cleanup primitives.
- Do not create a new report renderer.

## Acceptance Criteria

- The primary Robot View Timeline no longer includes `observe raw_fpv_*` scan
  cards when the report has Raw FPV Observations.
- Raw FPV observations still render after Score in their own evidence section.
- Current-contract report behavior remains unchanged.
- The report regeneration CLI can repair more than one cleanup artifact through
  the existing run-result adapter.
- Focused lint, format, and pytest pass.

## Result

Complete.

`render_cleanup_report` now filters raw FPV observation capture cards out of the
visual-core Robot View Timeline only when raw FPV observations are present.
Semantic action views still show `Subphase: nav/pick/open/place`, role detail,
and raw phase as secondary evidence. The raw scan images continue to render in
Raw FPV Observations after Score.

`scripts/regenerate_molmo_cleanup_report.py` accepts one or more
`run_result.json` paths and returns both a backwards-compatible `report` field
for single-file runs and a `reports` list for batch repair.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/artifact_report.py roboclaws/molmo_cleanup/report.py scripts/regenerate_molmo_cleanup_report.py tests/test_molmo_cleanup_artifact_report.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/artifact_report.py roboclaws/molmo_cleanup/report.py scripts/regenerate_molmo_cleanup_report.py tests/test_molmo_cleanup_artifact_report.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_artifact_report.py tests/test_molmo_cleanup_report.py tests/test_molmo_report_visual_core.py`
