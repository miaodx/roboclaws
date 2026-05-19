# MolmoSpaces Camera Model Policy Cleanup

**Status:** Completed under GSD Phase 29 on 2026-05-09
**Created:** 2026-05-09
**Source:** `CONTEXT.md`, ADR-0003, ADR-0009, ADR-0013, ADR-0020, Phase 28 state
**Workflow:** `hybrid-phase-pipeline`

## Problem

The ADR-0003 harness now has a strict public/private boundary, shared visual
report underlay, semantic cleanup subphases, raw FPV evidence mode, planner
proof attachment, cleanup primitive provenance gates, and an RBY1M/CuRobo
runtime gate.

The remaining unblocked perception gap is the original discussion's harder
camera-only policy path. Current clean runs still depend on structured
robot-local visible detections. Raw FPV-only mode proves that structured
detections can be suppressed, but it intentionally cannot clean because no
object handles are registered.

## Decision

Implement ADR-0020 as a camera-model policy cleanup slice.

This phase should:

- add `perception_mode=camera_model_policy` while preserving existing defaults;
- keep `observe` camera-first by recording raw FPV observations and returning
  no built-in visible-object detections;
- add a shared contract method that derives model-labelled candidates from the
  current raw FPV observation and registers them as observed handles;
- reuse the same semantic cleanup loop, report renderer, robot-view timeline,
  Agent View, Private Evaluation, advisory scoring, planner-proof attachment,
  and cleanup primitive gate code;
- add checker support for requiring camera-model policy evidence;
- generate a local artifact proving the shared visual report shape and semantic
  `nav -> pick -> nav -> open? -> place` loop.

## Non-Goals

- Do not claim real VLM pixel inference when the CI/local deterministic policy
  is used.
- Do not expose private generated mess, target count, acceptable destinations,
  `is_misplaced`, target receptacles, or scorer-only truth.
- Do not clone report rendering.
- Do not replace cleanup primitives with planner-backed RBY1M/CuRobo execution.
- Do not make the standalone Franka planner proof satisfy RBY1M cleanup
  primitive readiness.

## Deliverables

- ADR-0020 and this source plan.
- `.planning/milestones/v1.98-phases/29-molmospaces-camera-model-policy-cleanup/29-01-camera-model-policy-cleanup-PLAN.md`.
- Camera-model policy support in `RealWorldCleanupContract`.
- Demo wiring in `examples/molmospaces_realworld_cleanup.py`.
- Report and checker support for `Camera Model Policy`.
- Focused tests for contract behavior, checker enforcement, report rendering,
  and the demo path.
- A local report artifact under `output/molmo-realworld-camera-model-policy/`.

## Acceptance Criteria

- Existing default visible-detection clean gates keep passing.
- Raw FPV-only evidence mode still exposes no structured detections and does
  not require cleanup success.
- Camera-model policy mode records raw FPV observations and camera-model
  candidates with explicit model provenance.
- Camera-model candidates can drive the existing cleanup semantic loop without
  private-truth leaks.
- The shared report renders `Camera Model Policy`, `Raw FPV Observations`,
  `Agent View`, `Private Evaluation`, `Semantic Substeps`, and the existing
  visual sections available for the backend.
- The checker can require camera-model policy evidence and still reject
  `api_semantic` cleanup primitives when strict planner-backed primitives are
  required.

## Verification

- `uv run ruff check` and `uv run ruff format --check` on changed Python files.
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_realworld_contract.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_molmospaces_realworld_cleanup.py`
- `.venv/bin/python examples/molmospaces_realworld_cleanup.py --output-dir output/molmo-realworld-camera-model-policy --perception-mode camera_model_policy`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --require-camera-model-policy --accept-blocked-planner-cleanup-primitives output/molmo-realworld-camera-model-policy/run_result.json`

## Completion Evidence

- Added `perception_mode=camera_model_policy` and
  `infer_camera_model_candidates` to the shared `RealWorldCleanupContract`.
- The deterministic camera model registers observed handles with
  `model_provenance=simulated_camera_model`, `perception_source=camera_model_policy`,
  and source raw FPV observation ids.
- The deterministic demo and realworld MCP surface both reuse the same contract
  primitive and shared report underlay.
- Reports now render `Camera Model Policy` alongside Agent View, Raw FPV
  Observations, Semantic Substeps, Robot View Timeline, Score, Advisory Review,
  Private Evaluation, and the cleanup primitive gate.
- Synthetic artifact:
  `output/molmo-realworld-camera-model-policy/report.html`.
- Real MolmoSpaces/RBY1M visual artifact:
  `output/molmo-realworld-camera-model-policy-visual/report.html`.
- The real visual artifact passed
  `--require-camera-model-policy --require-robot-views --accept-blocked-planner-cleanup-primitives`
  with 2/2 restored targets, 14 raw FPV observations, 14 camera-model events,
  2 model-derived candidates, and 24 robot-view timeline steps.
