---
refactor_scope: mcp-skill-minimal-surface
status: DONE
accepted_severities:
  - P1
  - P2
last_verified: 2026-05-18
---

# Refactor Scope: MCP / Skill Minimal Surface

## Status

DONE

## Target

The repo-local MCP and skill surfaces for AI2-THOR navigation and MolmoSpaces
cleanup. The current profile contracts are canonical:

- `ai2thor_navigation_v1`: `observe`, `observe_archived`, `move`, `done`
- `molmospaces_cleanup_v1`: ADR-0003 public cleanup tools only

## Accepted Severities

- P1: active legacy/current-contract Molmo bridge surfaces that still expose
  `scene_objects` / `object_done` as first-class agent, recipe, test, or checker
  paths.
- P2: AI2-THOR MCP defaults that expose privileged `scene_objects` / `goto`
  unless callers explicitly opt into them.
- P2: compatibility aliases and docs wording that keep stale surfaces alive
  despite the repo's no-backward-compatibility posture.

## Accepted Cleanup Checklist

- [x] Retire `skills/molmo-cleanup` and legacy/current-contract Molmo MCP server
      entrypoints, scripts, checkers, tests, and Just verify/harness recipes.
- [x] Keep ADR-0003 Molmo cleanup as the only agent-facing Molmo MCP surface.
- [x] Change AI2-THOR MCP construction so the default surface is canonical-only;
      require explicit opt-in for demo/photo privileged helpers.
- [x] Move AI2-THOR privileged helper guidance out of the base navigator surface
      and into the photo/demo opt-in path.
- [x] Remove broad task/driver/profile compatibility aliases unless they are the
      canonical public spelling.
- [x] Update human docs so profile cleanup is forward-only, not additive/stable
      compatibility.
- [x] Remove follow-up current-code compatibility leftovers found after the
      origin/main delta grew: stale Molmo `agent_bridge` run-result naming,
      deprecated `--backend direct` game aliases, and unused report-page
      back-compat constants.

## Parked Cross-Seam / Future Ideas

- Broader Just module consolidation is outside this pass unless it is needed to
  remove accepted compatibility aliases.
- Historical ADR and plan files may still mention removed legacy paths as
  dated evidence. Do not rewrite that history unless a current entrypoint,
  human doc, test, or recipe depends on it.

## Evidence Ladder

- L0: `ruff check` / `ruff format --check` on changed Python and tests.
- L1/L2: focused contract tests for MCP profiles, AI2-THOR MCP registration,
  Molmo realworld MCP server, skill manifests, and command routing.
- L4-L6 skipped unless a changed path requires simulator, Gateway, VLM, or live
  coding-agent validation.

## Stop Condition

Stop when the accepted checklist is complete, focused L0-L2 checks pass, stale
legacy/current-contract bridge surfaces are gone or explicitly parked here, and
the work is committed in one or more coherent review units.

## Execution Log

- 2026-05-15: Created gate from the `$intuitive-flow` / `$intuitive-refactor`
  audit findings and accepted the P1/P2 cleanup set for implementation.
- 2026-05-15: Removed the legacy Molmo current-contract skill/server/demo
  bridge, bridge scripts, checkers, verify/harness recipes, and tests. Renamed
  the remaining backend shim to `CleanupBackendSession`.
- 2026-05-15: Made AI2-THOR MCP construction canonical-only by default and
  kept `scene_objects` / `goto` behind explicit privileged-helper opt-in for
  photo/demo launchers.
- 2026-05-15: Removed public task/driver/profile compatibility aliases from
  `task::run` and removed private compatibility wrappers from `just/task.just`.
- 2026-05-15: Updated human docs and report artifact routing so active docs,
  skills, commands, and report rerendering live at the current profile head.
- 2026-05-15: Evidence:
  `ROBOCLAWS_JUST_TRACE=1 just task::run molmo-cleanup codex smoke`;
  `ROBOCLAWS_JUST_TRACE=1 just task::run ai2thor-nav openclaw`;
  `ROBOCLAWS_JUST_TRACE=1 just task::run molmo-cleanup codex minimal` fails;
  `ROBOCLAWS_JUST_TRACE=1 just task::run molmospace-cleanup codex` fails;
  `just --summary`;
  `ruff check` / `ruff format --check` on existing changed Python;
  focused MCP/skill/Molmo/report/command contract tests;
  full `./scripts/dev/run_pytest_standalone.sh -q`.
- 2026-05-18: Reopened for one bounded entropy-reduction follow-up after the
  branch diverged significantly from `origin/main`. Scope is current-code
  compatibility leftovers only; historical ADR/plan references stay parked as
  dated evidence.
- 2026-05-18: Completed follow-up cleanup. Renamed current Molmo run-result
  diagnostics from `agent_bridge` to `agent_diagnostics`; removed the
  deprecated `--backend direct` alias from the territory/coverage example CLIs
  and tests; removed the unused `_OPENCLAW_ITEMS` back-compat constant from
  the Pages index generator. Evidence:
  `uv sync --extra dev`;
  `.venv/bin/python -c "import ai2thor; print(f'ai2thor {ai2thor.__version__} ok')"`;
  `.venv/bin/ruff check examples/games/territory_game.py examples/games/coverage_game.py roboclaws/molmo_cleanup/realworld_mcp_server.py scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py scripts/reports/write_pages_index.py tests/unit/examples/test_territory_example.py tests/unit/examples/test_coverage_example.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py tests/unit/molmo_cleanup/test_ci_live_reports.py`;
  `.venv/bin/ruff format --check examples/games/territory_game.py examples/games/coverage_game.py roboclaws/molmo_cleanup/realworld_mcp_server.py scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py scripts/reports/write_pages_index.py tests/unit/examples/test_territory_example.py tests/unit/examples/test_coverage_example.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py tests/unit/molmo_cleanup/test_ci_live_reports.py`;
  `./scripts/dev/run_pytest_standalone.sh -q tests/unit/examples/test_territory_example.py tests/unit/examples/test_coverage_example.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py tests/unit/molmo_cleanup/test_ci_live_reports.py`;
  stale current-surface search for `agent_bridge`, `--backend direct`, and
  `_OPENCLAW_ITEMS`.
