# 17-01 Real-World Agent Dogfood Summary

**Status:** Complete
**Completed:** 2026-05-09

## What Changed

- Added `skills/molmo-realworld-cleanup/SKILL.md`, a compact ADR-0003 agent
  skill that teaches Metric Map, Fixture Hints, waypoint observation, Observed
  Object Handles, and semantic cleanup tools without `scene_objects`.
- Added `examples/molmo_realworld_cleanup_agent_server.py`, a direct
  Codex/Claude/OpenClaw launcher for the `molmo_cleanup_realworld` MCP surface.
- Extended `scripts/check_molmo_realworld_cleanup_result.py` with
  `--require-agent-driven` and `--require-clean-agent-run`.
- Tightened trace validation so any real-world `scene_objects` tool event
  fails the checker.
- Added `just harness::molmo-realworld-agent-dogfood-kit` and
  `just verify::molmo-realworld-agent-dogfood-kit`.

## Evidence

- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_realworld_agent_server.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_verify_just_recipes.py tests/test_molmo_realworld_mcp_server.py`
  - Result: 16 passed.
- `.venv/bin/ruff check` on changed Python files
  - Result: passed.
- `.venv/bin/ruff format --check` on changed Python files
  - Result: passed.
- `just verify::molmo-realworld-agent-dogfood-kit`
  - Result: 16 focused tests passed, then the synthetic kit harness passed.
- `scripts/check_molmo_realworld_cleanup_result.py` with
  `--require-clean-agent-run --require-robot-views` against the Phase 16 real
  visual evidence
  - Result: passed.
- Claude Code direct synthetic dogfood
  - Result: checker passed for
    `output/molmo-realworld-agent-dogfood-claude-synth/run_result.json`.

## Direct Agent Result

`output/molmo-realworld-agent-dogfood-claude-synth/run_result.json`:

- `contract`: `realworld_cleanup_v1`
- `mcp_server`: `molmo_cleanup_realworld`
- `policy`: `claude_code_agent`
- `agent_driven`: true
- `adr_0003_satisfied`: true
- `cleanup_status`: `success`
- `mess_restoration_rate`: 1.0
- `sweep_coverage_rate`: 1.0
- `disturbance_count`: 0
- `generated_mess_count`: 5
- `semantic_substeps`: 5
- `scene_objects` trace entries: 0

## Codex Attempt

Codex was attempted twice against the same synthetic server shape. It listed MCP
tools but cancelled the first required `metric_map` call. The second attempt
also failed to read the skill under the read-only sandbox with:

```text
bwrap: loopback: Failed RTM_NEWADDR
```

Those attempts are recorded as blocked tooling behavior and are not counted as
successful dogfood evidence.

## Residual Follow-Ups

- OpenClaw Gateway dogfood against `molmo_cleanup_realworld`.
- Real MolmoSpaces/RBY1M visual direct-agent dogfood. The report shape is
  already validated through the Phase 16 real visual evidence, but the Phase 17
  successful external-agent run used the synthetic backend.
- Advisory scoring/model checks.
- Raw FPV-only perception.
- Planner-backed RBY1M/Franka manipulation.
