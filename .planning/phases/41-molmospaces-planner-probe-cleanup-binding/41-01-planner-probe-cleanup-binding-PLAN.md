# 41-01 Planner Probe Cleanup Binding Plan

## Goal

Make planner probe artifacts emit cleanup primitive binding only when a
requested cleanup object, target, and tool set exactly match the sampled
upstream task.

## Status

Completed 2026-05-09.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context.
2. [x] Add optional cleanup binding request CLI fields to the planner probe.
3. [x] Record sampled pickup/place task binding from the upstream task config.
4. [x] Promote cleanup primitive binding only on exact request/sample match.
5. [x] Add focused tests for matching, mismatch, and no-request behavior.
6. [x] Re-run focused probe/executor/report tests and the current real visual
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

- Passed: `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py tests/test_molmo_planner_headless_renderer.py roboclaws/molmo_cleanup/planner_probe_primitive_executor.py`
- Passed: `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py tests/test_molmo_planner_headless_renderer.py roboclaws/molmo_cleanup/planner_probe_primitive_executor.py`
- Passed: `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_headless_renderer.py tests/test_molmo_planner_probe_primitive_executor.py tests/test_molmo_planner_proof_attachment.py`
- Passed: real visual artifact checker against
  `output/molmospaces-planner-cleanup-bridge-readiness/run_result.json` with
  bridge accepted as blocked.

## Risks

- Accidentally tagging a generic sampled task as cleanup-bound. Promotion must
  require exact requested object/target match.
- The upstream sampled names may use MuJoCo body names while ADR-0003 uses
  observed handles. Mismatches should remain blocked until a real mapping exists.

## Completion Notes

The planner probe now accepts optional requested cleanup object, target, source,
and tool fields. Execute-mode evidence includes `sampled_task_binding`,
`requested_cleanup_primitive_binding`, `cleanup_primitive_binding`, and
`cleanup_primitive_binding_blockers` when applicable. Promotion remains strict:
no request means no cleanup primitive binding, and sampled-task mismatches stay
blocked.
