---
plan_scope: operator-console-agent-interaction
status: IMPLEMENTED_ASK_WHY_REMOVED
architecture_layer: Thin Runtime / Server Adapter
source:
  - 2026-06-09 operator-console steering discussion
  - 2026-06-15 Ask Why removal decision
  - intuitive-reduce-entropy
  - grill-with-docs-batch
  - intuitive-preflight
last_reviewed: 2026-06-15
---

# Operator Console Agent Interaction

## Current Contract

As of 2026-06-15, the operator console keeps the interaction model focused on
robot-run control:

- `Goal` starts an initial run when no run is attached.
- `Goal` starts a linked `Next Goal` run when the attached parent run is
  terminal.
- `Steer` is the only active-run operator-message path. It writes
  `operator_messages.jsonl` and reaches the agent through the MCP
  `check_operator_messages` checkpoint.
- Active runs do not queue a later goal in this slice. The active-run path is
  `Steer`.
- `Ask Why` has been removed from the active UI, API, state, artifact support,
  and tests. The former `/api/runs/<run_id>/ask-why` route and `ask_why`
  artifacts are not compatibility contracts.
- Operators inspect `report.html`, raw public artifacts, and external coding
  agent analysis when they need an explanation or debugging pass after a run.

The console remains a Thin Runtime / Server Adapter surface. It launches
catalog-approved runs, shows normalized state, links artifacts, and transports
operator steering. It does not own cleanup/search strategy, private scorer
truth, or an embedded explanation agent.

## Implementation Results

### Ask Why Removal

Implemented on 2026-06-15.

Shipped removal includes:

- Removed the visible `Ask Why` operator mode.
- Removed `POST /api/runs/<run_id>/ask-why` from the server route table.
- Removed `append_ask_why` and deterministic Ask Why artifact writing.
- Removed `ask_why_available` from derived operator state.
- Removed the UI branch, result formatting, and stale helper state for Ask Why.
- Updated active-run copy to direct operators to `Steer` only.
- Updated unit/static tests so Ask Why strings, routes, and helper names are
  forbidden in active console assets.

Current deterministic gate:

```bash
node --check roboclaws/operator_console/static/app.js
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console
./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py
ruff check roboclaws/operator_console tests/unit/operator_console tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py
```

### Next Goal Refactor

Implemented on 2026-06-09.

Shipped Next Goal refactor includes:

- Public follow-up terminology is `Next Goal`, not `Continue`.
- Public API/artifact naming uses:
  - `POST /api/runs/<run_id>/next-goal`
  - `next_goal_queue.jsonl`
  - `command_type="next_goal"`
  - `next_goal_packet`
- Public `/continue`, `continue_queue.jsonl`, and
  `command_type="continue"` compatibility paths were removed.
- Operator text input is in the left setup/input area through the unified
  `Operator Input` composer.
- The right side is reserved for run state, evidence, outputs, raw artifact
  inspection, and run controls.
- `Goal` mode starts an initial run when no run is attached and starts a linked
  `Next Goal` run after a terminal parent.
- Active-run `Goal`/Next Goal queueing is intentionally not exposed in this
  slice.
- Terminal failed, stopped, checker-failed, physical, real-movement, or
  emergency-stop-gated parents require explicit confirmation before Next Goal
  startup.
- Passed simulator parents may auto-start a linked child run with
  `operator_session_id`, `parent_run_id`, and public parent artifact
  references.
- Steer remains route-gated and delivered through `operator_messages.jsonl`
  plus MCP `check_operator_messages`.

Historical live acceptance evidence from 2026-06-09:

- Console route: `just console::run 127.0.0.1 8876`
- Parent run: `20260609-235202-codex-mujoco-cleanup`
- Parent report:
  `output/operator-console/runs/20260609-235202-codex-mujoco-cleanup/0609_2352/seed-7/report.html`
- Parent result:
  `output/operator-console/runs/20260609-235202-codex-mujoco-cleanup/0609_2352/seed-7/run_result.json`
- Steer message: `steer-09dcabe66c7c`, seen at `2026-06-09T15:52:43Z`
- Historical Ask Why message: `ask_why-d399ac67b220`, answered from public
  artifacts only. This is historical evidence for the superseded surface, not
  an active console contract.
- Next Goal message: `next_goal-96e0ba48dea8`, started child
  `20260610-000401-codex-mujoco-cleanup`

### V1 Interaction Slice

Implemented on 2026-06-09. The historical v1 record is kept only to explain
the source of the later refactors.

Shipped v1 included:

- Operator Session artifacts and session APIs.
- Explicit active-run steering APIs/UI.
- Linked follow-up run metadata with `operator_session_id`, `parent_run_id`,
  and public follow-up packets.
- Route-gated active-run steering through `operator_messages.jsonl` and the
  household MCP `check_operator_messages` tool.
- Ordinary MCP pending-message hints without exposing full message text.
- Simulator queued follow-up auto-start only after terminal parent evidence;
  physical, real-movement, and emergency-stop routes require confirmation.
- Focused deterministic tests and one local live Codex console proof.

The v1 Ask Why surface was intentionally removed on 2026-06-15.

## Interaction Model

### Goal

`Goal` is the operator-authored task text path.

- With no attached run, it starts a new Robot Run through the launch catalog.
- With a terminal attached parent run, it starts a linked `Next Goal` Robot Run.
- With an active attached run, it does not queue a later run. The UI directs the
  operator to `Steer`.

### Steer Current Run

`Steer Current Run` is a behavior-changing action for an active Robot Run. It
lets the operator provide hints, constraints, priorities, or corrective
instructions while the run is still active.

Steering is artifact-backed and agent-visible through a public MCP tool:

