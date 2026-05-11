# 30-01 Report Underlay Consolidation Plan

## Goal

Make MolmoSpaces cleanup reports reuse one canonical visual underlay so
current-contract bridge artifacts and ADR-0003 artifacts preserve the same
review rhythm while still rendering their contract-specific evidence.

## Status

Completed 2026-05-09.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context
   references.
2. [x] Refactor `render_cleanup_report` to assemble sections through a shared
   canonical sequence.
3. [x] Centralize semantic subphase display labels and reuse them across
   Semantic Substeps, Robot View Timeline, and Cleanup Primitive Gate.
4. [x] Add regression tests for visual-core section order and semantic labels.
5. [x] Generate and checker-gate a report artifact proving the consolidated
   underlay.

## Acceptance

- The shared visual core order is Before And After, Object Moves, Semantic
  Substeps, Robot View Timeline, Score when those sections exist.
- ADR-0003-only audit sections still render after the shared visual core.
- Report-facing semantic labels are `nav/object`, `pick/object`, `nav/target`,
  optional `open/target`, and `place/surface` or `place/inside`.
- Raw tool names remain available as trace/checker data but are no longer the
  primary visual phase vocabulary.

## Verification

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

## Risks

- Moving audit sections must not hide ADR-0003 public/private evidence. Keep
  those sections visible, just downstream of the shared visual core.
- Tests should pin section order without overfitting incidental CSS.
