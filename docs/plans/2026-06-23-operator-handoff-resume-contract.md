---
plan_scope: operator-handoff-resume-contract
status: PREFLIGHT_READY
architecture_layer: Thin Runtime / Server Adapter, Agent Engines And Provider Profiles, MCP Capability Contract And Tools
source:
  - 2026-06-23 operator-console paused handoff steer investigation
  - intuitive-reduce-entropy
  - grill-with-docs-batch
  - agent-planning-loop
  - intuitive-preflight
---

# Operator Handoff Resume Contract

## Problem

The operator console currently has a two-state interaction model for text:

- `Goal` starts a run when no run is attached, or starts a linked `Next Goal`
  child run after a terminal parent.
- `Steer` appends a queued message to `operator_messages.jsonl` for an active
  run. The agent may read it later through MCP `check_operator_messages`.

That model is incomplete for explicit operator handoff. A live agent can be
asked to navigate to a waypoint, stop, and wait while the operator manually
adjusts the robot position. Codex CLI and OpenAI Agents SDK runners recognize
that as `operator_handoff_requested`, write `phase=paused` with
`resume_available=true`, stop the model turn, and keep the MCP server alive for
manual control. The UI still treats the run as non-terminal active state, so it
allows `Steer`. The steer message is queued, but no active agent turn remains to
call `check_operator_messages`; the message appears ignored.

The resulting surprise is product-level, not only a runner bug:

- `paused` is not terminal, so `Goal` / `Next Goal` is blocked.
- `paused` is also not a normal active autonomous run, so queued `Steer` is not
  consumed.
- `resume_available=true` suggests continuation, but the console has no
  route-specific resume action.

## Current Evidence

- Latest observed run:
  `output/operator-console/runs/20260623-103831-molmospaces-procthor-objaverse-val-0-mujoco-open-task-openai-agents-sdk-world-public-labels`
- Nested live status:
  `phase=paused`, `reason=operator_handoff_requested`,
  `resume_available=true`.
- `operator_messages.jsonl` contains a queued steer message:
  `在每个房间拍一张照片`.
- The nested `trace.jsonl` contains manual-control MCP activity but no
  `check_operator_messages` and no `done` call after the handoff.
- The MCP server process remains alive, so direct operator movement and observe
  calls work; that is not evidence that the agent has resumed.

Code evidence:

- `scripts/molmo_cleanup/run_live_codex_cleanup.py` pauses on explicit handoff
  and returns from the Codex turn.
- `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` pauses on explicit
  handoff and stops continuation attempts.
- `roboclaws/operator_console/state.py` exposes `steer_available` whenever the
  route supports steering and the run is not terminal; it does not distinguish
  paused handoff from active autonomous execution.
- `roboclaws/operator_console/interactions.py` rejects `Next Goal` for
  non-terminal runs and accepts `Steer` for non-terminal steer-capable routes.
- `roboclaws/operator_console/routes.py` has `supports_operator_steer`,
  `supports_relative_navigation_control`, `pause_supported`, and safety flags,
  but no route capability for paused-handoff resume.
- `scripts/molmo_cleanup/run_live_claude_cleanup.py` has live status fields that
  can record `resume_available`, but the current runner scan did not find the
  same explicit `operator_handoff_requested` branch. Claude Code must be
  classified rather than assumed equivalent.

## Existing Constraints

- The console is a Thin Runtime / Server Adapter. It may launch approved runs,
  show normalized state, record operator intent, and route lifecycle actions. It
  must not own cleanup/search/map-build strategy.
- `check_operator_messages` is an active-run steering checkpoint, not a generic
  follow-up queue and not a post-`done` mutation path.
- The live-agent runner boundary explicitly removed implicit continuation of
  unfinished live runs. A new resume path must be an explicit agent-owned
  handoff protocol, not a hidden runner retry.
- Shared `live_status.resume_available` is already used for provider-transient
  retry/resume status. This plan must not globally redefine that field as
  operator-handoff continuation without a migration.
- Private scorer truth, generated mess membership, acceptable destinations, and
  private manifests must not enter resume or next-goal prompt context.

