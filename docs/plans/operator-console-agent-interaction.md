---
plan_scope: operator-console-agent-interaction
status: IMPLEMENTED_V1
source:
  - 2026-06-09 operator-console steering discussion
  - intuitive-reduce-entropy
  - grill-with-docs-batch
last_reviewed: 2026-06-09
---

# Operator Console Agent Interaction

## Implementation Result

Implemented on 2026-06-09.

Shipped v1 includes:

- Operator Session artifacts and session APIs.
- deterministic Ask Why over public run artifacts.
- explicit Steer Current Run and Continue After Run APIs/UI modes.
- linked follow-up run metadata with `operator_session_id`, `parent_run_id`,
  and public continuation packets.
- route-gated active-run steering through `operator_messages.jsonl` and the
  household MCP `check_operator_messages` tool.
- ordinary MCP pending-message hints without exposing full message text.
- simulator queued Continue auto-start only after terminal parent evidence;
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

Parked follow-ups:

- Add richer steer lifecycle states such as `applied`, `rejected`, and
  `expired`; parked because v1 acceptance only needs durable queueing,
  pending hints, and MCP `seen` acknowledgement. Unpark when the task skill
  defines how agents should explicitly apply or reject operator instructions.
- Replace deterministic Ask Why with an optional live analyzer route; parked
  because v1 intentionally avoids provider calls and robot MCP mutation for
  read-only explanations. Unpark when product wants natural-language analysis
  beyond public artifact summarization.

## Goal

Give the operator console a clear interaction model for asking questions,
steering active robot work, and continuing with follow-up work without weakening
`done` as the terminal boundary for one robot run.

The product model is:

```text
Operator Session
  -> Robot Run 1 -> done -> report/checker artifacts
  -> Ask Why over Robot Run 1 artifacts
  -> Robot Run 2 linked to Robot Run 1
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

5. Keep Private Evaluation out of agent-facing continuation context.
   Follow-up runs may use public Agent View, Runtime Metric Map, trace summaries,
   report links, and operator-authored notes. They must not use hidden mess
   membership, acceptable destination sets, private manifests, or scorer truth
   as agent input.

6. Allow active-run steering during long MCP runs.
   Steering is not a post-`done` feature. A long-running cleanup or service task
   should accept operator hints while it is active. The agent receives those
   hints the next time it checks the operator-message MCP surface at a safe
   checkpoint.

7. Require explicit operator intent for new text.
   The console should not infer whether a new user prompt means Ask Why, Steer
   Current Run, or Continue After Run. The UI/API mode must be explicit because
   only Steer mutates the active run.

8. Allow explicit Continue After Run queueing.
   While a Robot Run is active, the operator may queue a follow-up prompt that
   should start only after the active run reaches a terminal state. This is
   different from Steer Current Run: queued Continue does not change the active
   run's behavior.

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

### Continue With Follow-Up Run

`Continue` starts or queues a new Robot Run linked to an Operator Session and
optionally a parent Robot Run. It is used when the previous run is already
terminal, when the operator intentionally starts a new episode, or when the
operator wants to queue the next long task while the current run continues.

Examples:

- "Now also build the semantic map."
- "Continue with the next room."
- "Run the same cleanup again but avoid moving books."

The new run should receive a public continuation packet:

- `operator_session_id`
- `parent_run_id`
- new operator prompt
- public summary of the parent run
- public Runtime Metric Map or Actionable Semantic Map Snapshot when available
- artifact links for human review
- clear instruction that this is a follow-up episode, not mutation of the parent
  report

If Continue is queued while the parent run is active, the queued prompt should
remain inert until the parent run is terminal. It must not be visible to the
active agent as a steer message.

## Non-Goals

- Do not remove or weaken `done`.
- Do not make live Codex or Claude runners automatically continue after an
  unfinished run.
- Do not make the console a generic shell or arbitrary `just` executor.
- Do not expose Private Evaluation as agent input for Ask Why, Steer, or
  Continue.
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
- Continue may create a linked follow-up Robot Run.
- Steer Current Run is unavailable and should offer Continue instead.

While a Robot Run is active:

- Ask Why remains available as read-only analysis over current artifacts.
- Steer Current Run may append active-run hints.
- Continue After Run may queue a follow-up Robot Run without changing the
  active run.

### Operator Message

An Operator Message is either read-only (`ask_why`) or behavior-changing
(`steer`, `continue`). The command type must be explicit in the API and UI.

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
POST /api/runs/<run_id>/continue
GET  /api/runs/<run_id>/messages
```

`POST /api/runs/<run_id>/messages` is for active-run steering only.
`POST /api/runs/<run_id>/continue` creates a new linked run when the parent is
terminal, or queues one when the parent is active.

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
- New operator text must use an explicit mode: Ask Why, Steer Current Run, or
  Continue After Run. The console must not infer mode from text.
- Continue After Run may be queued while the current run is active. Queued
  follow-up prompts are not shown to the active agent and do not mutate the
  active run.
