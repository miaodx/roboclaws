# 43-01 Bounded Planner Cleanup Executor Plan

## Goal

Make the ADR-0003 cleanup harness able to run a bounded shared-loop cleanup
attempt through the probe-backed planner executor when attached proof binding
matches the observed handle and target fixture.

## Status

Planned 2026-05-09.

## Tasks

1. [ ] Add ADR/source-plan documentation and update roadmap/state/context.
2. [ ] Add an opt-in harness flag/parameter for planner proof cleanup
   primitive execution.
3. [ ] Attach strict planner proof before cleanup when the opt-in is enabled.
4. [ ] Wrap only matching observed-handle/target cleanup attempts with
   `PlannerBackedCleanupContractAdapter`.
5. [ ] Preserve normal semantic cleanup for default and mismatched proof paths.
6. [ ] Add focused tests for matching proof, fallback behavior, checker/report
   evidence, and default behavior.
7. [ ] Run focused verification gates.

## Acceptance

- Default ADR-0003 cleanup runs remain `api_semantic`.
- With matching bound proof and the opt-in enabled, at least the bounded object
  subphases emit `primitive_provenance=planner_backed` with executor evidence.
- Mismatched proof does not relabel subphases and does not block normal cleanup.
- Cleanup Primitive Gate and Planner Cleanup Bridge visual report sections show
  the new planner-backed evidence.
- The Agent View remains free of planner aliases and private mapping details.

## Verification

- `uv run ruff check` on changed Python/tests.
- `uv run ruff format --check` on changed Python/tests.
- Focused pytest for the real-world cleanup harness, real-world checker,
  planner probe executor, and report coverage.
- Current real visual artifact checker in blocked mode.

## Risks

- Relabeling semantic sync as planner execution would overclaim. The adapter
  must only produce `planner_backed` after the probe-backed executor accepts the
  matching proof binding.
- Applying one proof to every detected object would produce false positives.
  Matching must be object/target specific.
