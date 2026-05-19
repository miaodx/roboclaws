---
refactor_scope: command-runner-architecture
status: DONE
accepted_severities:
  - P0
  - P1
last_verified: 2026-05-13
---

# Refactor Scope: Command Runner Architecture

## Status

DONE

## Target

The human-facing command runner seam around `just task::run`, especially the
boundary between discoverable Just recipes and route/default/compatibility
logic.

## Accepted Severities

- P0: none identified.
- P1: `task::run` routing is encoded as shell control flow, which makes route
  compatibility, defaults, aliases, and trace behavior harder to test as a
  single source of truth.
- P1: the Molmo cleanup mode transition left a public compatibility gap:
  `minimal` is still documented as cheap iteration language in user-facing
  guidance, while the current profile router only accepts `smoke`,
  `world-labels`, `camera-raw`, and `camera-labels`.

## Accepted P0/P1 Checklist

- [x] Add an importable Python command router for `task::run` normalization,
  compatibility validation, mode/profile resolution, and Just delegation.
- [x] Make `just/task.just` a thin wrapper over that router while preserving
  the public `just task::run <task> <driver> [mode] [key=value ...]` surface.
- [x] Preserve current Molmo cleanup profiles and add `minimal` as a
  backwards-compatible alias for the cheap `smoke` profile.
- [x] Update command-surface contract tests to assert the route table through
  the importable router and the Just facade.

## Parked P2 / Future Ideas

- Move `agent::run` route/default logic into the same Python command router.
- Generate `just/README.md` task/driver/profile tables from the Python route
  registry.
- Replace regex-based Just source checks with direct route-registry tests where
  possible.
- Revisit whether lower implementation modules should stay in Just or move to
  purpose-specific Python scripts.

## Evidence Ladder

- L0: `ruff check` and `ruff format --check` on changed Python/tests.
- L1/L2: focused command-surface contract tests under
  `tests/contract/dev_tools/`.
- L2: direct trace commands for representative public routes.
- L4-L6 skipped: no simulator, Gateway, VLM, or coding-agent live run is needed
  to prove this command-routing refactor.

## Stop Condition

Stop when `just --summary` still exposes only the public facade, representative
`ROBOCLAWS_JUST_TRACE=1 just task::run ...` commands route to the expected
lower module calls, the focused command-surface contract tests pass, and all
P2 ideas are recorded here instead of implemented by drift.

## Execution Log

- 2026-05-13: Created the refactor gate for the approved command-runner slice.
- 2026-05-13: Added `roboclaws.devtools.commands` as the importable
  `task::run` route resolver and reduced `just/task.just` to a thin launcher.
- 2026-05-13: Preserved Molmo cleanup profiles and added compatibility aliases:
  `minimal -> smoke`, `visual -> world-labels`.
- 2026-05-13: Evidence passed:
  - `uv sync --extra dev`
  - `just --summary`
  - `ROBOCLAWS_JUST_TRACE=1 just task::run molmo-cleanup codex minimal`
  - `ROBOCLAWS_JUST_TRACE=1 just task::run molmo-cleanup codex world-labels`
  - `ROBOCLAWS_JUST_TRACE=1 just task::run ai2thor-nav openclaw`
  - `./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools`
  - `.venv/bin/ruff check roboclaws/devtools tests/contract/dev_tools/test_task_agent_just_recipes.py`
  - `.venv/bin/ruff format --check roboclaws/devtools tests/contract/dev_tools/test_task_agent_just_recipes.py`
  - `git diff --check`
- 2026-05-13: L4-L6 local simulator/Gateway/provider gates skipped because this
  refactor only changes command routing and trace contracts.
