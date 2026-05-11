# 15-01 Generated Mess Set Scale Plan

## Goal

Close the `CONTEXT.md` Generated Mess Set scale gap by making the ADR-0003
real-world cleanup harness request and score at least 10 hidden generated
objects while preserving the Phase 14 public/private boundary and report views.

## Context

- ADR-0003 separates Cleanup Agent public inputs from private Mess Generator and
  Scorer truth.
- ADR-0005 locks the architectural decision to use a configurable Generated
  Mess Set size.
- Phase 14 shipped the public/private contract and robot-view visual parity but
  retained the historical fixed five-object selector.

## Tasks

1. Add generated-count configuration to the MolmoSpaces subprocess path:
   worker CLI, backend constructor, target selection, and private manifest
   threshold derivation.
2. Thread the requested count through
   `examples/molmospaces_realworld_cleanup.py` and the `just` harness/verify
   recipes.
3. Update reports and checker output so requested and actual generated counts
   are explicit, and add a checker flag for a minimum generated count.
4. Add focused tests for the new configuration, selector behavior, and checker
   gate.
5. Run focused tests, ruff checks, and a real one-seed MolmoSpaces harness run
   that produces all visual report views with at least 10 generated objects.

## Verification

- `pytest -q tests/test_molmospaces_realworld_cleanup.py tests/test_check_molmo_realworld_cleanup_result.py`
- `ruff check` and `ruff format --check` on changed Python files.
- `just harness::molmo-realworld-cleanup 1 output/molmo-realworld-cleanup-harness-scale-check "帮我收拾这个房间" 10`
- `just verify::molmo-realworld-cleanup output/molmo-realworld-cleanup-harness-scale-check 10`

## Risks

- Some MolmoSpaces scenes may not have enough movable objects for larger hidden
  sets. The worker should fail during setup with a clear count-specific error
  rather than silently shrinking the scenario.
- Larger sets increase runtime and artifact volume. Phase 15 requires one real
  visual evidence seed; broader multi-seed evidence can follow once policy
  evaluation starts.
