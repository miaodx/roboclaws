# 22-01 Real-World Raw FPV Perception Plan

## Goal

Add a raw FPV-only perception mode to ADR-0003 MolmoSpaces cleanup artifacts so
the Cleanup Agent can receive reviewable camera observations without structured
movable-object detections, while preserving the current visible-detection mode
and shared report underlay.

## Status

Completed 2026-05-09. ADR-0013 raw FPV-only observation evidence mode is
implemented, checker-gated, and verified through the real MolmoSpaces/RBY1M
harness.

## Tasks

1. Add ADR/source-plan documentation and update roadmap/state/context
   references for Phase 22.
2. Add a `perception_mode` option to `RealWorldCleanupContract`, deterministic
   real-world cleanup runs, and `molmo_cleanup_realworld` MCP server creation.
3. Implement `raw_fpv_only` observation payloads that record public
   `raw_fpv_observations` and expose no structured object detections.
4. Attach FPV artifacts from existing robot-view capture when robot views are
   recorded, and render a `Raw FPV Observations` report section.
5. Add checker flags, tests, local harness/verify recipes, summary, and
   verification docs.

## Verification

- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_realworld_contract.py tests/test_molmo_realworld_mcp_server.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_verify_just_recipes.py`
- `ruff check` / `ruff format --check` on changed Python files.
- `just verify::molmo-realworld-raw-fpv`

## Risks

- Raw FPV evidence can look like a failed cleanup run unless the checker and
  report state that this is perception-boundary evidence, not a clean policy
  claim.
- The MCP response must not leak categories/support estimates just because the
  default mode still needs them.
- Report additions must reuse `roboclaws/molmo_cleanup/report.py`; a second
  report path would recreate the visual-diff problem this work is meant to
  avoid.
