# 20-01 Summary: Real-World OpenClaw Clean Policy

## Outcome

Phase 20 is complete for the contract hardening slice. The ADR-0003
`molmo_cleanup_realworld` MCP surface now enforces the public semantic cleanup
loop instead of silently auto-repairing skipped phases through backend
navigation.

The strict loop is:

```text
navigate_to_object -> pick -> navigate_to_receptacle -> open_receptacle? -> place/place_inside
```

Skipped semantic phases now return `ok=false`,
`error_reason=semantic_order`, `required_tool`, and a public recovery hint. The
payload does not include Generated Mess Set data, target counts, acceptable
destination sets, or private scorer truth.

## Code Changes

- `RealWorldCleanupContract.pick()` rejects calls before
  `navigate_to_object(object_id)`.
- `RealWorldCleanupContract.navigate_to_receptacle()` requires a held object.
- `open_receptacle()` requires navigation to the fixture with the held object.
- `place()` and `place_inside()` require matching
  `navigate_to_receptacle(fixture_id)`.
- Fridge-like `place_inside()` requires `open_receptacle(fixture_id)` first.
- `semantic_diagnostics()` now records `semantic_order_errors`.
- `scripts/check_molmo_realworld_cleanup_result.py --require-clean-agent-run`
  rejects nonzero semantic-order errors.
- `skills/molmo-realworld-cleanup/SKILL.md` and the server kickoff text now
  tell agents the server rejects skipped semantic phases.

## Evidence

- Focused tests passed:
  `tests/test_molmo_realworld_contract.py`,
  `tests/test_molmo_realworld_mcp_server.py`, and
  `tests/test_check_molmo_realworld_cleanup_result.py`.
- `just verify::molmo-realworld-agent-dogfood-kit` passed with
  `semantic_order_errors=0`, `complete_semantic_substep_objects=5`, and
  `cleanup_status=success`.
- `just verify::molmo-realworld-openclaw-dogfood-kit` passed with
  `policy=openclaw_agent`, `semantic_order_errors=0`, and
  `cleanup_status=success`.
- The existing real visual OpenClaw artifact at
  `output/molmo-realworld-openclaw-visual-dogfood-kit/run_result.json` still
  passes the strict clean visual checker.

## Remaining Follow-Up

This phase did not rerun a live OpenClaw Gateway model after the contract
hardening. The next live Gateway attempt should now fail visibly on skipped
semantic phases or recover by following `required_tool`. Broader remaining
MolmoSpaces follow-ups are advisory scoring/model checks, raw FPV-only
perception, and planner-backed manipulation.
