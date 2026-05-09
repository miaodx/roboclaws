# 39-01 Planner Primitive Target Binding Plan

## Goal

Make planner-backed cleanup primitive evidence object-specific by requiring
executor evidence to match the semantic cleanup object and, for target-side
subphases, the target receptacle.

## Status

Planned 2026-05-09.

## Tasks

1. [ ] Add ADR/source-plan documentation and update roadmap/state/context.
2. [ ] Tighten cleanup primitive evidence validation for object binding.
3. [ ] Tighten target-side validation for receptacle binding.
4. [ ] Add focused tests for matching evidence, object mismatch, and target
   mismatch.
5. [ ] Re-run focused executor/gate/bridge/report tests.
6. [ ] Re-run the current real visual artifact checker in blocked mode.

## Acceptance

- `planner_backed` subphases are strict-ready only when evidence matches the
  same object id as the semantic row.
- Target-side subphases are strict-ready only when evidence matches the same
  target receptacle.
- Mismatches produce explicit blockers.
- Default ADR-0003 cleanup artifacts remain blocked without real
  object-specific executor evidence.
- The shared report visual core remains unchanged.

## Verification

- `uv run ruff check` on changed Python/tests.
- `uv run ruff format --check` on changed Python/tests.
- `./scripts/run_pytest_standalone.sh -q` on focused target-binding,
  executor, primitive-gate, bridge, and report tests.
- Real visual artifact checker against
  `output/molmospaces-planner-cleanup-bridge-readiness/run_result.json` with
  bridge accepted as blocked.

## Risks

- Over-tightening target validation could reject legitimate object-only phases.
  Bind targets only for target-side subphases.
- The stricter gate could make old synthetic planner-backed fixtures fail.
  Update tests to include realistic object and target fields.
