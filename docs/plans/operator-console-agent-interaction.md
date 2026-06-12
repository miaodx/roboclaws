---
plan_scope: operator-console-agent-interaction
status: IMPLEMENTED_NEXT_GOAL
source:
  - 2026-06-09 operator-console steering discussion
  - intuitive-reduce-entropy
  - grill-with-docs-batch
  - intuitive-preflight
last_reviewed: 2026-06-09
---

# Operator Console Agent Interaction

## Implementation Results

### V1 Interaction Slice

Implemented on 2026-06-09. Superseded public `Continue` terminology was later
renamed to `Next Goal`; the historical v1 record is kept only to explain the
source of the refactor.

Shipped v1 includes:

- Operator Session artifacts and session APIs.
- deterministic Ask Why over public run artifacts.
- explicit Steer Current Run and follow-up run APIs/UI modes.
- linked follow-up run metadata with `operator_session_id`, `parent_run_id`,
  and public follow-up packets.
- route-gated active-run steering through `operator_messages.jsonl` and the
  household MCP `check_operator_messages` tool.
- ordinary MCP pending-message hints without exposing full message text.
- simulator queued follow-up auto-start only after terminal parent evidence;
  physical, real-movement, and emergency-stop routes require confirmation.
- focused deterministic tests and one local live Codex console proof.

Verification evidence:

```bash
.venv/bin/ruff check roboclaws/operator_console roboclaws/household roboclaws/cli/household_agent_server.py roboclaws/mcp/profiles.py tests/unit/operator_console tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/contract/dev_tools/test_task_agent_just_recipes.py
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/contract/dev_tools/test_task_agent_just_recipes.py::test_household_cleanup_route_passes_operator_messages_path_override tests/contract/dev_tools/test_task_agent_just_recipes.py::test_semantic_map_build_codex_live_passes_task_identity_to_server_and_checker
```

Live acceptance evidence:

- Console route: `just console::run 127.0.0.1 8876`
- Run id: `20260609-134702-codex-mujoco-cleanup`
- Report:
  `output/operator-console/runs/20260609-134702-codex-mujoco-cleanup/0609_1347/seed-7/report.html`
- Result:
  `output/operator-console/runs/20260609-134702-codex-mujoco-cleanup/0609_1347/seed-7/run_result.json`
- Checker: passed with exit status 0.
- Operator message:
  `steer-6e4bfca03853` moved from `queued` to `seen` at
  `2026-06-09T05:47:36Z` after Codex read it through
  `check_operator_messages`.

### Next Goal Refactor

Implemented on 2026-06-09 and locally live-validated on
2026-06-09T15:52Z through 2026-06-09T16:04Z.

Shipped Next Goal refactor includes:

- Public follow-up terminology is now `Next Goal`, not `Continue`.
- Public API/artifact naming uses:
  - `POST /api/runs/<run_id>/next-goal`
  - `next_goal_queue.jsonl`
  - `command_type="next_goal"`
  - `next_goal_packet`
  - `next_goal_*` route/state fields where follow-up state is exposed.
- Public `/continue`, `continue_queue.jsonl`, and
  `command_type="continue"` compatibility paths were removed.
- All operator text input is in the left setup/input area through one
  `Operator Input` composer with explicit `Goal`, `Steer`, and `Ask Why`
  modes.
- The right side is reserved for run state, evidence, outputs, raw artifact
  inspection, and run controls.
- `Goal` mode starts an initial run when no run is attached and starts a linked
  `Next Goal` run after a terminal parent.
- Active-run `Goal`/Next Goal queueing is intentionally not exposed in this
  slice; active runs direct the operator to `Steer` or `Ask Why`.
- Terminal failed, stopped, checker-failed, physical, real-movement, or
  emergency-stop-gated parents require explicit confirmation before Next Goal
  startup.
- Passed simulator parents may auto-start a linked child run with
  `operator_session_id`, `parent_run_id`, and public parent-context artifacts.
- Ask Why remains public-artifact-only and read-only.
- Steer remains route-gated and delivered through `operator_messages.jsonl`
  plus MCP `check_operator_messages`.

Deterministic verification evidence:

```bash
node --check roboclaws/operator_console/static/app.js
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console
./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py
.venv/bin/ruff check roboclaws/operator_console roboclaws/household tests/unit/operator_console tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py
```

Static console smoke evidence:

- `just console::run 127.0.0.1 8876`
- `/`, `/app.js`, and `/styles.css` served with no-store cache headers.
- Left setup area contains `Operator Input` with `Goal`, `Steer`, and
  `Ask Why`.
- State/evidence rail contains no operator text input.
- Static assets include `/next-goal` and no public `/continue` route.
- Browser automation through the local gstack browse CLI was attempted but the
  current Chromium runtime failed before page load with `No usable sandbox`;
  this was treated as a browser-runtime issue, not an app failure, and the HTTP
  static smoke plus live API proof covered the interaction contract.

Live acceptance evidence:

- Network preflight: `just dev::network-status` reported `network: work`, so
  OpenClaw/system-provider Claude routes remained blocked. Repo-local Codex
  provider keys were present, so the supported Docker-backed Codex route was
  allowed.
- Console route: `just console::run 127.0.0.1 8876`
- Live passed parent run:
  `20260609-235202-codex-mujoco-cleanup`
- Report:
  `output/operator-console/runs/20260609-235202-codex-mujoco-cleanup/0609_2352/seed-7/report.html`
- Result:
  `output/operator-console/runs/20260609-235202-codex-mujoco-cleanup/0609_2352/seed-7/run_result.json`
- Checker/status: passed. Terminal reason:
  `Completed full-room sweep and resolved cleanup candidates: Potato inside
  fridge, Pillow on bed, Plate at sink, RemoteControl on TV stand, Book inside
  shelving. All 14 generated exploration waypoints observed.`
- Steer proof:
  `steer-09dcabe66c7c` moved from `queued` to `seen` at
  `2026-06-09T15:52:43Z` after Codex read it through
  `check_operator_messages`.
- Ask Why proof:
  `ask_why-d399ac67b220` returned `status="answered"` with
  `basis="public_operator_artifacts_only"`,
  `robot_mcp_tools_called=false`, and `private_evaluation_used=false`.
- Next Goal proof:
  `next_goal-96e0ba48dea8` returned `status="started"`,
  `confirmation_required=false`, and started linked child run
  `20260610-000401-codex-mujoco-cleanup` with
  `parent_run_id="20260609-235202-codex-mujoco-cleanup"` and public parent
  artifact references. The child was immediately stopped by the operator to
  release the simulator/provider lock.
- Earlier failed/checker-failed parent proof:
  `20260609-233753-codex-mujoco-cleanup` required
  `confirmation_required=true` before starting child
  `20260609-234854-codex-mujoco-cleanup`, validating the explicit
  confirmation path.

Parked follow-ups:

- Add richer steer lifecycle states such as `applied`, `rejected`, and
  `expired`; parked because v1 acceptance only needs durable queueing,
  pending hints, and MCP `seen` acknowledgement. Unpark when the task skill
  defines how agents should explicitly apply or reject operator instructions.
- Replace deterministic Ask Why with an optional live analyzer route; parked
  because v1 intentionally avoids provider calls and robot MCP mutation for
  read-only explanations. Unpark when product wants natural-language analysis
  beyond public artifact summarization.

## Next Goal Refactor Decisions

Accepted on 2026-06-09 after the first v1 interaction slice and implemented in
the Next Goal refactor.

The first implementation shipped with `Continue After Run` language and
`continue` API/artifact names. That wording is superseded by **Next Goal**
across the UI, API, and artifacts, without a compatibility alias.

Durable decisions:

- User-visible follow-up language is `Next Goal`, not `Continue`.
- API/artifact names should use the same concept:
  - `POST /api/runs/<run_id>/next-goal`
  - `next_goal_queue.jsonl`
  - `command_type="next_goal"`
  - route/state fields should use `next_goal_*` where a new field is needed.
- Do not keep `/continue`, `continue_queue.jsonl`, or
  `command_type="continue"` as public compatibility paths.
- All operator text inputs belong in the left setup/input area. The right side
  is state, evidence, outputs, raw artifact inspection, and run controls.
- The left input area is a unified operator input composer with explicit modes:
  `Goal`, `Steer`, and `Ask Why`.
- `Goal` mode starts a new run when no run is attached. After a terminal run,
  the same mode starts a linked `Next Goal` run.
- While a run is active, first-slice behavior should not implement automatic
  "run after current" queueing. Active-run operator text defaults to
  `Steer Current Run`; `Next Goal` is available only after the parent run is
  terminal.
