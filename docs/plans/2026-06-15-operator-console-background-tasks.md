# Operator Console Background Tasks

**Status:** Implemented
**Created:** 2026-06-15
**Last reviewed:** 2026-06-15
**Current implementation contract:** Add an operator-console Background Tasks page backed by a shared runtime inventory API, and reuse that inventory to explain launch blockers before a route fails.
**Related ADRs:** None

## Goal

Make live local resource ownership visible before launch. The operator should
see when a Codex, Claude, OpenAI Agents SDK, eval-harness, tmux, MCP server,
visual-backend slot, or coding-agent Docker task is already occupying the
backend resources needed by a route.

The immediate failure this plan prevents is a launch that reports only
`another interactive Codex Molmo cleanup session appears to be active` after
Start, while the UI had no visible indication that an eval-harness live row was
still running.

## Architecture Layer

This belongs to **Thin Runtime / Server Adapters** and the local
`operator_console` launch-control surface. It is lifecycle, readiness, lock,
port, run-directory, and live-status plumbing. It must not add cleanup strategy,
prompt policy, private scoring truth, or task-specific robot behavior.

## Decisions From Grill

1. Use a dedicated user-facing **Background Tasks** page, plus a compact
   resource-occupied summary near Start.
2. Inventory all repo-relevant live resources, not only runs launched by the
   operator console.
3. Provide direct Stop controls only for operator-console-managed runs in the
   first slice. For external/eval/tmux tasks, show attach, tail, artifact, and
   copyable stop/cleanup commands.
4. Fix eval-harness detached live-row semantics so a detached launch is not
   reported as `passed` until polling proves a terminal successful result.
5. Reuse the same runtime inventory in route readiness. Do not maintain a
   separate UI-only task page and launch-blocker logic.
6. Use **Background Tasks** in the UI and `runtime_inventory` internally.
   Avoid using bare "Runtime" as the main label because the repo already uses
   runtime for backend runtimes, provider runtime, and Runtime Metric Map.

## Scope

- Add `roboclaws/operator_console/runtime_inventory.py`.
- Add `GET /api/runtime/tasks` to the operator-console server.
- Add a Background Tasks view/tab in the operator console.
- Add a compact launch-panel summary for resources that block the selected
  route.
- Enrich route readiness with the resource owner when a backend lock, visual
  slot, tmux session, or MCP port blocks launch.
- Update eval-harness detached live-product rows so "launched detached" is not
  recorded as final pass without terminal artifact polling.
- Add focused tests for inventory detection, readiness enrichment, and detached
  eval row state.

## Inventory Sources

The inventory should read current local state from bounded, redacted sources:

- `output/operator-console/locks/*.json`
- `output/operator-console/runs/*/operator_state.json`
- nested live artifacts such as `live_status.json`, `tmux_session.txt`,
  `server.pid`, `driver.log`, and agent event logs
- `output/molmo/visual-backend-slots/*.json`
- tmux sessions matching repo-owned live names such as `roboclaws-molmo-*`
- TCP owner evidence for MCP ports used by catalog routes, especially `18788`
- coding-agent Docker containers with repo run-dir or workspace mounts
- selected `output/eval-harness/*/rows/*` live rows and detached row logs

The API must not expose provider keys or raw process environments. Process
commands should be summarized or redacted before returning to the browser.

## Task Row Shape

Each Background Tasks row should include:

- status: running, launched, blocked, terminal, stale, or unknown
- owner: operator-console, eval-harness, molmo-live, manual-tmux, docker, or port-owner
- route or row id when known
- resource: backend lock, visual slot, MCP port, tmux session, Docker container
- PID/container/session id
- age and started-at timestamp when known
- run directory and display directory when known
- artifact links: driver log, report, trace, status JSON, eval harness report
- safe actions: attach tmux, tail log, open artifacts, copy stop command
- direct Stop only when the owner is an operator-console-managed run

## Expected UI Behavior

### Launch Panel

- If the selected route is blocked by a known task, show a concise owner
  summary near Start:
  `Background task <id> is using MCP port 18788 and Molmo visual slot 1.`
- Provide a link/button to open the Background Tasks page filtered to that
  owner or resource.
- Keep existing route cards and launch axes focused on selecting a route, not
  listing every task inline.

### Background Tasks Page

- Show active repo-relevant tasks that can affect operator-console/UI E2E
  startup: backend locks, MCP ports, Molmo visual slots, repo-owned tmux
  sessions, and repo-mounted Docker containers.
- Do not make operators filter through terminal, stale, unknown, or unrelated
  history in the default UI. Keep the full inventory as an internal readiness
  and debugging source.