## Desired Contract

The console and live-agent runners should expose three distinct operator text
states:

1. **Autonomous Active**
   - The model turn or model loop is still expected to reach future safe
     checkpoints.
   - `Steer` is available.
   - `Steer` writes `operator_messages.jsonl`.
   - The agent reads queued messages through MCP `check_operator_messages`.

2. **Paused Operator Handoff**
   - The robot MCP server is alive for direct operator control.
   - The model turn has stopped intentionally.
   - Manual control and observe are available when the route supports them.
   - Plain delayed `Steer` is not presented as the way to continue.
   - `Resume With Prompt` is available only when a route-specific runner-owned
     continuation protocol exists.

3. **Terminal Parent**
   - The run has fixed completion, failure, stop, or emergency-stop evidence.
   - `Steer` is unavailable.
   - `Goal` starts a linked `Next Goal` child run with public parent context.

The implementation should run through the full plan with `$intuitive-flow`.
Truthful paused-handoff state is the first phase, not the stopping point. The
full objective includes an explicit resume request surface and runner-owned
resume for Codex CLI and OpenAI Agents SDK, plus Claude Code classification.

## Scope

### Phase 1: Truthful Paused Handoff State

- Add a first-class derived operator state for paused handoff, based on
  `phase=paused` and `reason=operator_handoff_requested`.
- Add route/control metadata for paused-handoff resume support, defaulting to
  unsupported.
- Distinguish these booleans in console state:
  - `steer_available`
  - `resume_available`
  - `next_goal_available`
  - `relative_navigation_control_available`
  - `operator_handoff_paused`
- Preserve manual control for paused handoff when the route supports it.
- Stop exposing plain `Steer` as available during paused handoff unless a
  future runner explicitly keeps an agent loop alive and can consume
  `operator_messages.jsonl`.
- Keep terminal `Goal` / `Next Goal` behavior unchanged.
- Preserve provider-transient retry/resume status semantics outside the
  operator-handoff UI controls.

### Phase 2: Resume Request Surface

- Add a console action for paused handoff continuation. Working name:
  `Resume With Prompt`.
- The action records an auditable resume request artifact. It must not silently
  reinterpret old queued `Steer` messages as resume input.
- The action must not inject stdin into Codex, Claude, or another CLI.
- The console/server may record the request and route to a supported runner
  action, but runner-owned logic must perform the actual continuation.
- Resume prompt text is public operator intent and may include notes about the
  manual adjustment. It must not include private scorer truth.
- The resume request packet should follow the same public-only discipline as
  `next_goal_packet`.
- If a route has no runner-owned resume implementation, the request must fail
  loudly with an actionable unsupported-route response.

### Phase 3: Runner-Owned Continuation

- Codex CLI:
  - Implement paused-handoff resume as a second explicit agent turn against the
    same live MCP server and public run artifacts when trace semantics can be
    preserved.
  - Preserve traceability: resumed model work must write distinct attempt
    metadata and keep the original run's handoff/manual-control evidence
    auditable.
- OpenAI Agents SDK:
  - Implement paused-handoff resume through an explicit SDK request or
    run-state mechanism owned by the SDK runner.
  - Keep continuation attempts bounded and visible in live timing.
- Shared runner contract:
  - Do not treat resume as generic unfinished-run continuation.
  - Do not call `done` from the runner.
  - If same-run resume cannot be implemented without losing traceability, stop
    with `BLOCKED_NEEDS_DECISION` before substituting a linked child run.
- Claude Code:
  - Classify current behavior.
  - Do not advertise resume for Claude routes unless a matching runner-owned
    path is proven.

### Phase 4: UI Copy And Controls

- In normal active state, keep `Steer`.
- In paused handoff state, show manual controls and a clear paused handoff
  status.
- Show `Resume With Prompt` only when route metadata says the runner has real
  paused-handoff resume support.
- If paused handoff is not resumable, show a clear blocked resume state and keep
  Stop / Emergency Stop available where appropriate.
- Keep terminal `Goal` / `Next Goal` behavior unchanged.

## Non-Goals

