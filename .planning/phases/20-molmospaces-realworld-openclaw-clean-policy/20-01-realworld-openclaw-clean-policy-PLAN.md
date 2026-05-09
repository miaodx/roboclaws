# 20-01 Real-World OpenClaw Clean Policy Plan

## Goal

Harden the ADR-0003 `molmo_cleanup_realworld` MCP surface so OpenClaw and other
external agents cannot silently skip the public semantic cleanup loop. Clean
artifacts should show the same `nav -> pick -> nav -> open? -> place` subphase
shape that the shared report underlay expects.

## Status

Completed 2026-05-09. The ADR-0003 real-world MCP contract now rejects skipped
semantic phases with public `semantic_order` guidance, and the strict clean
checker rejects nonzero semantic-order errors.

## Tasks

1. Add ADR/source-plan documentation for the semantic-order decision and update
   roadmap/state/context references for Phase 20.
2. Add contract-level semantic-order guards:
   - `pick` requires matching `navigate_to_object`;
   - `place` requires matching `navigate_to_receptacle`;
   - `place_inside` also requires `open_receptacle` for fridge-like targets.
3. Add public recovery guidance and diagnostics without exposing private
   Generated Mess Set or scorer truth.
4. Update tests, the strict checker, the OpenClaw cleanup skill, and the server
   kickoff text.
5. Run focused tests/recipes, write Phase 20 summary and verification docs, and
   record whether any live Gateway rerun was attempted.

## Verification

- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_realworld_contract.py tests/test_molmo_realworld_mcp_server.py tests/test_check_molmo_realworld_cleanup_result.py`
- `ruff check` / `ruff format --check` on changed Python files.
- `just verify::molmo-realworld-agent-dogfood-kit`

## Risks

- Strict ordering may initially make weak live Gateway policies fail faster. That
  is intentional for clean-policy evidence, but the error payload must include
  enough public guidance for recovery.
- The semantic timeline should keep raw failed calls visible without cloning a
  report path.
- Existing deterministic smoke tests should keep passing because they already
  follow the full semantic loop.
