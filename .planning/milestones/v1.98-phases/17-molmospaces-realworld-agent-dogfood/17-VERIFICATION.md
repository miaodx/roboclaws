# Phase 17 Verification

**Phase:** MolmoSpaces real-world agent dogfood
**Status:** Verified complete
**Date:** 2026-05-09

## Goal-Backward Check

Phase 17 needed to make direct coding-agent dogfood possible and checkable on
the ADR-0003 MCP surface. The implementation now provides a real-world cleanup
skill, direct agent server entrypoint, clean-run checker, recipes, and one
checker-validated direct Claude Code run on the strict public contract.

## Acceptance Criteria

| Criterion | Result |
| --- | --- |
| Direct entrypoint prints setup guidance for Codex, Claude Code, and OpenClaw using `molmo_cleanup_realworld`. | Passed. `tests/test_molmo_realworld_agent_server.py` covers setup text, MCP URL, skill path, contract, server name, backend, visual mode, and client commands. |
| Real-world skill instructs public ADR-0003 tool use and forbids `scene_objects`/private files. | Passed. `skills/molmo-realworld-cleanup/SKILL.md` defines the public loop and boundaries. |
| Checker enforces clean ADR-0003 agent run criteria. | Passed. Added `--require-agent-driven` and `--require-clean-agent-run`; tests cover successful smoke and rejection of `scene_objects` trace events. |
| `just harness::molmo-realworld-agent-dogfood-kit` proves the kit with the synthetic backend. | Passed. The harness produced `output/molmo-realworld-agent-dogfood-kit/run_result.json` and checker accepted it. |
| External-agent dogfood is attempted, with success or exact blocker recorded. | Passed. Claude Code produced a checker-validated clean run; Codex blocker is recorded separately. |
| Real visual report evidence retains Agent View, Private Evaluation, Score, Cleanup Trace/Semantic Substeps, and Robot View Timeline when robot-view capture is enabled. | Passed. The new checker accepted `output/molmo-realworld-agent-mcp-harness/seed-1/run_result.json` with `--require-clean-agent-run --require-robot-views`. |

## Commands Run

```bash
./scripts/run_pytest_standalone.sh -q \
  tests/test_molmo_realworld_agent_server.py \
  tests/test_check_molmo_realworld_cleanup_result.py \
  tests/test_verify_just_recipes.py \
  tests/test_molmo_realworld_mcp_server.py

.venv/bin/ruff check \
  examples/molmo_realworld_cleanup_agent_server.py \
  scripts/check_molmo_realworld_cleanup_result.py \
  tests/test_molmo_realworld_agent_server.py \
  tests/test_check_molmo_realworld_cleanup_result.py \
  tests/test_verify_just_recipes.py

.venv/bin/ruff format --check \
  examples/molmo_realworld_cleanup_agent_server.py \
  scripts/check_molmo_realworld_cleanup_result.py \
  tests/test_molmo_realworld_agent_server.py \
  tests/test_check_molmo_realworld_cleanup_result.py \
  tests/test_verify_just_recipes.py

just verify::molmo-realworld-agent-dogfood-kit

.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py \
  --expect-task "帮我收拾这个房间" \
  --expect-backend molmospaces_subprocess \
  --expect-policy realworld_contract_smoke_agent \
  --expect-mcp-server molmo_cleanup_realworld \
  --min-generated-mess-count 10 \
  --require-agent-driven \
  --require-clean-agent-run \
  --require-robot-views \
  output/molmo-realworld-agent-mcp-harness/seed-1/run_result.json

.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py \
  --expect-task "帮我收拾这个房间" \
  --expect-backend api_semantic_synthetic \
  --expect-policy claude_code_agent \
  --expect-mcp-server molmo_cleanup_realworld \
  --min-generated-mess-count 5 \
  --require-agent-driven \
  --require-clean-agent-run \
  output/molmo-realworld-agent-dogfood-claude-synth/run_result.json
```

## Direct Claude Evidence

`output/molmo-realworld-agent-dogfood-claude-synth/run_result.json`:

```json
{
  "backend": "api_semantic_synthetic",
  "seed": 7,
  "contract": "realworld_cleanup_v1",
  "mcp_server": "molmo_cleanup_realworld",
  "policy": "claude_code_agent",
  "agent_driven": true,
  "adr_0003_satisfied": true,
  "cleanup_status": "success",
  "completion_status": "success",
  "mess_restoration_rate": 1.0,
  "sweep_coverage_rate": 1.0,
  "disturbance_count": 0,
  "generated_mess_count": 5,
  "semantic_substeps": 5
}
```

Tool counts included `metric_map`, `fixture_hints`, `navigate_to_waypoint`,
`observe`, `navigate_to_object`, `pick`, `navigate_to_receptacle`, `place`,
`open_receptacle`, `place_inside`, and `done`. The trace had zero
`scene_objects` events.

## Codex Blocker

Command shape attempted:

```bash
codex exec --skip-git-repo-check --sandbox read-only --add-dir .. \
  -c approval_policy='never' \
  -C demo \
  --output-last-message ../output/molmo-realworld-agent-dogfood-codex-synth/codex-final.txt \
  "Read ../skills/molmo-realworld-cleanup/SKILL.md, then use only the roboclaws MCP tools ..."
```

Outcome:

- Codex listed MCP tools.
- No cleanup tool response was recorded in `trace.jsonl`.
- Codex reported the first `metric_map` call was cancelled.
- Codex also reported `bwrap: loopback: Failed RTM_NEWADDR` while trying to
  read the skill under the sandbox.

This does not count as a clean agent run.

## Residual Risk

The successful external-agent proof used the synthetic backend. The strict
checker was separately run against the Phase 16 real MolmoSpaces/RBY1M visual
artifact to verify the report surface, but a real visual Claude/Codex dogfood
run remains a follow-up because it is slow and would duplicate Phase 16's
deterministic real visual capture. OpenClaw Gateway dogfood is also left as a
separate phase.