- Do not turn the operator console into a task strategy layer.
- Do not add server-side cleanup/search/map-build policy.
- Do not add private evaluator truth to resume or next-goal context.
- Do not mutate terminal reports after `done`, stop, failure, or emergency stop.
- Do not add compatibility aliases such as `continue_queue.jsonl` unless a
  human explicitly requests compatibility.
- Do not make active-run `Goal` queue a future run in this slice.
- Do not use stdin injection or terminal text pasting as the resume mechanism.
- Do not globally redefine provider-transient `resume_available` semantics.
- Do not make Claude Code resume a success requirement unless its runner path
  is explicitly proven during implementation.

## Decision Classification

### Accepted Defaults

1. Full implementation is in scope; `$intuitive-flow` should not stop after
   truthful paused-handoff state unless a stop gate is hit.
2. Same-run resume is the target for Codex CLI and OpenAI Agents SDK. A linked
   child run may be proposed only after stopping for user approval; it must not
   be silently shipped under the name resume.
3. Queued `Steer` messages sent during paused handoff are not silently consumed
   by a future resume attempt.
4. Route metadata defaults to `resume_supported=false` and is enabled only by a
   proven runner-owned path.
5. Codex CLI and OpenAI Agents SDK must both satisfy the paused-handoff resume
   contract for full success. Claude Code is classification-only unless its
   runner path is proven.

### Stop Gates

1. `resume_available=true` for operator handoff must not be presented to the UI
   as a real continuation action unless a route-specific resume endpoint and
   runner path exist.
2. If same-run resume cannot preserve auditable trace/session semantics for
   Codex CLI or OpenAI Agents SDK, stop with `BLOCKED_NEEDS_DECISION` before
   substituting a linked child run.
3. If the implementation would require task strategy in the console/server,
   stop and redesign the runner-owned protocol.
4. If local/live proof cannot be run in the current environment, the work is
   `BLOCKED_NEEDS_LOCAL_VALIDATION` rather than complete.

## Acceptance Criteria

Full success requires all of these:

- A paused handoff run no longer presents delayed `Steer` as the action that
  resumes the agent.
- Manual control remains available for paused handoff routes that support
  relative navigation control.
- Terminal parents still use linked `Next Goal` behavior.
- Active autonomous runs still support MCP `check_operator_messages` steering.
- Route metadata or derived controls clearly report paused-handoff resume as
  unsupported unless a real runner path exists.
- `resume_available` used for provider-transient retry remains readable and is
  not conflated with operator-handoff UI controls.
- `Resume With Prompt` creates public-only auditable resume request evidence.
- Codex CLI and OpenAI Agents SDK implement the same paused-handoff resume
  contract, including bounded attempt metadata and preserved manual-control
  evidence.
- Claude Code is explicitly classified as supported, blocked, or out of scope,
  with route metadata matching the classification.
- Queued steer in paused handoff does not create a false expectation of agent
  response or get silently drained by resume.
- Local/live UI proof shows the robot can pause at handoff, accept manual
  control, resume with a new prompt, call task-relevant MCP tools, and either
  reach `done` or record an explicit blocked/failure reason.

## Verification Plan

Focused deterministic checks:

```bash
node --check roboclaws/operator_console/static/app.js
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console
./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_ci_live_reports.py
ruff check roboclaws/operator_console scripts/molmo_cleanup tests/unit/operator_console tests/unit/molmo_cleanup/test_ci_live_reports.py
```

Contract scenarios to cover:

- active run + steer-capable route: `Steer` available, `Next Goal` unavailable.
- paused handoff + manual-control route: manual control available, delayed
  `Steer` unavailable, resume shown only when route supports real resume.
- paused handoff + no resume support: clear blocked resume state.
- terminal parent: `Next Goal` available and autostarts linked child when
  current confirmation rules allow it.
- Codex explicit handoff: paused state does not imply delayed steer will be
  consumed; explicit resume starts a bounded agent turn.
- OpenAI Agents SDK explicit handoff: same behavior as Codex.
- Claude Code route: classified behavior has matching route metadata before
  resume is advertised.