- A terminal failed, stopped, or checker-failed parent may still start a
  `Next Goal` after explicit operator confirmation. This starts a new linked
  Robot Run; it is not recovery or mutation of the failed parent.
- A `Next Goal` run should inherit route, driver, backend, profile, world/run
  setup, operator session, `next_goal_packet`, and public parent artifact
  references by default.
  The new goal text is operator-authored for the child run.
- Real-robot or real-movement gates remain in the left setup area and must be
  reconfirmed for a `Next Goal` launch when they gate real movement. They are
  not silently inherited from the parent run.
- If no run is attached and the operator provides a prompt without explicitly
  selecting an intent, keep the existing household-world rule: prompt implies
  `intent=open-ended`; explicit `intent=cleanup` remains prompt-scoped cleanup.

## Goal

Give the operator console a clear interaction model for asking questions,
steering active robot work, and continuing with follow-up work without weakening
`done` as the terminal boundary for one robot run.

The product model is:

```text
Operator Session
  -> Robot Run 1 -> done -> report/checker artifacts
  -> Ask Why over Robot Run 1 artifacts
  -> Next Goal: Robot Run 2 linked to Robot Run 1
  -> Steer Robot Run 2 while it is active
```

An **Operator Session** is long-lived. A **Robot Run** is short-lived and ends
at `done`, Stop, Emergency Stop, or a live-agent failure.

## Current Source Evidence

- `docs/plans/refactor-live-agent-runner-boundary.md` locks live Codex and
  Claude runners as one-turn launch/artifact/checker wrappers. They must not
  become cleanup supervisors.
- `scripts/molmo_cleanup/run_live_codex_cleanup.py` launches one
  `codex exec --json` turn and requires `done` to produce `run_result.json`.
- `scripts/molmo_cleanup/run_live_claude_cleanup.py` launches one Claude Code
  print-mode turn and requires the same `done`/checker boundary.
- `roboclaws/household/realworld_mcp_server.py` finalizes reports and
  `run_result.json` in the `done` path.
- `roboclaws/household/realworld_mcp_backend.py` rejects non-`done` tool calls
  after the server's `done_event` is set.
- `roboclaws/operator_console/server.py` currently exposes start, status, raw
  artifact, stop, and emergency-stop APIs. It does not expose a live message
  API.
- `docs/human/mcp-skills-and-semantic-profiles.md` defines
  `household_episode_v1` as the profile layer that owns task completion through
  `done`.

## Decisions Already Made

1. Keep `done` terminal for a single Robot Run.
   `done` writes review artifacts, fixes the report/checker boundary, and
   prevents later robot tool calls from changing that run's evidence.

2. Do not inject operator text into `codex exec` or tmux/stdin.
   Stdin injection would not be a stable, auditable agent-control protocol and
   can corrupt the event stream or make it unclear whether the model saw the
   message.

3. Separate read-only questions from behavior-changing steering.
   `Ask Why` and `Steer` are different commands with different safety and audit
   properties.

4. Treat post-`done` continuation as a linked follow-up run, not as mutation of
   the completed run.
   The previous run can provide public context to the next run, but the old
   report remains immutable.

5. Keep Private Evaluation out of agent-facing Next Goal context.
   Follow-up runs may use public Agent View, Runtime Metric Map, trace summaries,
   report links, and operator-authored notes. They must not use hidden mess
   membership, acceptable destination sets, private manifests, or scorer truth
   as agent input.

6. Allow active-run steering during long MCP runs.
   Steering is not a post-`done` feature. A long-running cleanup or service task
   should accept operator hints while it is active. The agent receives those
   hints the next time it checks the operator-message MCP surface at a safe
   checkpoint.

7. Require explicit operator input modes for new text.
   The console should not infer whether new operator text means Goal,
   Ask Why, or Steer Current Run. The mode must be explicit because only
   Steer mutates the active run, while Goal starts a Robot Run or linked
   Next Goal run.

8. Treat Next Goal as a terminal-parent follow-up for the shipped slice.
   The implementation starts a linked follow-up Robot Run after the parent run
   is terminal. Active-run "run after current" queueing is out of scope for the
   first Next Goal refactor.

## Interaction Types

### Ask Why

`Ask Why` is a read-only analysis action. It answers operator questions such as:

- "Why did the agent pick that object first?"
- "Why did it call `done`?"
- "Why did it avoid the table?"
- "What evidence was available before that action?"

