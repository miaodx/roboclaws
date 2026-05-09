# 41-01 Planner Probe Cleanup Binding Plan

## Goal

Make planner probe artifacts emit cleanup primitive binding only when a
requested cleanup object, target, and tool set exactly match the sampled
upstream task.

## Status

Planned 2026-05-09.

## Tasks

1. [ ] Add ADR/source-plan documentation and update roadmap/state/context.
2. [ ] Add optional cleanup binding request CLI fields to the planner probe.
3. [ ] Record sampled pickup/place task binding from the upstream task config.
4. [ ] Promote cleanup primitive binding only on exact request/sample match.
5. [ ] Add focused tests for matching, mismatch, and no-request behavior.
6. [ ] Re-run focused probe/executor/report tests and the current real visual
   artifact checker.

## Acceptance

- Generic probe runs remain target runtime proof only and do not emit cleanup
  primitive binding.
- Matching requested object/target/tools emit
  `planner_probe_cleanup_primitive_binding_v1`.
- Mismatches emit explicit blockers.
- Phase 40 probe-backed executor can consume promoted binding.
- Current ADR-0003 visual artifacts remain blocked without bound probe proof.

## Verification

- `uv run ruff check` on changed Python/tests.
- `uv run ruff format --check` on changed Python/tests.
- `./scripts/run_pytest_standalone.sh -q` on focused probe, executor,
  attachment, gate, bridge, and report tests.
- Real visual artifact checker against
  `output/molmospaces-planner-cleanup-bridge-readiness/run_result.json` with
  bridge accepted as blocked.

## Risks

- Accidentally tagging a generic sampled task as cleanup-bound. Promotion must
  require exact requested object/target match.
- The upstream sampled names may use MuJoCo body names while ADR-0003 uses
  observed handles. Mismatches should remain blocked until a real mapping exists.