Required local/live proof:

- Start a MolmoSpaces operator-console run with Codex CLI.
- Prompt it to navigate to the first waypoint and wait without `done`.
- Manually move/observe through the console.
- Resume with a new prompt through the explicit resume action.
- Verify the resumed agent calls task-relevant MCP tools and eventually `done`,
  or records an explicit blocked/failure reason.
- Repeat the same proof for OpenAI Agents SDK.
- Verify trace/report artifacts preserve operator intervention evidence.

## Risks

- Same-run resume may be hard for CLI-based engines without losing context or
  trace semantics.
- A server-owned resume implementation could accidentally become task strategy.
- Treating queued paused-handoff steer as resume input could surprise users and
  tests.
- Provider/session resume primitives differ across engines.
- Shared `resume_available` already has provider-transient meaning; changing it
  broadly would break unrelated status consumers.
- Physical or real-movement routes need stricter confirmation before resume.

## Recommended Implementation Order

1. Update state/API tests to encode the three-state interaction contract.
2. Add route/control metadata for paused-handoff resume support, default false.
3. Adjust state derivation and UI affordances so paused handoff is no longer
   plain active steer.
4. Add resume request API, artifact, and UI affordance with unsupported-route
   fail-loud behavior.
5. Implement Codex CLI runner-owned resume.
6. Implement OpenAI Agents SDK runner-owned resume.
7. Classify Claude Code and update route metadata/tests.
8. Run deterministic verification.
9. Run local/live UI proof for Codex CLI and OpenAI Agents SDK.
10. Stop as blocked if true same-run resume cannot meet trace semantics or if
    required local/live proof cannot run.

## Planning Loop Result

Two read-only scouts reviewed the draft:

- Entropy scout: found P0 risk from bundling truthful UI/state repair with true
  same-run runner resume, and P0 risk from overloading shared
  `resume_available`.
- Grill scout: confirmed `resume_available=true` is a false operator-handoff
  contract without a route-specific resume path, and pushed the plan to make
  the server boundary explicit.

Main-session judgment after user follow-up:

- Accept the scouts' boundary concerns, but keep full implementation in scope.
- Implement truthful paused-handoff state first as the foundation.
- Continue through explicit runner-owned resume for Codex CLI and OpenAI Agents
  SDK in the same `$intuitive-flow` execution.
- Keep Claude Code classification in scope, but not Claude resume unless proven.

## Preflight Contract

Preflight status: DRAFT

Task source: plan path plus 2026-06-23 user direction to implement the full
plan through `$intuitive-flow`, not just one slice.

Canonical source:
`docs/plans/2026-06-23-operator-handoff-resume-contract.md`

Route: durable `$intuitive-flow`

Goal: implement the full operator paused-handoff resume contract across console
state/UI/API and Codex CLI plus OpenAI Agents SDK runners, while keeping server
logic thin and preserving public/private evidence boundaries.

Scope:

- Implement truthful paused-handoff state and controls.
- Add explicit route/control metadata for paused-handoff resume support.
- Add `Resume With Prompt` API/UI/artifact support with fail-loud unsupported
  route behavior.
- Implement runner-owned paused-handoff resume for Codex CLI and OpenAI Agents
  SDK.
- Classify Claude Code route behavior and keep route metadata honest.
- Update deterministic tests and static UI checks.
- Run required local/live UI proof for Codex CLI and OpenAI Agents SDK, or mark
  the work `BLOCKED_NEEDS_LOCAL_VALIDATION`.

Non-goals:

- No server-owned robot task strategy.
- No private scorer truth or private manifests in resume context.
- No terminal report mutation after `done`, stop, failure, or emergency stop.
- No compatibility aliases unless explicitly requested.
- No stdin/terminal injection as a resume mechanism.
- No Claude Code resume requirement unless a runner-owned path is proven.

Entity budget:

- Reuse: operator console run state, route metadata, interaction artifacts,
  live runner status files, MCP `check_operator_messages`, manual control, and
  existing `Next Goal` public packet discipline.