```text
console POST /api/runs/<run_id>/messages
  -> append operator_messages.jsonl
  -> active MCP server exposes check_operator_messages
  -> agent checks at safe checkpoints
  -> acknowledgement is written into trace/operator_messages.jsonl
```

Safe checkpoints are owned by the task skill and MCP contract. Initial default
checkpoints include after `metric_map`, after `observe`, before starting a new
cleanup object chain, and before `done`.

If a steer message is urgent enough that waiting for the next checkpoint is
unsafe, the operator should use Stop or Emergency Stop instead of Steer.

### Next Goal

`Next Goal` starts a new Robot Run linked to an Operator Session and optionally
a parent Robot Run. It is used when the previous run is terminal or when the
operator intentionally starts a new episode.

The new run receives a public Next Goal packet:

- `operator_session_id`
- `parent_run_id`
- new operator prompt
- public summary of the parent run
- public Runtime Metric Map or Actionable Semantic Map Snapshot when available
- artifact links for human review
- clear instruction that this is a follow-up episode, not mutation of the
  parent report

Failed, stopped, checker-failed, physical, real-movement, or emergency-stop
parents require explicit operator confirmation before Next Goal startup.

## Active API Shape

```text
POST /api/sessions
GET  /api/sessions/<session_id>

POST /api/runs
POST /api/runs/<run_id>/messages
GET  /api/runs/<run_id>/messages
POST /api/runs/<run_id>/next-goal
POST /api/runs/<run_id>/pause
POST /api/runs/<run_id>/stop
POST /api/runs/<run_id>/emergency-stop
```

`POST /api/runs/<run_id>/messages` is for active-run steering only.
`POST /api/runs/<run_id>/next-goal` creates a new linked run when the parent is
terminal. It may require operator confirmation when the parent failed, was
stopped, or when a physical/real-movement gate must be reconfirmed.

There is no active Ask Why endpoint.

## Decisions

1. Keep `done` terminal for a single Robot Run.
   `done` writes review artifacts, fixes the report/checker boundary, and
   prevents later robot tool calls from changing that run's evidence.

2. Do not inject operator text into `codex exec`, Claude print mode, tmux, or
   stdin. Stdin injection would not be a stable, auditable agent-control
   protocol.

3. Remove Ask Why instead of hiding it. The console's main job is run control;
   explanation/debugging should use report artifacts and an external coding
   agent when needed.

4. Treat post-`done` continuation as a linked follow-up run, not as mutation of
   the completed run.

5. Keep Private Evaluation out of agent-facing Next Goal context.
   Follow-up runs may use public Agent View, Runtime Metric Map, trace
   summaries, report links, and operator-authored notes. They must not use
   hidden mess membership, acceptable destination sets, private manifests, or
   scorer truth as agent input.

6. Allow active-run steering during long MCP runs.
   The agent receives hints the next time it checks the operator-message MCP
   surface at a safe checkpoint.

7. Require explicit operator input modes for new text. The active modes are
   `Goal` and `Steer`.

## Non-Goals

- Do not remove or weaken `done`.
- Do not make live Codex or Claude runners automatically continue after an
  unfinished run.
- Do not make the console a generic shell or arbitrary `just` executor.
- Do not expose Private Evaluation as agent input for Steer or Next Goal.
- Do not claim hidden model chain-of-thought visibility.
- Do not keep a dormant Ask Why route, artifact writer, or UI mode for
  compatibility.
- Do not implement physical manipulation steering for Agibot cleanup while
  physical cleanup manipulation remains a blocked capability.
- Do not require SDK runtime migration for Goal, Steer, or Next Goal.

## Acceptance Criteria

- `done` remains terminal for one Robot Run.
- A terminal Robot Run rejects Steer Current Run and offers Next Goal instead.
- Next Goal runs carry `operator_session_id` and `parent_run_id` metadata.
- Next Goal context excludes Private Evaluation and hidden scorer truth.
- Active-run Next Goal queueing is not part of this refactor.
- Active-run steering is stored in auditable artifacts and delivered through a
  public MCP tool, not stdin/tmux injection.
- The left input composer distinguishes `Goal` and `Steer`.
- The active UI/API/state/artifact/test surface contains no Ask Why support.
- Tests cover state transitions and artifact boundaries without live provider
  calls.

## Verification Contract

Deterministic checks for this surface:

```bash
node --check roboclaws/operator_console/static/app.js
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console
./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py
ruff check roboclaws/operator_console tests/unit/operator_console tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py
```

Focused checks cover:

- Post-`done` steer returns a clear terminal-run error.
- Active-run Next Goal tells the operator to use Steer.
- Next Goal creates a linked run with a parent run id.
- `operator_messages.jsonl` preserves ordering and redaction.
- MCP `check_operator_messages` marks messages as seen or rejected.
- Ordinary MCP responses expose only a pending steer hint when unread messages
  exist; message contents are retrieved through `check_operator_messages`.
- Failed, stopped, checker-failed, physical, or real-movement parents require
  explicit operator confirmation before Next Goal start.
- Static assets do not expose Ask Why controls, routes, or JS helper state.

Live Codex, live Claude, Isaac, Agibot, GPU, and physical-robot validation are
not required for the 2026-06-15 Ask Why removal because the change removes a
console-only interaction path and leaves the existing run/steer/next-goal
contracts covered by deterministic tests.

## Parked Follow-Ups

- Add richer steer lifecycle states such as `applied`, `rejected`, and
  `expired`; parked because current acceptance only needs durable queueing,
  pending hints, and MCP `seen` acknowledgement. Unpark when the task skill
  defines how agents should explicitly apply or reject operator instructions.
- Add a new explanation/debugging workflow only if operators need it after
  using reports and raw artifacts with external coding-agent inspection. That
  should be a new product-contract decision, not a dormant restoration of the
  removed Ask Why route.
