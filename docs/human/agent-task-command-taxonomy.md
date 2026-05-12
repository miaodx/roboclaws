# Agent and Task Command Taxonomy Plan

Status: implemented as `just/task.just`, `just/agent.just`, and
[`just/README.md`](../../just/README.md).

This plan defines the human-facing command layers for robot/agent demos while
keeping the existing implementation modules available for lower-level debugging.

## Goal

Make command discovery follow what users care about:

- `task::*` owns the small user grammar:
  `task::run <task> <driver> [report] [key=value ...]`.
- `agent::*` owns compact maintainer dispatchers: `run`, `verify`, `harness`,
  `mcp`, and `gateway`.
- Existing implementation modules keep their current ownership:
  `code::*`, `chat::*`, `openclaw::*`, `vlm::*`, `molmo::*`, `harness::*`,
  `verify::*`, but are hidden from completion.

## Non-Goal

Do not move all recipe bodies into one large file. The lower-level files remain
the source of implementation detail for their subsystem.

## Dependency Rule

The command graph must be one-way:

```text
task::* -> agent::* or molmo::* or harness::* or verify::*
agent::* -> code::* or chat::* or openclaw::* or vlm::* or molmo::* or scripts/examples
verify::* -> harness::* or focused tests
harness::* -> scripts/examples
lower modules must not call task::*
lower modules must not call agent::*
```

This avoids circular references. In particular:

- `task::*` may call `agent::*`.
- `agent::*` must not call `task::*`.
- `verify::*` should not depend on `task::*`; gates should stay strict and
  stable.
- `harness::*` should not depend on `task::*` or `agent::*`; harness recipes are
  implementation rigs.

## Implemented User Surface

`task::*` public recipe:

- `task::run <task> <driver> [report] [key=value ...]`

Tasks:

- `ai2thor-nav`
- `territory`
- `coverage`
- `photo-chairs`
- `molmo-cleanup`
- `molmo-planner-proof`

Drivers:

- `openclaw`
- `vlm`
- `codex`
- `claude`
- `script`
- `direct`
- `mcp-smoke`

Reports:

- `visual` by default.
- `minimal` for cheap semantic agent iteration.

`agent::*` public recipes:

- `agent::run`
- `agent::verify`
- `agent::harness`
- `agent::mcp`
- `agent::gateway`

## Documentation Updates

- README should point normal users to `task::*`.
- Human docs should describe the layer model and when to drop down to
  `agent::*` or lower implementation modules.
- Existing lower-level docs can keep implementation recipes where useful.

## Verification

Add cheap command-surface tests that prove:

- `task` and `agent` modules are registered in the root `justfile`.
- `just --summary` exposes only the small public facade.
- `task::run` routes prompt-derived commands to the expected lower modules.
- visual default and minimal override choose the expected cleanup report shape.
- lower-level modules do not call `task::*`.
- no `task::* <-> agent::*` cycle exists.
- coding-agent launches still satisfy the existing full-permission guard.

No live Codex, Claude Code, OpenClaw Gateway, VLM API, or MolmoSpaces simulator
run is required for this command taxonomy refactor.

## Implementation Evidence

Completed on 2026-05-12:

- Collapsed public task recipes into `task::run`.
- Collapsed public agent recipes into compact dispatchers.
- Marked implementation modules private in the root `justfile`.
- Added `just/README.md`.
- Updated README and human docs to point normal users at `task::run`.
- Updated `tests/contract/dev_tools/test_task_agent_just_recipes.py`.

Verification run:

- `just --summary`
- `ROBOCLAWS_JUST_TRACE=1 just task::run molmo-cleanup codex`
- `ROBOCLAWS_JUST_TRACE=1 just task::run molmo-cleanup codex minimal`
- `ROBOCLAWS_JUST_TRACE=1 just task::run ai2thor-nav openclaw`
- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools`
- `.venv/bin/ruff check tests/contract/dev_tools/test_task_agent_just_recipes.py`
- `.venv/bin/ruff format --check tests/contract/dev_tools/test_task_agent_just_recipes.py`
- `git diff --check`

Skipped by design:

- Live Codex / Claude Code / OpenClaw Gateway runs.
- Direct VLM API runs.
- Real MolmoSpaces subprocess visual reports.
