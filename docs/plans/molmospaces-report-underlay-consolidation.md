# MolmoSpaces Report Underlay Consolidation

**Status:** Completed under GSD Phase 30 on 2026-05-09
**Created:** 2026-05-09
**Source:** `CONTEXT.md`, ADR-0003, ADR-0009, ADR-0021, Phase 29 state
**Workflow:** `hybrid-phase-pipeline`

## Problem

The MolmoSpaces cleanup demos now mostly reuse one report renderer, but the
renderer still lets evidence-slice sections define the artifact shape. That is
why newer ADR-0003 reports can feel different from
`output/molmo-agent-bridge-visual-codex/report.html`: the same visual evidence
exists, but Before/After, Semantic Substeps, Robot View Timeline, and Score can
be pushed below contract-audit panels.

The original discussion also wanted semantic cleanup subphases to read as
`nav, pick, nav, open?, place`, while raw trace artifacts keep full tool names.
That vocabulary should be reused consistently across report sections.

## Decision

Implement ADR-0021 as a small architecture cleanup.

This phase should:

- make the Cleanup Artifact Report assemble sections through a canonical shared
  sequence;
- keep the visual core aligned with the current-contract bridge artifact:
  Before/After, Object Moves, Semantic Substeps, Robot View Timeline, then
  Score;
- move ADR-0003/private/perception/planner audit panels after the visual core;
- centralize report-facing semantic subphase labels in
  `semantic_timeline.py`;
- reuse those labels in semantic cards, robot timeline badges, and cleanup
  primitive gates;
- add focused regression tests so later evidence panels cannot reintroduce a
  second report shape.

## Non-Goals

- Do not remove ADR-0003 Agent View, Private Evaluation, Raw FPV Observations,
  Camera Model Policy, advisory review, or planner evidence.
- Do not hide raw tool names from `trace.jsonl` or `run_result.json`.
- Do not claim planner-backed cleanup primitives; this is report architecture
  and presentation only.
- Do not rerun live OpenClaw Gateway unless the report renderer change requires
  it.

## Deliverables

- ADR-0021 and this source plan.
- `.planning/phases/30-molmospaces-report-underlay-consolidation/30-01-report-underlay-consolidation-PLAN.md`.
- Shared report section assembly in `roboclaws/molmo_cleanup/report.py`.
- Shared semantic subphase display helpers in
  `roboclaws/molmo_cleanup/semantic_timeline.py`.
- Focused report-rendering tests covering section order and semantic labels.
- Regenerated synthetic report artifacts proving the section order.

## Acceptance Criteria

- Current-contract and ADR-0003 reports use one report module and one visual
  core sequence.
- The report visual core appears in this order when data exists:
  Before And After, Object Moves, Semantic Substeps, Robot View Timeline, Score.
- ADR-0003 audit sections still render, but after the shared visual core.
- Semantic subphase labels render as `nav/object`, `pick/object`,
  `nav/target`, optional `open/target`, and `place/surface` or
  `place/inside`.
- Tests fail if Robot View Timeline reverts to raw tool names as the primary
  semantic label.

## Verification

- `uv run ruff check roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/semantic_timeline.py tests/test_molmo_cleanup_report.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/semantic_timeline.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py`
- `.venv/bin/python examples/molmospaces_realworld_cleanup.py --output-dir output/molmo-realworld-report-underlay --perception-mode camera_model_policy --generated-mess-count 2`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --require-camera-model-policy --accept-blocked-planner-cleanup-primitives output/molmo-realworld-report-underlay/run_result.json`

## Completion Evidence

- `render_cleanup_report` now uses one canonical section sequence rather than
  inline section assembly.
- The shared visual core appears before ADR-0003 evidence panels when data is
  present: Before And After, Object Moves, Semantic Substeps, Robot View
  Timeline, then Score.
- `semantic_timeline.py` owns the compact report-facing subphase labels, and
  the report reuses them in Semantic Substeps, Robot View Timeline, and Cleanup
  Primitive Gate.
- Synthetic artifact:
  `output/molmo-realworld-report-underlay/report.html`.
- Real MolmoSpaces/RBY1M visual artifact:
  `output/molmo-realworld-report-underlay-visual/report.html`.
- The real visual artifact passed
  `--require-camera-model-policy --require-robot-views --accept-blocked-planner-cleanup-primitives`
  with 2/2 restored targets, 24 robot-view timeline steps, 14 raw FPV
  observations, and semantic labels including `nav/target` and
  `place/surface`.