The answer is produced by a separate analyzer process or agent that reads public
run artifacts. It does not talk to the robot MCP server and cannot change robot
state.

Recommended artifact scope:

- `operator_state.json`
- `live_status.json`
- `trace.jsonl`
- `codex-events.jsonl`, `claude-events.jsonl`, or `openai-agents-events.jsonl`
- `agent_view.json`
- `runtime_metric_map.json`
- `run_result.json` with private fields redacted or summarized only through
  public-facing fields
- `report.html` link and public report summary

### Steer Current Run

`Steer Current Run` is a behavior-changing action for an active Robot Run. It
lets the operator provide hints, constraints, priorities, or corrective
instructions while the run is still active.

Examples:

- "Before picking anything else, observe the desk again."
- "Do not move the cup."
- "Prioritize books before soft objects."
- "If you are about to call `done`, explain the public evidence first."

Steering should be artifact-backed and agent-visible through a public MCP tool,
not injected into the coding-agent process. The intended transport is:

```text
console POST /api/runs/<run_id>/messages
  -> append operator_messages.jsonl
  -> active MCP server exposes check_operator_messages
  -> agent checks at safe checkpoints
  -> acknowledgement is written into trace/operator_messages.jsonl
```

Safe checkpoints should be owned by the task skill and MCP contract. Initial
default checkpoints:

- after `metric_map`
- after `observe`
- before starting a new cleanup object chain
- before `done`

Steering is active while the Robot Run is non-terminal. It is best-effort until
acknowledged: the operator can append a hint during a long cleanup or service
task, and the agent should incorporate it the next time it checks
`check_operator_messages`. If a steer message is urgent enough that waiting for
the next checkpoint is unsafe, the operator should use Stop or Emergency Stop
instead of Steer. The UI must show whether a message is `queued`, `seen`,
`applied`, `rejected`, or `expired`.

### Next Goal

`Next Goal` starts a new Robot Run linked to an Operator Session and optionally
a parent Robot Run. It is used when the previous run is already terminal or
when the operator intentionally starts a new episode.

Examples:

- "Now also build the semantic map."
- "Start the next room."
- "Run the same cleanup again but avoid moving books."

The new run should receive a public Next Goal packet:

- `operator_session_id`
- `parent_run_id`
- new operator prompt
- public summary of the parent run
- public Runtime Metric Map or Actionable Semantic Map Snapshot when available
- artifact links for human review
- clear instruction that this is a follow-up episode, not mutation of the parent
  report

For the first Next Goal refactor, active-run queueing is intentionally out of
scope. While a Robot Run is active, operator text should use Steer Current Run
or read-only Ask Why. Next Goal becomes available after the parent reaches a
terminal state.

## Non-Goals

- Do not remove or weaken `done`.
- Do not make live Codex or Claude runners automatically continue after an
  unfinished run.
- Do not make the console a generic shell or arbitrary `just` executor.
- Do not expose Private Evaluation as agent input for Ask Why, Steer, or
  Next Goal.
- Do not claim hidden model chain-of-thought visibility.
- Do not implement physical manipulation steering for Agibot cleanup while
  physical cleanup manipulation remains a blocked capability.
- Do not require SDK runtime migration before the first Ask Why or follow-up-run
  implementation.

## Product State Model

### Operator Session

An Operator Session groups one or more Robot Runs and read-only Ask Why answers.
It is a console/user conversation surface, not a robot execution artifact by
itself.

Minimum fields:

- `operator_session_id`
- `created_at`
- `active_run_id`
- `run_ids`
- `message_ids`

### Robot Run

A Robot Run is one task execution attempt through an existing route. It owns the
current backend lock, MCP server, live agent turn, artifacts, checker, and
terminal state.

Terminal states:

- `done`
- `stopped_by_operator`
- `emergency_stopped`
- `failed`

After a Robot Run is terminal:

- Ask Why remains available.
- Next Goal may create a linked follow-up Robot Run.
- Steer Current Run is unavailable and should offer Next Goal instead.

While a Robot Run is active:

- Ask Why remains available as read-only analysis over current artifacts.
- Steer Current Run may append active-run hints.
- Next Goal active-run queueing is out of scope for the first refactor.

### Operator Message

An Operator Message is either read-only (`ask_why`) or behavior-changing
(`steer`, `next_goal`). The command type must be explicit in the API and UI.

Suggested status values:

- `queued`
- `running`
- `answered`
- `seen`
- `applied`
- `rejected`
- `expired`
- `failed`

