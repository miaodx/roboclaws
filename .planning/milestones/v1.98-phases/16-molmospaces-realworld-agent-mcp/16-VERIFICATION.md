# Phase 16 Verification

**Phase:** MolmoSpaces real-world agent MCP
**Status:** Verified complete
**Date:** 2026-05-09

## Goal-Backward Check

Phase 16 needed to close the gap where ADR-0003 had a real-world public/private
cleanup contract, but no agent-facing MCP surface. The implementation now gives
agents a separate `molmo_cleanup_realworld` MCP contract backed by
`RealWorldCleanupContract`, while keeping the current-contract `scene_objects`
shortcut out of that surface.

## Acceptance Criteria

| Criterion | Result |
| --- | --- |
| `observe` exposes visible detections and Observed Object Handles only after waypoint observation. | Passed. The smoke agent collected 10 public `observed_*` handles through `navigate_to_waypoint` and `observe`. |
| Real-world MCP does not register or accept `scene_objects`. | Passed. Focused tests assert rejection and the real trace has no `scene_objects` entries. |
| Trace contains `metric_map`, `fixture_hints`, `observe`, and semantic cleanup tools. | Passed. Real trace counts include all required public MCP tools and semantic actions. |
| `run_result.json` records ADR-0003 agent-driven metadata. | Passed. Real evidence records `contract=realworld_cleanup_v1`, `mcp_server=molmo_cleanup_realworld`, `agent_driven=true`, `adr_0003_satisfied=true`, and `policy_uses_private_truth=false`. |
| Checker validates `--expect-policy realworld_contract_smoke_agent`. | Passed. The real harness recipe invokes the checker with the expected policy and MCP server. |
| Real visual report includes Agent View, Private Evaluation, Score, Cleanup Trace, and Robot View Timeline. | Passed. Real seed 1 report includes those sections and 176 robot-view PNGs. |

## Commands Run

```bash
./scripts/run_pytest_standalone.sh -q \
  tests/test_molmo_realworld_mcp_server.py \
  tests/test_check_molmo_realworld_cleanup_result.py \
  tests/test_verify_just_recipes.py

.venv/bin/ruff check \
  roboclaws/molmo_cleanup/realworld_mcp_server.py \
  scripts/run_molmo_realworld_agent_mcp_smoke.py \
  scripts/check_molmo_realworld_cleanup_result.py \
  tests/test_molmo_realworld_mcp_server.py \
  tests/test_check_molmo_realworld_cleanup_result.py \
  tests/test_verify_just_recipes.py

.venv/bin/ruff format --check \
  roboclaws/molmo_cleanup/realworld_mcp_server.py \
  scripts/run_molmo_realworld_agent_mcp_smoke.py \
  scripts/check_molmo_realworld_cleanup_result.py \
  tests/test_molmo_realworld_mcp_server.py \
  tests/test_check_molmo_realworld_cleanup_result.py \
  tests/test_verify_just_recipes.py

just harness::molmo-realworld-agent-mcp \
  "1" \
  "output/molmo-realworld-agent-mcp-harness" \
  "帮我收拾这个房间" \
  "10"
```

## Real Evidence

`output/molmo-realworld-agent-mcp-harness/seed-1/run_result.json`:

```json
{
  "backend": "molmospaces_subprocess",
  "seed": 1,
  "requested_generated_mess_count": 10,
  "generated_mess_count": 10,
  "contract": "realworld_cleanup_v1",
  "mcp_server": "molmo_cleanup_realworld",
  "policy": "realworld_contract_smoke_agent",
  "agent_driven": true,
  "adr_0003_satisfied": true,
  "cleanup_status": "success",
  "completion_status": "success",
  "mess_restoration_rate": 0.8,
  "sweep_coverage_rate": 1.0,
  "disturbance_count": 0,
  "semantic_substeps": 10,
  "robot_view_steps": 44
}
```

Robot-view artifact count:

```text
176 PNGs under output/molmo-realworld-agent-mcp-harness/seed-1/robot_views
```

## Residual Risk

This phase proves the ADR-0003 MCP surface with a deterministic smoke policy,
not direct Codex/Claude/OpenClaw autonomy. Primitive execution is still
`api_semantic` MuJoCo state mutation, so planner-backed RBY1M/Franka
manipulation remains future work.
