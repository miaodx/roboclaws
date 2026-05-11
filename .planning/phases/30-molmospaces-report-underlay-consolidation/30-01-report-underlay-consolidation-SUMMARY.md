# Phase 30 Summary: Report Underlay Consolidation

Completed: 2026-05-09
Backfilled: 2026-05-11
Source plan: `30-01-report-underlay-consolidation-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Make MolmoSpaces cleanup reports reuse one canonical visual underlay so
current-contract bridge artifacts and ADR-0003 artifacts preserve the same
review rhythm while still rendering their contract-specific evidence.

## Completed Tasks

- Add ADR/source-plan documentation and update roadmap/state/context references.
- Refactor `render_cleanup_report` to assemble sections through a shared canonical sequence.
- Centralize semantic subphase display labels and reuse them across Semantic Substeps, Robot View Timeline, and Cleanup Primitive Gate.
- Add regression tests for visual-core section order and semantic labels.
- Generate and checker-gate a report artifact proving the consolidated underlay.

## Recorded Status

Completed 2026-05-09.

## Evidence

- `uv run ruff check roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/semantic_timeline.py tests/test_molmo_cleanup_report.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/semantic_timeline.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py`
- Synthetic camera-model report artifact plus realworld checker.

Evidence:

- `render_cleanup_report` now assembles sections through one canonical
  Cleanup Artifact Report sequence.
- `semantic_timeline.py` provides shared `nav/object`, `pick/object`,
  `nav/target`, `open/target`, `place/surface`, and `place/inside` display
  labels reused by report sections.
- `output/molmo-realworld-report-underlay/run_result.json` passed
  `--require-camera-model-policy --accept-blocked-planner-cleanup-primitives`.
- `output/molmo-realworld-report-underlay-visual/run_result.json` passed
  `--require-camera-model-policy --require-robot-views --accept-blocked-planner-cleanup-primitives`
  with 2/2 restored targets, 24 robot-view timeline steps, 14 raw FPV
  observations, and the visual core ordered before audit sections.
- Focused ruff and 41 focused pytest tests passed.

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.