- Prefer operator actions that preserve evidence: attach, tail, open artifacts,
  copy stop command.
- Make stale ownership explicit when a lock/slot exists but the PID is gone.

## Non-Goals

- Do not build a general host process manager.
- Do not expose secrets, raw env vars, private scoring truth, or raw provider
  logs.
- Do not let the UI kill arbitrary tmux sessions or Docker containers in the
  first slice.
- Do not change public launch axes, surfaces, presets, or evidence-lane names.
- Do not add robot cleanup/search/map-build strategy to operator-console code.

## Acceptance Criteria

- A live eval-harness Codex Molmo cleanup row appears in Background Tasks while
  its tmux session, MCP port, visual slot, or Docker container is active.
- The selected Molmo/Codex cleanup route shows the blocking owner before Start
  when the MCP port, visual slot, or matching tmux session is active.
- Operator-console-owned active runs still support direct Stop from the UI.
- External/eval/tmux-owned tasks expose attach/tail/artifact/copy-command
  actions but no direct destructive stop button.
- `mcp_port_free` readiness includes owner/resource evidence when the port
  owner can be identified.
- Detached eval-harness live product rows are not marked final `passed` merely
  because a tmux session was launched.
- Redaction tests prove provider keys and raw process env are not returned from
  the runtime inventory API.

## Suggested Verification

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console tests/unit/evals
./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py
.venv/bin/ruff check roboclaws/operator_console skills/eval-harness/scripts tests/unit/operator_console tests/unit/evals tests/contract/dev_tools/test_task_agent_just_recipes.py
```

Manual smoke:

```bash
just console::run
```

Then start or simulate a detached Molmo/Codex run and verify the Background
Tasks page and selected route readiness name the owner before Start.

## Shipped Evidence

Implemented on 2026-06-15 in the local checkout.

- Added `roboclaws/operator_console/runtime_inventory.py` and
  `GET /api/runtime/tasks`.
- Added a Background Tasks workspace view scoped to resources that can block
  console/UI E2E startup, with artifact links, copyable attach/tail/stop
  commands, and direct Stop only for active operator-console-owned runs.
- Reused the runtime inventory in route readiness so selected Molmo/Codex
  cleanup routes name eval-harness/tmux/slot/port owners before launch.
- Updated eval-harness direct detached live-product rows so launch success is
  not final `passed` until `run_result.json` appears.
- Fixed active-run state derivation so artifact-only active runs are not
  mislabeled as failed wrapper launches.

Verification:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console tests/unit/evals
./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py
.venv/bin/ruff check roboclaws/operator_console skills/eval-harness/scripts tests/unit/operator_console tests/unit/evals tests/contract/dev_tools/test_task_agent_just_recipes.py
```

Manual smoke:

- `just console::run` was blocked because local port `8765` was already in use.
- Ran `python -m roboclaws.operator_console --host 127.0.0.1 --port 8766`.
- Queried `/api/runtime/tasks?port=18788` and confirmed the active
  `eval-row:codex-cleanup-camera-raw-fpv-live-product` row was listed with
  tmux, MCP port `18788`, server PID, visual slot 1, artifacts, and safe
  attach/tail/copy actions.
- Queried `/api/readiness` for the Molmo/Codex cleanup route and confirmed
  `blocker_kind=background_task` named that eval-harness owner before launch.

## Remaining Work

- Browser visual QA of the Background Tasks page on desktop/mobile is still a
  useful follow-up if layout polish is needed.
- The first slice intentionally does not add destructive UI stop controls for
  external tmux, Docker, or eval-harness-owned tasks.

## Next Step

Use the Background Tasks page/API for future local launch debugging. Browser
visual QA can be run as a polish follow-up.

## Open Questions

None after grill. Remaining choices are implementation defaults unless preflight
finds an execution-risk boundary.

## Intuitive Preflight Result

Preflight status: DRAFT

Task source: `docs/plans/2026-06-15-operator-console-background-tasks.md`

Canonical source:
`docs/plans/2026-06-15-operator-console-background-tasks.md`

Route: durable `$intuitive-flow`

Goal: implement a Background Tasks page and shared runtime inventory so the
operator console can show live resource owners before launch, including
eval-harness detached Molmo/Codex sessions.

Scope:

- Add `roboclaws/operator_console/runtime_inventory.py` to normalize
  operator-console runs, locks, Molmo visual slots, tmux sessions, MCP port
  owners, coding-agent Docker containers, and selected eval-harness live rows.