## API Shape Draft

```text
POST /api/sessions
GET  /api/sessions/<session_id>

POST /api/runs
POST /api/runs/<run_id>/ask-why
POST /api/runs/<run_id>/messages
POST /api/runs/<run_id>/next-goal
GET  /api/runs/<run_id>/messages
```

`POST /api/runs/<run_id>/messages` is for active-run steering only.
`POST /api/runs/<run_id>/next-goal` creates a new linked run when the parent is
terminal. It may require operator confirmation when the parent failed, was
stopped, or when a physical/real-movement gate must be reconfirmed.

## Grill Batch Decisions

### Batch 1: Control Model And Safety Boundaries

Resolved on 2026-06-09:

- `Ask Why` is public-agent-perspective analysis only. It should not use
  Private Evaluation or hidden scorer truth. A future separate action such as
  `Explain Score` may use post-run private scoring evidence if the UI labels it
  clearly as scorer-side explanation rather than agent reasoning.
- `Steer Current Run` is not done-only. It can be appended while a Robot Run is
  active and should be delivered through the MCP operator-message surface at the
  next safe checkpoint.
- `Steer Current Run` is not the safety interrupt. Stop and Emergency Stop
  remain the operator controls for urgent intervention.
- New operator text must use an explicit mode: Goal, Ask Why, or Steer Current
  Run. The console must not infer mode from text.
- Goal mode starts the first run when no run is attached and starts a linked
  Next Goal run after a terminal parent. Active-run "run after current" queueing
  is out of scope for the first Next Goal refactor.
- Follow-up runs should inherit public-safe Runtime Metric Map context
  automatically when available, with the included parent artifacts shown to the
  operator.
- Implementation order for the shipped slice was Next Goal rename/terminal
  follow-up startup, left-side unified input composer, then additional steer
  lifecycle hardening as parked follow-up work.

### Batch 2: Next Goal And Delivery Semantics

Resolved on 2026-06-09:

- `Next Goal` replaces `Continue After Run` as the public follow-up concept.
  The refactor renamed UI/API/artifact names and does not preserve
  compatibility aliases.
- Next Goal starts only after a terminal parent in the first refactor. Active
  runs use Steer Current Run or Ask Why.
- A terminal failed, stopped, or checker-failed parent may still start a
  Next Goal after explicit operator confirmation.
- Physical robot routes, routes with `emergency_stop_required=true`, and any
  route with real movement enabled require operator confirmation and relevant
  gate reconfirmation before a Next Goal starts.
- Active-run steer delivery should not rely only on the agent remembering to
  call `check_operator_messages`. Ordinary MCP responses should include a small
  pending hint such as `operator_message_pending=true` when unread steer exists.
  Full message retrieval and acknowledgement still happen through
  `check_operator_messages`.
- Steer Current Run is route-gated. Only routes that declare
  `supports_operator_steer=true` should enable the UI/API action. Other routes
  must show a clear unavailable state.
- Ask Why is allowed during active runs. Active-run answers must be labeled as
  based on artifacts available so far. Terminal-run answers may include the
  final public run result.

## Vertical Slices

1. **Plan and terminology**
   Lock the Operator Session / Robot Run / Operator Message vocabulary, command
   types, and `done` boundary.

2. **Ask Why v1**
   Add a read-only console API and UI panel that answers questions from public
   artifacts. It may start with a deterministic summarizer before adding a
   live analyzer agent.

3. **Follow-Up Run v1**
   Add `operator_session_id` and `parent_run_id` metadata to console runs and
   start payloads. Allow the operator to launch a new run from a terminal run
   with a public Next Goal packet.

4. **Steer Inbox v1**
   Add `operator_messages.jsonl`, console POST/read APIs, an MCP
   `check_operator_messages` tool, trace logging, and skill instructions for
   safe checkpoints.

5. **Steer UX hardening**
   Show queued/seen/applied/rejected state, expiration, and a clear "not yet
   seen by agent" warning.

6. **SDK/session runtime spike, optional**
   Use `LiveAgentRuntime` SDK routes only if the CLI one-turn routes cannot
   provide enough visibility for Ask Why or follow-up-run ergonomics. This is
   not required for the first implementation.

## Acceptance Criteria

- `done` remains terminal for one Robot Run.
- A terminal Robot Run rejects Steer Current Run and offers Next Goal instead.
- Ask Why can run after `done` and does not call robot MCP tools.
- Ask Why answers cite or summarize public artifacts instead of claiming hidden
  chain-of-thought.