- Remove/merge: narrow the misleading paused-handoff `Steer` affordance; do not
  remove active-run steering.
- New: route/control resume capability metadata, resume request artifact/API/UI,
  and runner attempt metadata for explicit resume. These are necessary because
  current `Steer` and `Next Goal` semantics do not represent paused handoff.
- Expansion triggers: linked-child fallback, Claude resume support, physical
  route resume, compatibility aliases, or private evidence in prompt context
  requires explicit re-approval.

Context:

- Must-read:
  - `docs/plans/2026-06-23-operator-handoff-resume-contract.md`
  - `docs/plans/operator-console-agent-interaction.md`
  - `docs/plans/refactor-live-agent-runner-boundary.md`
  - `ARCHITECTURE.md`
  - `docs/human/mcp-skills-and-semantic-profiles.md`
  - `roboclaws/operator_console/state.py`
  - `roboclaws/operator_console/interactions.py`
  - `roboclaws/operator_console/server.py`
  - `roboclaws/operator_console/routes.py`
  - `roboclaws/operator_console/static/app.js`
  - `scripts/molmo_cleanup/run_live_codex_cleanup.py`
  - `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
  - `scripts/molmo_cleanup/run_live_claude_cleanup.py`
  - `tests/unit/operator_console`
  - `tests/unit/molmo_cleanup/test_ci_live_reports.py`
- Useful:
  - `roboclaws/agents/live_runtime.py`
  - `roboclaws/agents/live_status.py`
  - `docs/human/coding-agent-nav-server.md`
  - current observed run artifacts under
    `output/operator-console/runs/20260623-103831-molmospaces-procthor-objaverse-val-0-mujoco-open-task-openai-agents-sdk-world-public-labels`
- Avoid unless needed: broad generated `output/**`, historical retrospectives,
  unrelated plans, and private evaluator artifacts.

Acceptance:

- SUCCESS: full acceptance criteria above pass, deterministic gates pass, Codex
  CLI and OpenAI Agents SDK local/live UI proof pass, and Claude Code is
  honestly classified.
- BLOCKED_NEEDS_DECISION: same-run resume cannot preserve trace semantics,
  implementation would require server-owned task strategy, linked-child fallback
  is proposed, or public/private boundary decisions need owner review.
- BLOCKED_NEEDS_LOCAL_VALIDATION: required Codex CLI or OpenAI Agents SDK
  local/live UI proof cannot run in the current environment.
- INTERMEDIATE_ONLY: none unless the user explicitly accepts a checkpoint.
- No regressions: active-run `Steer`, terminal `Next Goal`, manual control,
  provider-transient retry status, and `done` terminal semantics continue to
  behave as documented.

Verification:

- Deterministic:
  - `node --check roboclaws/operator_console/static/app.js`
  - `./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console`
  - `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_ci_live_reports.py`
  - `ruff check roboclaws/operator_console scripts/molmo_cleanup tests/unit/operator_console tests/unit/molmo_cleanup/test_ci_live_reports.py`
- Integration: focused operator-console route/API tests for messages,
  next-goal, control, and resume request behavior.
- Product-run: operator-console manual flow for a MolmoSpaces open-task run.
- Local-live-manual: required Codex CLI and OpenAI Agents SDK proof described
  in the verification plan. If unavailable, the final status is blocked rather
  than complete.
- Optional: browser screenshot/video evidence for the paused handoff and resume
  UI flow.

Execution:

- Main: root supervisor keeps the goal, reviews worker output, protects scope,
  and decides complete/blocked.
- Worker: `$intuitive-flow` may delegate implementation and verification
  substeps, but the main session owns final integration and proof review.
- Worker-goal: implement this plan end to end without broadening server
  strategy or bypassing local/live proof gates.

To execute:

```text
/goal execute docs/plans/2026-06-23-operator-handoff-resume-contract.md with intuitive-flow
```

Optional tracking: none.

Approval: `LGTM`, `approve`, or `go ahead` approves this preflight; edits
request revision.

## Recommended Next Action

Execute the full plan with `$intuitive-flow` using the preflight contract above.

Shortcut: `flow full plan`

