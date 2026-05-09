# 17-01 Real-World Agent Dogfood Plan

## Goal

Make direct coding-agent dogfood possible and checkable on the ADR-0003
`molmo_cleanup_realworld` MCP surface without reintroducing current-contract
shortcuts.

## Tasks

1. Add `skills/molmo-realworld-cleanup/SKILL.md` for external agents. The skill
   must teach the public ADR-0003 loop:
   `metric_map`, `fixture_hints`, `navigate_to_waypoint`, `observe`,
   `inspect_visible_object` as needed, then
   `navigate_to_object -> pick -> navigate_to_receptacle -> open? -> place`.
2. Add a direct server entrypoint for the real-world MCP surface that prints
   Codex, Claude Code, and OpenClaw setup commands plus the kickoff prompt.
3. Extend the real-world checker with clean agent-run assertions: expected
   policy, MCP server, agent-driven metadata, no private-truth flags, no
   `scene_objects` trace event, semantic substeps, ADR-0003 thresholds, and
   report sections.
4. Add `just harness::molmo-realworld-agent-dogfood-kit` and
   `just verify::molmo-realworld-agent-dogfood-kit` as focused gates for the
   skill, server entrypoint, checker, and synthetic dogfood artifact shape.
5. Attempt local direct coding-agent evidence if the installed tooling can run
   non-interactively. Record successful artifacts or the exact blocker in the
   verification document.

## Verification

- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_realworld_agent_server.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_verify_just_recipes.py`
- `ruff check` and `ruff format --check` on changed Python files.
- `just harness::molmo-realworld-agent-dogfood-kit`
- Optional local external-agent command if available:
  `codex exec ...` or `claude -p ...` against the direct server.

## Risks

- External agents may prematurely call `done` after partial sweep coverage.
  The checker must treat this as a failed clean run, not as a prompt issue.
- Tool descriptions could accidentally imply a global object list. The skill
  and tests should assert the `scene_objects` shortcut is absent from the
  real-world dogfood flow.
- Real visual dogfood is slow. The kit gate should remain synthetic, while
  real visual runs remain local evidence.
