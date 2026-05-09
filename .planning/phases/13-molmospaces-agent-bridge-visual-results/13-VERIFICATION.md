# Phase 13 Verification - MolmoSpaces Agent Bridge Visual Results

Verified on 2026-05-08 in the local workstation session.

## Prompt-To-Artifact Checklist

| Requirement | Evidence |
| --- | --- |
| Agent bridge reports include images like the visual harness | `MolmoCleanupMCPServer` records `robot_view_steps`; visual artifacts include `before.png`, `after.png`, `robot_views/`, `run_result.json`, and `report.html`. |
| Reports include semantic mid phases | `report.html` contains `Robot View Timeline`; checker requires focused robot-view rows for navigation, pick, place, fridge open/place-inside, and verification. |
| Codex visual run | `output/molmo-agent-bridge-visual-codex/run_result.json`, checker passed with `--require-agent-driven --require-robot-views`. |
| Claude visual run | `output/molmo-agent-bridge-visual-claude/run_result.json`, checker passed with `--require-agent-driven --require-robot-views`. |
| OpenClaw visual run | `output/molmo-agent-bridge-visual-openclaw/run_result.json`, checker passed with `--require-agent-driven --require-robot-views`; Gateway was removed afterward. |
| Public-rule comparison | `just harness::molmo-agent-bridge-visual` produced both `output/molmo-agent-bridge-visual-rule/` and `output/molmo-agent-bridge-visual-harness/`. |
| ADR-0003 boundary remains explicit | Reports and run results still label `contract=current_contract`, `policy_uses_private_truth=false`, and `mcp_server=molmo_cleanup`. |

## Gates

| Gate | Result | Evidence |
| --- | --- | --- |
| Focused tests | PASS | `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_mcp_server.py tests/test_molmo_cleanup_agent_server.py tests/test_check_molmo_agent_bridge_result.py tests/test_verify_just_recipes.py` -> `16 passed`. |
| Focused lint | PASS | `.venv/bin/ruff check ...` on changed Python/test files -> `All checks passed!`. |
| Focused format | PASS | `.venv/bin/ruff format --check ...` on changed Python/test files -> `8 files already formatted`. |
| Existing bridge verify | PASS | `just verify::molmo-agent-bridge` passed after visual support was added. |
| Visual bridge harness | PASS | `just harness::molmo-agent-bridge-visual` passed; checker accepted the visual smoke artifact against the visual rule result. |
| Visual bridge verify | PASS | `just verify::molmo-agent-bridge-visual` passed; its pytest slice reported `21 passed, 1 skipped`, then the real visual rule/smoke harness completed and checker accepted `output/molmo-agent-bridge-visual-harness/run_result.json`. |
| Codex direct visual dogfood | PASS WITH NOTE | `cleanup_status=success`, 4/5 restored, 25 timeline steps. Codex chose a reasonable bed for the pillow, but the private scorer expected a different bed. |
| Claude direct visual dogfood | PASS WITH NOTE | `cleanup_status=success`, 4/5 restored, 25 timeline steps. Claude chose dining table for the bowl; private scorer expected a different receptacle. |
| OpenClaw Gateway visual dogfood | PASS WITH NOTE | `cleanup_status=success`, 3/5 restored, 25 timeline steps. OpenClaw completed all five semantic loops; bowl and book missed private scorer truth. |
| Docker hygiene | PASS | `docker rm -f openclaw-gateway`; final `docker ps -a ...` -> `no stale gateway`. |

## Comparison Results

| Driver | Policy | Backend | Status | Restored | Robot View Steps | Notes |
| --- | --- | --- | --- | ---: | ---: | --- |
| Rule-based baseline | `public_heuristic` | `molmospaces_subprocess` | `success` | 5/5 | 25 | Private scorer baseline. |
| Contract smoke | `contract_smoke_agent` | `molmospaces_subprocess` | `success` | 5/5 | 25 | Cheap MCP smoke over first five public objects. |
| Codex | `codex_agent` | `molmospaces_subprocess` | `success` | 4/5 | 25 | Missed pillow private target. |
| Claude Code | `claude_code_agent` | `molmospaces_subprocess` | `success` | 4/5 | 25 | Missed bowl private target. |
| OpenClaw | `openclaw_agent` | `molmospaces_subprocess` | `success` | 3/5 | 25 | Missed bowl and book private targets. |

## Review Note

The Phase 13 fix addresses the original report-quality gap: direct-agent and
OpenClaw artifacts now show the same visual robot timeline and semantic
mid-phase evidence as `output/molmo-robot-visual-harness/report.html`.

The score differences are not hidden. They show the current-contract limitation:
agents can see public objects/receptacles and make plausible semantic choices,
but they do not see the private scorer target map. That is why the deterministic
rule baseline is 5/5 while public agent choices can be 3/5 or 4/5 and still be
valid evidence for visual bridge behavior.
