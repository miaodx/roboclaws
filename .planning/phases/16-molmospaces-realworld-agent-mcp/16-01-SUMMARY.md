# 16-01 Real-World Agent MCP Summary

**Status:** Complete
**Completed:** 2026-05-09

## What Changed

- Added `roboclaws/molmo_cleanup/realworld_mcp_server.py`, a separate FastMCP
  surface for the ADR-0003 `RealWorldCleanupContract`.
- Exposed only public real-world cleanup tools: `metric_map`, `fixture_hints`,
  waypoint navigation/observation, Observed Object Handles, semantic cleanup
  actions, and `done`.
- Explicitly rejected `scene_objects` on the real-world MCP surface so the
  historical current-contract shortcut cannot satisfy ADR-0003 by accident.
- Added `scripts/run_molmo_realworld_agent_mcp_smoke.py`, a deterministic MCP
  smoke policy that uses public tool responses only.
- Reused the shared cleanup report and semantic timeline underlay so the real
  report keeps Agent View, Private Evaluation, Score, Cleanup Trace, and Robot
  View Timeline sections.
- Extended checker/tests/just recipes for the new agent-driven real-world MCP
  artifact shape.

## Evidence

- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_realworld_mcp_server.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_verify_just_recipes.py`
  - Result: 12 passed.
- `.venv/bin/ruff check` on changed Python files
  - Result: passed.
- `.venv/bin/ruff format --check` on changed Python files
  - Result: passed.
- `just harness::molmo-realworld-agent-mcp "1" "output/molmo-realworld-agent-mcp-harness" "帮我收拾这个房间" "10"`
  - Result: checker passed for one real MolmoSpaces/RBY1M seed.

## Real Run Summary

`output/molmo-realworld-agent-mcp-harness/seed-1/run_result.json`:

- `contract`: `realworld_cleanup_v1`
- `mcp_server`: `molmo_cleanup_realworld`
- `policy`: `realworld_contract_smoke_agent`
- `agent_driven`: true
- `adr_0003_satisfied`: true
- `requested_generated_mess_count`: 10
- `generated_mess_count`: 10
- `cleanup_status`: `success`
- `completion_status`: `success`
- `mess_restoration_rate`: 0.8
- `sweep_coverage_rate`: 1.0
- `disturbance_count`: 0
- `semantic_substeps`: 10
- `robot_view_steps`: 44
- robot-view PNGs: 176

## Residual Follow-Ups

- Run direct Codex, Claude Code, and OpenClaw policy dogfood against the new
  ADR-0003 MCP surface.
- Add an advisory model/scorer layer only after the public MCP contract remains
  stable.
- Add raw FPV-only perception instead of semantic observe handles.
- Replace `api_semantic` MuJoCo state mutation with planner-backed
  RBY1M/Franka manipulation.