- Follow-up runs should inherit public-safe Runtime Metric Map context
  automatically when available, with the included parent artifacts shown to the
  operator.
- Implementation order remains Ask Why first, then Continue After Run, then
  Steer Current Run, unless local execution planning finds that the steer inbox
  is cheaper to build as a shared substrate for Continue.

### Batch 2: Queue And Delivery Semantics

Resolved on 2026-06-09:

- Queued Continue After Run may auto-start for simulator routes.
- Physical robot routes, routes with `emergency_stop_required=true`, and any
  route with real movement enabled require operator confirmation before a queued
  follow-up starts.
- Queued Continue waits for terminal state plus checker/result availability.
  If the parent run fails, is stopped, or lacks required result artifacts, the
  queued item pauses and asks the operator to confirm, edit, or discard it.
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
   with a public continuation packet.

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
- A terminal Robot Run rejects Steer Current Run and offers Continue instead.
- Ask Why can run after `done` and does not call robot MCP tools.
- Ask Why answers cite or summarize public artifacts instead of claiming hidden
  chain-of-thought.
- Follow-up runs carry `operator_session_id` and `parent_run_id` metadata.
- Follow-up context excludes Private Evaluation and hidden scorer truth.
- A queued follow-up prompt does not affect the active Robot Run.
- Active-run steering is stored in auditable artifacts and delivered through a
  public MCP tool, not stdin/tmux injection.
- The UI distinguishes Ask Why, Steer Current Run, and Continue.
- Tests cover state transitions and artifact boundaries without live provider
  calls.

## Verification

