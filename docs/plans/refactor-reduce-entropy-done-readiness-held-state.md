---
refactor_scope: done-readiness-held-state
status: DONE
accepted_severities:
  - P1
last_verified: 2026-06-05
---

# Refactor Scope: Done Readiness Held State

## Status

DONE

## Target

`RealWorldCleanupContract` done-readiness blockers for pending cleanup
candidates.

## Accepted Severities

- P1: blocked `done` must return the correct public next tool when the agent is
  already holding a cleanup object.

## Accepted Cleanup Checklist

- [x] Preserve lifecycle `state` in non-sanitized pending-candidate payloads.
- [x] Return `required_tool: navigate_to_receptacle` for held pending
  candidates.
- [x] Cover the non-sanitized held-object path with a contract regression test.
- [x] Keep ADR-0134 public/private boundary assertions green.

## Parked Cross-Seam / Future Ideas

- None.

## Evidence Ladder

- L2 contract tests for `done` readiness blocker shape and public/private
  boundary.

## Verification

- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_realworld_contract_rejects_done_with_pending_public_candidates tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_world_labels_done_rejects_held_public_candidate_with_receptacle_hint tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_world_labels_sanitized_done_rejects_held_policy_required_object tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_world_labels_requested_run_size_does_not_enable_raw_fpv_grounded_chain_gate tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_camera_raw_requested_run_size_enables_grounded_chain_gate_after_sweep tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_world_labels_explicit_grounded_chain_gate_uses_world_label_tooling`
- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::test_realworld_mcp_raw_fpv_camera_raw_done_requires_complete_live_chains tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::test_realworld_mcp_world_labels_requested_run_size_does_not_use_raw_fpv_chain_gate tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::test_realworld_mcp_raw_fpv_camera_raw_done_allows_complete_live_chains`
- `ruff check roboclaws/household/realworld_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_contract.py`
- `git diff --check -- roboclaws/household/realworld_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_contract.py docs/plans/refactor-reduce-entropy-done-readiness-held-state.md`

## Stop Condition

Stop when the focused contract tests prove that held non-sanitized cleanup
candidates produce a blocked `done` response with `state: held` and
`required_tool: navigate_to_receptacle`, and the existing readiness tests still
pass.

## Execution Log

- 2026-06-05: Gate created for approved held-object readiness hint slice.
- 2026-06-05: Added non-sanitized held-object regression coverage and preserved
  pending-candidate `state` / `required_tool` in public done-readiness
  blockers. Verified with focused contract and MCP readiness tests plus Ruff.