- Add `GET /api/runtime/tasks` and a Background Tasks UI view with filtering,
  artifact links, attach/tail/copy actions, and direct Stop only for
  operator-console-owned runs.
- Enrich selected-route readiness and launch-panel messaging with the blocking
  task/resource owner from the runtime inventory.
- Fix eval-harness detached live-product row state so launch success is not
  recorded as terminal `passed` without polling evidence.
- Add focused tests for inventory detection, readiness owner evidence, UI/API
  redaction, safe action exposure, and detached eval row semantics.

Non-goals:

- No general host process manager.
- No arbitrary UI kill button for tmux sessions, Docker containers, or
  eval-harness rows not owned by the operator console.
- No public launch-axis, surface, preset, evidence-lane, MCP-tool, or cleanup
  behavior changes.
- No private scoring truth, raw provider logs, provider keys, or raw process
  environment exposure.
- No live provider/model behavior tuning.

Context:

- must-read: this plan, `ARCHITECTURE.md` Thin Runtime / Server Adapters,
  `README.md` Agent operator console row, `just/README.md` Live Agent Launch
  Behavior, `roboclaws/operator_console/launcher.py`,
  `roboclaws/operator_console/readiness.py`,
  `roboclaws/operator_console/server.py`,
  `roboclaws/operator_console/state.py`,
  `roboclaws/operator_console/locks.py`,
  `roboclaws/operator_console/static/index.html`,
  `roboclaws/operator_console/static/app.js`,
  `roboclaws/operator_console/static/styles.css`,
  `skills/eval-harness/scripts/run_eval_harness.py`, and `just/molmo.just`.
- useful: the failure artifact
  `output/operator-console/runs/20260615-152322-molmospaces-val_2-mujoco-cleanup-codex-cli-world-oracle-labels/console-launch.log`,
  the active detached row under
  `output/eval-harness/20260615_focused_live_after_fix/rows/codex-cleanup-camera-raw-fpv-live-product/`,
  `tests/unit/operator_console/`, `tests/unit/evals/test_eval_harness_selector.py`,
  and `tests/contract/dev_tools/test_task_agent_just_recipes.py`.
- avoid-unless-needed: full `output/` scans, historical retrospectives,
  private scorer artifacts, raw provider logs, and broad docs/plans unrelated
  to operator-console readiness.

Acceptance:

- SUCCESS: Background Tasks lists an eval-harness Codex Molmo cleanup row while
  its tmux session, MCP port, visual slot, or Docker container is active; the
  selected Molmo/Codex cleanup route names that owner before Start; Stop is
  direct only for operator-console-owned runs; eval-harness detached live rows
  no longer claim final `passed` solely on launch.
- BLOCKED_NEEDS_DECISION: none expected.
- BLOCKED_NEEDS_LOCAL_VALIDATION: required browser/manual console smoke if it
  cannot be run in the execution environment; required Docker/tmux/local process
  proof if the inventory cannot be exercised with fixtures alone.
- INTERMEDIATE_ONLY: acceptable only if the deterministic inventory/API tests
  pass but manual UI/Docker/tmux proof remains pending and is explicitly
  reported.
- No regressions: existing route selection, provider readiness, MCP port gate,
  backend lock attach-to-existing behavior, operator-console Stop behavior, and
  eval-harness environment-blocked classification remain intact.

Verification:

- deterministic: `./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console tests/unit/evals`
- integration: `./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py`
- static: `.venv/bin/ruff check roboclaws/operator_console skills/eval-harness/scripts tests/unit/operator_console tests/unit/evals tests/contract/dev_tools/test_task_agent_just_recipes.py`
- product-run: `just console::run`, then verify the Background Tasks view and
  selected-route readiness against either a fixture-backed simulated owner or a
  real detached Molmo/Codex run.
- local-live-manual: if Docker/tmux/provider/simulator are available, start or
  use a detached Molmo/Codex run and confirm the UI identifies the owner before
  launching another conflicting route. If unavailable, completion status must
  be `BLOCKED_NEEDS_LOCAL_VALIDATION` for the full product claim.
- optional: run `just agent::eval recommend plan=docs/plans/2026-06-15-operator-console-background-tasks.md budget=focused` after implementation to check whether the eval harness recommends more gates.

Execution: main=root supervisor owns scope, test selection, and final
complete/blocked judgment; worker=none by default unless `$intuitive-flow`
chooses an implementation worker; worker-goal=none.

To execute:

```text
/goal execute docs/plans/2026-06-15-operator-console-background-tasks.md with intuitive-flow
```

Optional tracking: none

Approval: LGTM/approve/go ahead approves; edits request revision.
