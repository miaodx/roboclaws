# Agent and Task Command Taxonomy Plan

Status: implemented as `just/task.just` and `just/agent.just`.

This plan defines the human-facing command layers for robot/agent demos while
keeping the existing implementation modules available for lower-level debugging.

## Goal

Make command discovery follow what users care about:

- `task::*` names the outcome: navigate, photograph, compete, cover, cleanup,
  prove.
- `agent::*` names the driver: Codex, Claude Code, OpenClaw, direct VLM, or
  script.
- existing implementation modules keep their current ownership:
  `code::*`, `chat::*`, `openclaw::*`, `vlm::*`, `molmo::*`, `harness::*`,
  `verify::*`.

## Non-Goal

Do not move all recipe bodies into one large file. The lower-level files remain
the source of implementation detail for their subsystem.

## Dependency Rule

The command graph must be one-way:

```text
task::* -> agent::* or molmo::* or harness::* or verify::*
agent::* -> code::* or chat::* or openclaw::* or vlm::* or scripts/examples
verify::* -> harness::* or focused tests
harness::* -> scripts/examples
lower modules must not call task::*
lower modules must not call agent::* unless they are explicitly user-facing aliases
```

This avoids circular references. In particular:

- `task::*` may call `agent::*`.
- `agent::*` must not call `task::*`.
- `verify::*` should not depend on `task::*`; gates should stay strict and
  stable.
- `harness::*` should not depend on `task::*` or `agent::*`; harness recipes are
  implementation rigs.

## Proposed User Surface

`task::*` recipes:

- `task::navigate driver=codex|claude|openclaw`
- `task::photo-chairs driver=openclaw`
- `task::territory driver=vlm|openclaw|script`
- `task::coverage driver=vlm|openclaw|script`
- `task::control-ui driver=openclaw`
- `task::cleanup-quick-check`
- `task::cleanup-report driver=direct|mcp-smoke|openclaw-smoke|codex-live|claude-live|openclaw-live`
- `task::cleanup-raw-fpv`
- `task::planner-proof mode=dry-run|execute-rerun`

`agent::*` recipes:

- `agent::codex-nav`
- `agent::claude-nav`
- `agent::openclaw-nav`
- `agent::openclaw-photo`
- `agent::openclaw-territory`
- `agent::openclaw-coverage`
- `agent::openclaw-ui`
- `agent::vlm-territory`
- `agent::vlm-coverage`
- `agent::script-territory`
- `agent::script-coverage`

## Documentation Updates

- README should point normal users to `task::*`.
- Human docs should describe the layer model and when to drop down to
  `agent::*` or lower implementation modules.
- Existing lower-level docs can keep implementation recipes where useful.

## Verification

Add cheap command-surface tests that prove:

- `task` and `agent` modules are registered in the root `justfile`.
- `task::*` recipes delegate only downward.
- `agent::*` recipes delegate only downward.
- lower-level modules do not call `task::*`.
- no `task::* <-> agent::*` cycle exists.
- coding-agent launches still satisfy the existing full-permission guard.

No live Codex, Claude Code, OpenClaw Gateway, VLM API, or MolmoSpaces simulator
run is required for this command taxonomy refactor.

## Implementation Evidence

Completed on 2026-05-12:

- Added `just/task.just` and `just/agent.just`.
- Registered both modules in the root `justfile`.
- Updated README and human docs to point normal users at `task::*`.
- Added `tests/contract/dev_tools/test_task_agent_just_recipes.py`.

Verification run:

- `just --list task`
- `just --list agent`
- `just task::cleanup-quick-check`
- `just --dry-run task::navigate codex`
- `just --dry-run task::navigate claude`
- `just --dry-run task::territory openclaw`
- `just --dry-run task::control-ui openclaw kimi`
- `just --dry-run task::cleanup-report openclaw-live`
- `./scripts/run_pytest_standalone.sh -q tests/contract/dev_tools`
- `.venv/bin/ruff check tests/contract/dev_tools/test_task_agent_just_recipes.py`
- `.venv/bin/ruff format --check tests/contract/dev_tools/test_task_agent_just_recipes.py`
- `git diff --check`

Skipped by design:

- Live Codex / Claude Code / OpenClaw Gateway runs.
- Direct VLM API runs.
- Real MolmoSpaces subprocess visual reports.