CI-safe checks:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console
.venv/bin/ruff check roboclaws/operator_console tests/unit/operator_console
```

Focused future checks should cover:

- Ask Why cannot access Private Evaluation as agent input.
- Post-`done` steer returns a clear terminal-run error.
- Continue creates a linked run with a parent run id.
- `operator_messages.jsonl` preserves ordering and redaction.
- MCP `check_operator_messages` marks messages as seen or rejected.
- A steer message appended during an active run remains queued until the agent
  checks the MCP operator-message tool.
- Ordinary MCP responses expose only a pending steer hint when unread messages
  exist; message contents are retrieved through `check_operator_messages`.
- A steer message appended after `done` is rejected with a terminal-run error
  and the API offers Continue After Run instead.
- A Continue After Run prompt queued before terminal state starts only after the
  parent Robot Run reaches a terminal state.
- Simulator queued Continue can auto-start after terminal state plus
  checker/result availability.
- Physical or real-movement queued Continue requires operator confirmation
  before start.

No live Codex, Claude, Isaac, or Agibot validation is required for the plan
slice. Live validation belongs to later local proof once the deterministic
console and MCP contracts are in place.

## Grill Saturation Audit

No more discussion is needed before implementation.

Resolved user-level decisions now cover:

- public command modes: Ask Why, Steer Current Run, Continue After Run;
- `done` terminal semantics for one Robot Run;
- active-run steering through MCP checkpoints;
- queued Continue After Run semantics;
- simulator auto-start versus physical/real-movement confirmation;
- public-artifact boundaries for Ask Why and follow-up context.

Remaining items are implementation defaults:

- exact JSON schema field names for session/message files;
- exact UI placement and copy for the three command modes;
- deterministic Ask Why summarizer shape before any analyzer-agent route;
- exact expiration timeout for unread steer messages;
- focused test fixture layout.

## Preflight Contract

Preflight status: DRAFT

Task source: `docs/plans/operator-console-agent-interaction.md` plus the
2026-06-09 discussion.

Canonical source: `docs/plans/operator-console-agent-interaction.md`.

Route: durable `$intuitive-flow`.

Goal:
Implement the operator-console interaction model so operators can Ask Why,
queue Continue After Run, and steer active supported MCP runs without weakening
`done` as the terminal boundary for one Robot Run.

Scope:

- Add an Operator Session / Robot Run / Operator Message state layer to the
  operator console.
- Add explicit console API/UI actions for Ask Why, Steer Current Run, and
  Continue After Run.
- Implement Ask Why v1 as read-only public-artifact analysis. A deterministic
  summarizer is acceptable before adding a live analyzer agent.
- Implement Follow-Up Run v1 with `operator_session_id`, `parent_run_id`, and a
  public continuation packet.
- Implement active-run steering only for routes that declare support.
- Add an auditable operator-message artifact such as `operator_messages.jsonl`.
- Add a public MCP operator-message tool, tentatively `check_operator_messages`,
  for supported household routes.
- Add a pending-message hint to ordinary MCP responses when unread steer
  messages exist.
- Update route metadata, state derivation, redaction, and static UI as needed.
- Add focused tests for state transitions, artifact boundaries, route gating,
  and MCP message delivery.

Non-goals:

- Do not remove or weaken `done`.
- Do not make Codex or Claude live runners automatically continue unfinished
  work outside the explicit Continue After Run queue.
- Do not inject operator text into `codex exec`, Claude print mode, tmux, or
  stdin.
- Do not expose Private Evaluation or hidden scorer truth as agent input.
- Do not claim hidden model chain-of-thought visibility.
- Do not make the console a generic shell or arbitrary `just` executor.
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
  - `roboclaws/operator_console/server.py`
  - `roboclaws/operator_console/launcher.py`
  - `roboclaws/operator_console/routes.py`
  - `roboclaws/operator_console/state.py`
  - `roboclaws/operator_console/static/index.html`
  - `roboclaws/operator_console/static/app.js`
  - `roboclaws/operator_console/static/styles.css`
  - `roboclaws/household/realworld_mcp_server.py`
  - `roboclaws/household/realworld_mcp_backend.py`
  - `skills/molmo-realworld-cleanup/SKILL.md`
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
  - Ask Why can be requested for active and terminal runs using public artifacts
    only.
  - Ask Why output does not call robot MCP tools and does not expose Private
    Evaluation as agent input.
  - Continue After Run creates or queues linked runs with
    `operator_session_id` and `parent_run_id`.
  - Queued Continue does not affect the active Robot Run.
  - Simulator queued Continue can auto-start only after terminal state plus
    checker/result availability.
  - Physical, real-movement, or `emergency_stop_required` queued Continue waits
    for operator confirmation.
  - Steer Current Run is enabled only for routes that declare
    `supports_operator_steer=true`.
  - Active-run steer appends auditable operator messages and exposes only a
    pending hint in ordinary MCP responses.
  - Full steer content retrieval and acknowledgement happen through
    `check_operator_messages`.
  - Post-`done` Steer is rejected with a terminal-run error and offers Continue
    After Run.
  - Tests cover console API/state behavior and MCP message delivery without live
    provider calls.
  - A local live Codex household-cleanup proof exercises the changed behavior
    through `just console::run` or the equivalent supported public Codex route,
    and the resulting report/checker artifacts are recorded.
- PARTIAL if:
  - Ask Why and Continue After Run are implemented with tests, but Steer Inbox
    is left as a documented route-gated follow-up.
  - Console backend APIs are implemented with deterministic tests, but UI polish
    remains minimal.
  - Deterministic tests pass but live Codex cleanup could not be run because the
    local provider route, network, Docker runtime, or runtime keys were
    unavailable. In this case the implementation must report the missing live
    gate explicitly and must not call the full behavior accepted.
- BLOCKED_NEEDS_DECISION if:
  - Implementing steer requires changing `done` terminal semantics.
  - A route cannot safely separate public continuation context from Private
    Evaluation.
  - Physical-route auto-start semantics become ambiguous beyond the resolved
    confirmation rule.
  - Adding the MCP operator-message tool would require a broader profile/API
    decision than household routes.
- Must not regress:
  - existing `just console::run` launch behavior;
  - existing start/status/raw/stop/emergency-stop APIs;
  - route readiness and backend lock enforcement;
  - `done` report/checker artifact generation;
  - existing operator-console redaction behavior;
  - Codex/Claude one-turn live-runner boundary.

Verification:

Deterministic implementation gate:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console
./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py
.venv/bin/ruff check roboclaws/operator_console roboclaws/household tests/unit/operator_console tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py
```

If implementation edits static UI behavior materially, also run:

```bash
just console::run
```

and manually smoke the console in a browser.

Local live acceptance gate:

Before marking the full behavior accepted, run a supported local Codex cleanup
route and exercise the changed interaction surface against it. Preferred route:

```bash
just console::run
```

Then launch a Codex MuJoCo household cleanup from the console, verify the run
still reaches `done`, and record the generated `report.html`, `run_result.json`,
and relevant operator-message / Ask Why / Continue artifacts.

If a non-UI command is needed for setup or comparison, use the supported public
route shape, for example:

```bash
just task::run household-cleanup codex world-oracle-labels backend=molmospaces_subprocess seed=7 generated_mess_count=5
```

Live proof acceptance:

- Ask Why works against the live run artifacts without mutating robot state.
- If Steer Inbox is in the implemented slice, a steer message submitted during
  the active cleanup run is queued, surfaced through MCP pending state, read by
  `check_operator_messages`, and reflected in artifacts.
- If Continue After Run is in the implemented slice, a follow-up prompt can be
  queued or launched with `parent_run_id` and public continuation context.
- The Codex cleanup still reaches `done`, produces `run_result.json`, and
  passes the route checker.

Live Codex requires local provider keys, the supported Docker-backed coding
agent runtime, and normal local runtime availability. If those prerequisites are
unavailable, stop at PARTIAL and report the missing live gate instead of handing
untested behavior to the user as accepted. Live Claude, Isaac, Agibot, GPU, and
physical-robot validation remain out of scope for this preflight unless the
execution owner explicitly broadens it.

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