- Next Goal runs carry `operator_session_id` and `parent_run_id` metadata.
- Next Goal context excludes Private Evaluation and hidden scorer truth.
- Active-run Next Goal queueing is not part of the first refactor.
- Active-run steering is stored in auditable artifacts and delivered through a
  public MCP tool, not stdin/tmux injection.
- The left input composer distinguishes Goal, Steer Current Run, and Ask Why.
- Tests cover state transitions and artifact boundaries without live provider
  calls.

## Verification Contract

Implemented deterministic checks:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console
./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py
.venv/bin/ruff check roboclaws/operator_console roboclaws/household tests/unit/operator_console tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py
node --check roboclaws/operator_console/static/app.js
```

Implemented focused checks cover:

- Ask Why cannot access Private Evaluation as agent input.
- Post-`done` steer returns a clear terminal-run error.
- Next Goal creates a linked run with a parent run id.
- `operator_messages.jsonl` preserves ordering and redaction.
- MCP `check_operator_messages` marks messages as seen or rejected.
- A steer message appended during an active run remains queued until the agent
  checks the MCP operator-message tool.
- Ordinary MCP responses expose only a pending steer hint when unread messages
  exist; message contents are retrieved through `check_operator_messages`.
- A steer message appended after `done` is rejected with a terminal-run error
  and the API offers Next Goal instead.
- Next Goal can start after terminal state plus result/report availability.
- Failed, stopped, checker-failed, physical, or real-movement parents require
  explicit operator confirmation before Next Goal start.

Live Codex validation is required for this interaction behavior because the
claim depends on a live coding agent reading steer messages and the console
starting a linked child run after terminal evidence. Live Claude, Isaac, Agibot,
GPU, and physical-robot validation remain out of scope for this slice.

## Grill Saturation Audit

No more discussion is needed before implementation.

Resolved user-level decisions now cover:

- public input modes: Goal, Ask Why, Steer Current Run;
- `done` terminal semantics for one Robot Run;
- active-run steering through MCP checkpoints;
- Next Goal terminal-parent follow-up semantics;
- failed/physical/real-movement confirmation;
- public-artifact boundaries for Ask Why and follow-up context.

Remaining items are implementation defaults:

- exact JSON schema field names for session/message files beyond the required
  `next_goal` rename;
- exact styling of the left-side input composer;
- deterministic Ask Why summarizer shape before any analyzer-agent route;
- exact expiration timeout for unread steer messages;
- focused test fixture layout.

## Preflight Contract

Preflight status: APPROVED_AND_EXECUTED

Task source: `docs/plans/operator-console-agent-interaction.md` plus the
2026-06-09 Next Goal grill batch.

Canonical source: `docs/plans/operator-console-agent-interaction.md`.

Route: durable `$intuitive-flow`.

Goal:
Refactor the operator console from `Continue` to `Next Goal`, unify all
operator text inputs in the left setup/input area, and make terminal follow-up
goals actually start linked Robot Runs without weakening `done` as the terminal
boundary for one Robot Run.

Scope:

- Rename the existing follow-up concept from Continue to Next Goal across UI,
  API endpoints, artifact filenames, command types, state fields, tests, and
  visible copy.
- Remove public compatibility paths for `/continue`, `continue_queue.jsonl`,
  and `command_type="continue"`.
- Add or update the Next Goal API as `POST /api/runs/<run_id>/next-goal`.
- Use `next_goal_queue.jsonl` only where a durable Next Goal request artifact
  is still needed.
- Make terminal-parent Next Goal startup create a linked child Robot Run with
  `operator_session_id`, `parent_run_id`, and public parent-context evidence.
- For terminal failed, stopped, checker-failed, physical, real-movement, or
  `emergency_stop_required` parents, require explicit operator confirmation
  before starting the Next Goal.
- Move all operator text inputs into the left setup/input area.
- Replace separate prompt/operator-message surfaces with one left-side operator
  input composer whose modes are `Goal`, `Steer`, and `Ask Why`.
- Keep the right side as state, evidence, outputs, raw artifact inspection, and
  run controls.
- Preserve Ask Why as read-only public-artifact analysis.
- Preserve Steer Current Run as active-run route-gated MCP inbox delivery.
- Update route metadata, state derivation, redaction, static UI, and focused
  unit/static/API tests as needed.

Non-goals:

- Do not remove or weaken `done`.
- Do not make Codex or Claude live runners automatically continue unfinished
  work outside an explicit Next Goal start.
- Do not implement active-run "run after current" queueing in the first
  Next Goal refactor.
- Do not preserve `/continue`, `continue_queue.jsonl`, or
  `command_type="continue"` as public compatibility paths after the rename.
- Do not introduce a generic browser-submitted shell or arbitrary `just`
  executor.
- Do not inject operator text into `codex exec`, Claude print mode, tmux, or
  stdin.
- Do not expose Private Evaluation or hidden scorer truth as agent input.
- Do not claim hidden model chain-of-thought visibility.
- Do not enable physical cleanup manipulation or physical manipulation steering
  while those capabilities remain blocked.
- Do not require OpenAI Agents SDK or any other SDK runtime migration for the
  first implementation.
- Do not require live Claude, Isaac, Agibot, GPU, or physical-robot validation
  as part of this implementation contract.
- Do not require live Codex for every intermediate edit. Live Codex cleanup is
  required before marking the full behavior accepted, but deterministic tests
  remain the first implementation gate.

Context package:

- Must read:
  - `docs/plans/operator-console-agent-interaction.md`
  - `docs/plans/refactor-live-agent-runner-boundary.md`
  - `docs/plans/operator-console-layered-launch-gates.md`
  - `roboclaws/operator_console/server.py`
  - `roboclaws/operator_console/interactions.py`
  - `roboclaws/operator_console/launcher.py`
  - `roboclaws/operator_console/routes.py`
  - `roboclaws/operator_console/state.py`
  - `roboclaws/operator_console/static/index.html`
  - `roboclaws/operator_console/static/app.js`
  - `roboclaws/operator_console/static/styles.css`
  - `roboclaws/household/realworld_mcp_server.py`
  - `roboclaws/household/realworld_mcp_backend.py`
  - `tests/unit/operator_console/`
- Useful evidence:
  - `roboclaws/agents/live_runtime.py`
  - `scripts/molmo_cleanup/run_live_codex_cleanup.py`
  - `scripts/molmo_cleanup/run_live_claude_cleanup.py`
  - `docs/human/mcp-skills-and-semantic-profiles.md`
  - `docs/human/domain.md`
  - `tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`
- Do not read unless needed:
  - historical retrospectives
  - large generated reports under `output/`
  - Isaac/GPU/Agibot runtime artifacts
  - unrelated planner-proof or visual-grounding plans

Definition of Done / acceptance criteria:

- SUCCESS only if:
  - Next Goal uses `POST /api/runs/<run_id>/next-goal`,
    `next_goal_queue.jsonl` when a durable request artifact is needed, and
    `command_type="next_goal"`.
  - Public follow-up run context uses `next_goal_packet`; no public
    `continuation_packet` compatibility field remains.
  - The old `/continue`, `continue_queue.jsonl`, and
    `command_type="continue"` names are removed from public console behavior.
  - Next Goal starts linked runs with `operator_session_id` and `parent_run_id`
    after a terminal parent.
  - Active-run Next Goal queueing is not exposed in the first refactor.
  - Failed, stopped, checker-failed, physical, real-movement, or
    `emergency_stop_required` parents require operator confirmation before
    Next Goal start.
  - Post-`done` Steer is rejected with a terminal-run error and offers
    Next Goal.
  - All operator text inputs are in the left setup/input area; the right side
    is state, evidence, outputs, raw artifact inspection, and run controls.
  - The left input composer exposes explicit `Goal`, `Steer`, and `Ask Why`
    modes.
  - Goal mode starts the first run when no run is attached and starts Next Goal
    after a terminal parent.
  - Active-run Goal mode does not silently queue a later run in this slice; the
    UI directs the operator to Steer or Ask Why.
  - Ask Why remains read-only and public-artifact-only.
  - Steer Current Run remains route-gated by `supports_operator_steer=true` and
    still uses `operator_messages.jsonl` plus `check_operator_messages`.
  - Real-robot or real-movement gates remain in the left setup area and are not
    silently inherited for Next Goal launches.
  - Tests cover console API/state behavior, static UI behavior, route gating,
    and artifact naming without live provider calls.
  - A local live Codex household-cleanup proof exercises the changed behavior
    through `just console::run` or the equivalent supported public Codex route,
    and the resulting report/checker artifacts are recorded.
- BLOCKED_NEEDS_DECISION if:
  - A route cannot safely separate public Next Goal context from Private
    Evaluation.
  - Physical-route confirmation semantics become ambiguous beyond the resolved
    confirmation rule.
  - Removing `continue` compatibility would break an explicitly required
    external consumer that is not represented in this plan.
- BLOCKED_NEEDS_LOCAL_VALIDATION if:
  - Deterministic tests pass but the required local browser/live Codex proof
    cannot run because the local provider route, network, Docker runtime,
    browser runtime, or runtime keys are unavailable.
- INTERMEDIATE_ONLY if explicitly approved:
  - The code rename and deterministic tests are complete, but the local
    browser/live Codex proof has not run. This is not complete, merge-ready, or
    no-regression for the operator workflow.
- Must not regress:
  - existing `just console::run` launch behavior;
  - existing start/status/raw/stop/emergency-stop APIs;
  - route readiness and backend lock enforcement;
  - `done` report/checker artifact generation;
  - existing operator-console redaction behavior;
  - Codex/Claude one-turn live-runner boundary.
  - existing active-run Steer delivery through `check_operator_messages`.
  - existing Ask Why private-data redaction.

Verification:

Deterministic implementation gate, completed:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console
./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py
.venv/bin/ruff check roboclaws/operator_console roboclaws/household tests/unit/operator_console tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py
node --check roboclaws/operator_console/static/app.js
```

