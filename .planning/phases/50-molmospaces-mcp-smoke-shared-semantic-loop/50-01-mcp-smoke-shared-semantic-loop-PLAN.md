# 50-01 MCP Smoke Shared Semantic Loop Plan

## Goal

Remove the remaining hand-written MCP smoke cleanup loops so current-contract
and ADR-0003 smoke demos reuse the shared semantic cleanup loop and report-facing
subphase vocabulary.

## Status

Planned 2026-05-10.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context.
2. [ ] Refactor current-contract MCP smoke to call `run_semantic_cleanup_loop`.
3. [ ] Refactor ADR-0003 MCP smoke to call `run_semantic_cleanup_loop`.
4. [ ] Add focused tests that prove both smoke scripts use the shared loop seam.
5. [ ] Run focused verification gates.

## Acceptance

- `scripts/run_molmo_agent_bridge_smoke.py` uses the shared semantic loop and
  still records current-contract `object_done`.
- `scripts/run_molmo_realworld_agent_mcp_smoke.py` uses the shared semantic loop
  with fixture-style target requests and no `object_done`.
- Tests cover both call paths without requiring MolmoSpaces/RBY1M local-dev
  execution.
- Generated reports continue to satisfy the canonical visual core through the
  existing checkers.

## Verification

- `uv run ruff check scripts/run_molmo_agent_bridge_smoke.py scripts/run_molmo_realworld_agent_mcp_smoke.py tests/test_molmo_mcp_smoke_shared_semantic_loop.py`
- `uv run ruff format --check scripts/run_molmo_agent_bridge_smoke.py scripts/run_molmo_realworld_agent_mcp_smoke.py tests/test_molmo_mcp_smoke_shared_semantic_loop.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_mcp_smoke_shared_semantic_loop.py tests/test_molmo_semantic_cleanup_loop.py tests/test_verify_just_recipes.py`

## Risks

- The shared loop's request shape must remain compatible with both MCP
  contracts. Current-contract uses `receptacle_id` and `object_done`; ADR-0003
  uses public `fixture_id` target requests and does not expose `object_done`.
