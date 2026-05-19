# Phase 12 Plan 01 Summary - Current-Contract Agent Bridge

Completed on 2026-05-08.

## What Changed

- Added `MolmoCleanupMCPServer`, a separate FastMCP server for the Molmo cleanup
  current contract.
- Added `examples/molmo_cleanup_agent_server.py` for direct Codex / Claude Code
  setup and OpenClaw Gateway wiring instructions.
- Added `skills/molmo-cleanup/SKILL.md` with the exact semantic cleanup loop and
  current-contract boundaries.
- Added a cheap MCP bridge smoke runner plus checker:
  `scripts/run_molmo_agent_bridge_smoke.py` and
  `scripts/check_molmo_agent_bridge_result.py`.
- Added `just harness::molmo-agent-bridge` and
  `just verify::molmo-agent-bridge`.
- Updated cleanup reports to label `contract`, `policy`, `agent_driven`, and
  `mcp_server`, with an explicit ADR-0003 boundary note.
- Hardened tool and skill instructions after OpenClaw tried one stale
  receptacle/simulator-style object id before recovering.

## Verification

See `12-VERIFICATION.md`.

Key final evidence:

- `just verify::molmo-agent-bridge` passed.
- Codex direct MCP: `output/molmo-agent-bridge-codex/run_result.json` ->
  `success`, 5/5 restored, 0 stale references.
- Claude Code direct MCP: `output/molmo-agent-bridge-claude/run_result.json` ->
  `success`, 5/5 restored, 0 stale references.
- OpenClaw Gateway: `output/molmo-agent-bridge-openclaw/run_result.json` ->
  `success`, 5/5 restored, useful trace, one recovered stale-reference attempt.
- Rule-based comparison: `output/molmo-agent-bridge-rule/run_result.json` ->
  `success`, 5/5 restored.

## Boundaries

- This bridge is `contract=current_contract`.
- Global `scene_objects` remains intentionally available.
- `policy_uses_private_truth=false` for agent bridge artifacts.
- This phase does not satisfy ADR-0003 and does not claim planner-backed robot
  manipulation.