Static/browser smoke gate, completed with one browser-runtime limitation:

```bash
just console::run 127.0.0.1 8876
```

HTTP/static smoke confirmed:

- all operator text input appears in the left setup/input area;
- right-side panels contain state/evidence/outputs/controls only;
- no visible `Continue` label remains in the operator interaction UI;
- static assets expose `/next-goal` and no public `/continue` route.

The local gstack browser automation command could not load the page because the
current Chromium runtime failed with `No usable sandbox`. This did not block
acceptance because HTTP/static checks and the live API proof covered the
interaction contract.

Local live acceptance gate, completed:

The supported local Codex cleanup route was exercised through:

```bash
just console::run 127.0.0.1 8876
```

The run reached `done`, wrote `run_result.json`, passed the route checker, and
recorded relevant operator-message / Ask Why / Next Goal artifacts:

- Parent run:
  `20260609-235202-codex-mujoco-cleanup`
- Parent report:
  `output/operator-console/runs/20260609-235202-codex-mujoco-cleanup/0609_2352/seed-7/report.html`
- Parent result:
  `output/operator-console/runs/20260609-235202-codex-mujoco-cleanup/0609_2352/seed-7/run_result.json`
- Steer message:
  `steer-09dcabe66c7c`, seen at `2026-06-09T15:52:43Z`
