# Phase 12 Verification - MolmoSpaces Current-Contract Agent Bridge

Verified on 2026-05-08 in the local workstation session.

## Prompt-To-Artifact Checklist

| Requirement | Evidence |
| --- | --- |
| Implement `docs/retrospectives/plans/molmospaces-current-contract-agent-bridge.md` via hybrid pipeline | GSD execution artifact: `12-01-current-contract-agent-bridge-PLAN.md`; plan source updated to `Status: Implemented 2026-05-08`. |
| New Molmo-specific MCP server, separate from AI2-THOR MCP | `roboclaws/molmo_cleanup/mcp_server.py` defines `MolmoCleanupMCPServer` and `make_molmo_cleanup_mcp`; no subclassing of `roboclaws.mcp.server.RoboclawsMCPServer`. |
| Expose current cleanup tools over FastMCP | `tests/test_molmo_cleanup_mcp_server.py` covers `observe`, `scene_objects`, semantic substeps, and `done` finalization through `call_tool`; FastMCP registration is in `_register_tools`. |
| Direct MCP entrypoint prints setup for Codex and Claude Code | `tests/test_molmo_cleanup_agent_server.py` asserts Codex, Claude Code, OpenClaw URL, skill path, and `roboclaws__observe` appear in setup text. |
| `skills/molmo-cleanup/SKILL.md` exists and is used by dogfood prompts | Direct Codex and Claude prompts explicitly read `../skills/molmo-cleanup/SKILL.md`; OpenClaw bootstrap mounted `SKILLS_DIR=$PWD/skills/molmo-cleanup`. |
| Reports and `run_result.json` label `contract=current_contract` | Checker `_assert_common` enforces contract labels and report text; all bridge artifacts passed. |
| Agent artifacts distinguish policy, agent-driven status, private-truth use, MCP server, tool counts | `run_result.json` includes `policy`, `agent_driven`, `policy_uses_private_truth=false`, `mcp_server=molmo_cleanup`, `tool_event_counts`, and `agent_bridge`. |
| Codex can generate a reasonable result vs rule-based | `output/molmo-agent-bridge-codex/run_result.json`: `success`, 5/5 restored, 0 stale references; checker passed with `--compare-rule-result output/molmo-agent-bridge-rule/run_result.json`. |
| Claude Code can generate a reasonable result vs rule-based | `output/molmo-agent-bridge-claude/run_result.json`: `success`, 5/5 restored, 0 stale references; checker passed with the same rule comparison. |
| OpenClaw can generate a reasonable result vs rule-based | `output/molmo-agent-bridge-openclaw/run_result.json`: `success`, 5/5 restored, useful MCP trace; checker passed `--require-openclaw-minimum` and rule comparison. |
| Docs state this bridge does not satisfy ADR-0003 | Plan source and report note state global `scene_objects` remains available and `adr_0003_satisfied=false`. |

## Gates

| Gate | Result | Evidence |
| --- | --- | --- |
| Dependency preflight | PASS | `uv --version && uv pip install -e ".[dev,openclaw]"` completed; `.venv/bin/python -c "import ai2thor; ..."` -> `ai2thor 5.0.0 ok`. |
| Focused tests | PASS | `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_mcp_server.py tests/test_molmo_cleanup_agent_server.py tests/test_check_molmo_agent_bridge_result.py tests/test_molmo_cleanup_report.py tests/test_molmo_cleanup_mcp_contract.py tests/test_verify_just_recipes.py` -> `17 passed`. |
| Focused lint | PASS | `.venv/bin/ruff check ...` on changed Python/test files -> `All checks passed!`. |
| Focused format | PASS | `.venv/bin/ruff format --check ...` on changed Python/test files -> `10 files already formatted`. |
| Harness/verify recipe | PASS | `just verify::molmo-agent-bridge` -> tests passed and checker accepted `output/molmo-agent-bridge-harness/run_result.json`. |
| Legacy cleanup regression | PASS | `just verify::molmo-cleanup` -> `22 passed` and checker accepted `output/molmo-cleanup-harness/run_result.json`. |
| Codex direct dogfood | PASS | `codex exec ...` from `demo/` with MCP server at `127.0.0.1:18788`; final response reported 5/5 restored. Checker passed clean gate. |
| Claude Code direct dogfood | PASS | `claude -p --dangerously-skip-permissions ...` from `demo/`; final response reported 5/5 restored. Checker passed clean gate. |
| OpenClaw Gateway dogfood | PASS WITH NOTE | Gateway using `PROVIDER=mimo`, `SKILLS_DIR=skills/molmo-cleanup`, and `ROBOCLAWS_MCP_URL=http://host.docker.internal:18788/mcp` returned `terminated_by=done`; checker passed OpenClaw minimum and rule comparison. One stale-reference attempt was recovered before 5/5 success. |
| Docker hygiene | PASS | `docker rm -f openclaw-gateway` followed by `docker ps -a ...` -> `no stale gateway`. |

## Comparison Results

| Driver | Policy | Status | Restored | Stale refs | Object done |
| --- | --- | --- | ---: | ---: | ---: |
| Rule-based baseline | `public_heuristic` | `success` | 5/5 | n/a | n/a |
| Contract smoke | `contract_smoke_agent` | `success` | 5/5 | 0 | 5 |
| Codex | `codex_agent` | `success` | 5/5 | 0 | 5 |
| Claude Code | `claude_code_agent` | `success` | 5/5 | 0 | 5 |
| OpenClaw | `openclaw_agent` | `success` | 5/5 | 1 | 5 |

## OpenClaw Note

OpenClaw first attempted `navigate_to_object` with a sofa/simulator-style id,
received a `stale_reference`, then recovered and completed all five targets.
The skill and `observe` instruction were hardened afterward to state that
`object_id` values must come only from `scene_objects.objects[*].object_id`, and
receptacles are targets only.