- Ask Why message:
  `ask_why-d399ac67b220`, answered from public artifacts only
- Next Goal message:
  `next_goal-96e0ba48dea8`, started child
  `20260610-000401-codex-mujoco-cleanup`

Live proof acceptance, satisfied:

- Ask Why works against the live run artifacts without mutating robot state.
- A steer message submitted during the active cleanup run is queued, surfaced
  through MCP pending state, read by `check_operator_messages`, and reflected
  in artifacts.
- A terminal-parent follow-up goal can launch with `parent_run_id` and public
  parent-context evidence.
- The Codex cleanup still reaches `done`, produces `run_result.json`, and
  passes the route checker.

Live Codex required local provider keys, the supported Docker-backed coding
agent runtime, and normal local runtime availability; those prerequisites were
available through the repo-local Codex provider route. Live Claude, Isaac,
Agibot, GPU, and physical-robot validation remain out of scope unless the
execution owner explicitly broadens the slice.

Execution surface:

- Main session: root supervisor. It should preserve this plan as the canonical
  scope, inspect worker changes, and decide final complete/blocked status.
- Worker: none by default. Use a worker only if implementation becomes
  long-running or needs isolated UI/MCP subtasks.
- Worker-local goal: none.

Main-session `/goal` prompt:

```text
/goal execute docs/plans/operator-console-agent-interaction.md with intuitive-flow
```

To execute:

```text
/goal execute docs/plans/operator-console-agent-interaction.md with intuitive-flow
```

Approval gate:
Reply LGTM, approve, or go ahead to approve the contract. To start durable
execution from the main session, use the exact `To execute` command above;
otherwise request edits.
