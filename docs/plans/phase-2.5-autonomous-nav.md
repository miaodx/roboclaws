# Phase 2.5 — Autonomous OpenClaw Loop (v1: single-agent nav + human steer)

Parallel to Phase 2.4 (`PLAN.md`). Phase 2.4 measures *which images help*
under the **push** model. Phase 2.5 tests a different shape entirely —
make the agent drive. If 2.5 lands first and wins, 2.4 is re-run inside
the new architecture. They don't share code paths in v1.

## Problem Statement

Current OpenClaw integration is inverted relative to how OpenClaw is
designed. We push: every sim step, our Python loop shoves an FPV +
overhead at the agent via `/v1/chat/completions`, waits for a single
JSON action, executes it, repeats. The agent's SOUL, workspace, skill
loader, tool system, memory — the whole agentic shell — is wasted
overhead. We are paying for a full agent runtime and using it as a
glorified action picker.

Measured cost (the existing `output/coverage-openclaw-probe/` run,
2026-04-20): 55 s p50 per turn, 80 s average, latency grows 47 s → 82 s
across a 44-step run (context accumulation). Coverage run terminated at
22 % of its 200-step budget on `provider_unstable`.

**The inversion.** Let the agent drive. One kickoff prompt — *"navigate
the room for up to N moves"* — and the agent calls tools at its own
pace: `observe()`, `move(direction)`, `done(reason)`. Our Python just
babysits the AI2-THOR controller and serves tool requests over local
HTTP.

**Side channel for human steering.** A terminal user should be able to
type commands like *"draw a circle showing your path"* mid-run and have
the agent hear them without interrupting its thinking. Implementation:
a stdin thread queues human messages; the tool server attaches one
pending message as `human_message` on the next `observe()` /
`move()` response. The agent sees human notes alongside its regular
world observations. No interrupt, no extra protocol.

## Scope

### In scope (v1)

- **One agent, one scene.** Single-agent autonomous loop only. Demo
  script: `examples/openclaw_nav_autonomous.py`.
- **Three tools**: `observe` (returns FPV + overhead as base64 JPEGs +
  state JSON + pending `human_message`), `move(direction)` (advances
  sim, returns new state + pending `human_message`), `done(reason)`
  (signals end of run).
- **Local HTTP tool server** at `localhost:18788` — new module
  `roboclaws/openclaw/sim_server.py`. In-process with AI2-THOR
  controller; thread-safe mutex around `controller.step()`.
- **Docker host→host networking via `--add-host=host.docker.internal:
  host-gateway`** (default). Works on Docker 20.10+ Linux/macOS/Windows.
  `--network host` is the fallback documented in Error & Rescue only
  (Linux-only, overrides port mapping).
- **Kickoff + blocking wait** — new `OpenClawBridge.start_run(agent_id,
  prompt, wall_budget_s) → RunResult`. One `/v1/chat/completions` call
  with the kickoff prompt; blocks until agent calls `done` or wall
  budget expires (whichever first). `OPENCLAW_HTTP_TIMEOUT` raised
  to wall_budget + 60s buffer.
- **Per-run workspace reset** — `start_run` wipes the agent's
  `/home/node/.openclaw/workspaces/agent-<id>/state/` dir at kickoff so
  accumulated MEMORY from previous runs doesn't poison the new one.
  Matches the logged [fixed-session-prefix-leaks-memory] pitfall.
- **Human-interjection channel** — stdin reader thread in the example
  script pushes lines to a queue; tool server drains one per tool
  response as `human_message`.
- **Telemetry from the tool-server side** — every tool call logged to
  `output/openclaw-autonomous/<run-id>/trace.jsonl`. Every frame capture
  carries a `seen_by_agent: bool` flag (true for `/observe` responses,
  false for server-side snapshots taken during `/move`). Replay script
  reads the trace and produces `replay.gif` + `report.html`.
- **HTML report with agent-consumption hints.** `report.html` lays out
  every captured frame in a scrollable timeline. Each frame is visually
  tagged: a green border + 👁 badge means the agent saw this frame
  (came from `/observe`); a grey border + 🚶 badge means it was captured
  server-side during a `/move` and the agent never looked at it. The
  badges make the agent's observation cadence legible at a glance — you
  can see whether the agent batches moves or re-observes frequently.
- **Clean shutdown** — all internal threads `daemon=True`; the example
  wraps the full run in `try/finally` so SIGINT tears down sim server +
  Gateway container + stdin thread in order, even on Ctrl+C.
- **Skill update** — `skills/ai2thor-navigator/SKILL.md` gains a tool
  declaration block documenting the three tools and the `human_message`
  contract. Kickoff prompt references SKILL.md rather than duplicating
  the contract.
- **Wall-clock cap + hard kill.** If the blocking `/v1/chat/completions`
  call exceeds the budget, we kill it client-side and report partial
  results. Server stays up; only that single run dies.

### Not in scope (defer to v2+)

- **Multi-agent autonomous.** AI2-THOR's `step()` is single-threaded;
  two agents driving in parallel would race. Separate architectural
  phase — involves mutexing moves, interleaving semantics, or a
  real parallel-agent story.
- **Territory / coverage games under this architecture.** Single-agent
  navigation is the proof. Games inherently want turn-based mediation
  which the pull model doesn't natively provide.
- **Drawing / visualization tools** (`draw(...)`, `annotate(...)`).
  The interjection *channel* ships; the specific response *capabilities*
  (agent draws a circle, writes reasoning to a file) are v2. The
  channel is the architecture bet; the tools are polish.
- **Websocket UI, browser interface, `pause` command.** Stdin only.
- **Changes to the push-model code paths.** `bridge.step()`,
  `openclaw_demo.py`, `territory_game.py`, `coverage_game.py` are
  untouched. This phase is additive.
- **SOUL-specific tuning.** Same three tools for every SOUL; no
  per-personality tool subsets.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│   examples/openclaw_nav_autonomous.py  (single process)      │
│                                                              │
│   ┌────────────────┐    ┌───────────────┐                    │
│   │ AI2-THOR       │    │ stdin reader  │                    │
│   │ MultiAgentEng. │    │ thread        │                    │
│   └───────┬────────┘    └───────┬───────┘                    │
│           │                     │                            │
│           ▼                     ▼                            │
│   ┌──────────────────────────────────────────┐               │
│   │  SimHTTPServer  (localhost:18788)        │               │
│   │    GET  /observe → {fpv, map, state,     │               │
│   │                     human_message?}      │               │
│   │                   + trace: frame_capture │               │
│   │                     (seen_by_agent=true) │               │
│   │    POST /move    → {state,               │               │
│   │                     human_message?,      │               │
│   │                     server_warning?}     │               │
│   │                   + trace: frame_capture │               │
│   │                     (seen_by_agent=false)│               │
│   │    POST /done    → {status: "ok"}        │               │
│   │                                          │               │
│   │    (controller-mutex + human_msg queue)  │               │
│   └──────────────────────────────────────────┘               │
│                      ▲                                       │
│                      │ (HTTP from inside container,          │
│                      │  via host.docker.internal:18788)      │
└──────────────────────┼───────────────────────────────────────┘
                       │
┌──────────────────────┼───────────────────────────────────────┐
│   docker: openclaw-gateway  (--add-host host.docker.internal)│
│                      │                                       │
│   ┌──────────────────┴───────────────────┐                   │
│   │  agent-0  (workspace + SKILL.md +    │                   │
│   │           SOUL.md)                   │                   │
│   │                                      │                   │
│   │  loop: think → observe → think →     │                   │
│   │        move → ... → done             │                   │
│   │                                      │                   │
│   │  (curl http://host.docker.internal:  │                   │
│   │   18788/observe per skill tool)      │                   │
│   └──────────────────────────────────────┘                   │
└──────────────────────────────────────────────────────────────┘
                       ▲
                       │ ONE /v1/chat/completions call
                       │ with kickoff prompt
                       │ (blocks for up to wall_budget)
                       │
              ┌────────┴────────────┐
              │ OpenClawBridge      │
              │  .start_run(...)    │
              │  (wipes workspace   │
              │   state/ at start)  │
              └─────────────────────┘
```

The key inversion: one outer HTTP call (`start_run`) to the Gateway
that blocks for the whole run. Many inner HTTP calls (tool invocations)
from the Gateway *back* to the sim server. The Gateway is the client of
our local sim, not a remote we poke per step.

### Why this shape, briefly

- **Respects OpenClaw's design.** The Gateway is a coding-agent runtime;
  its performance characteristics (SOUL, skill, memory, tool calls)
  match "one long-lived agent task", not "400 cheap per-step RPCs."
- **Human interjection is cheap.** The agent polls the world via tools
  already; piggybacking notes on tool responses costs zero new plumbing.
- **Telemetry is trivial.** Every tool call is a local HTTP request we
  log on our side. No need to tail Gateway logs.
- **Fewer VLM calls could fall out naturally.** The agent may batch
  ("three `move`s without re-observing") if confident, saving tokens.
  Or it may think more per-decision (two calls per motion). Direction
  is unclear — acceptance criterion below treats latency as diagnostic,
  not pass/fail.

## Implementation Plan

### T49: Pre-build spike — de-risk two Gateway unknowns (NEW, from eng review)

**Files:** `scratch/phase25-spike.md` (throwaway), no merged code.
**Owner:** local-dev (needs running Gateway + Kimi key).
**Gate:** T50-T54 do NOT start until T49 answers both questions concretely. If
either answer invalidates the pull-model shape, escalate before writing code.

1. **Long-poll spike.** Bootstrap a gateway with `TIMEOUT_SECONDS=660`.
   Fire a single `/v1/chat/completions` call whose kickoff prompt says
   *"every 30 seconds, emit the current time in a markdown code block.
   Do this 6 times, then reply DONE."* Measure:
   - Does the call stay open for ~3 min without the Gateway timing out
     internally?
   - Does the response stream or land as one body at the end?
   - What's the observed shape when the agent is "working" with no
     upstream response yet?
   This de-risks T52's blocking-call design.
2. **Tool-format spike.** Read
   `docs/openclaw-gateway-internals.md` first. Then
   `docker exec openclaw-gateway sh -c 'cat /app/dist/skill-*.js | head -300'`
   to confirm how skills declare tools. Answer:
   - Is it free-text in SKILL.md, a YAML block, MCP manifest, or
     per-tool scripts in the workspace?
   - Does the agent invoke declared tools directly, or does the skill
     system wrap them?
   - Does tool invocation look like HTTP curl from a shell tool, or
     something else?
   This de-risks T51's declaration format AND T50's HTTP contract
   shape (if OpenClaw wraps everything in MCP, our HTTP endpoints need
   an MCP shim).
3. **Output**: a two-paragraph `scratch/phase25-spike.md` summarising
   both findings + one line per question confirming "safe to proceed
   with planned shape" OR "blocks: <what>". Not merged; deleted after
   plan update.
4. **Budget**: ~2 hours cloud-research + ~30 min local probe + one
   Kimi call (< $0.01).

### T50: `roboclaws/openclaw/sim_server.py` (tool server)

**Files:** `roboclaws/openclaw/sim_server.py`, `tests/test_sim_server.py`

1. Module exports `SimHTTPServer(engine, agent_id, host="127.0.0.1",
   port=18788)` class wrapping stdlib `http.server.ThreadingHTTPServer`.
   No new dependency; stdlib is enough.
2. Routes:
   - `GET /observe` — return JSON `{"fpv": <base64 JPEG>, "overhead":
     <base64 JPEG>, "state": {...}, "human_message": <str|null>}`.
     FPV from `engine.get_frame(agent_id)`; overhead from existing
     `render_overhead_map` (match push path so we're comparable).
     Images JPEG q=70, 320×240 — match `bridge._ndarray_to_data_url`.
     **Also writes a frame-capture event to trace.jsonl with
     `seen_by_agent: true`.**
   - `POST /move` — body `{"direction": "MoveAhead"|"MoveBack"|
     "RotateLeft"|"RotateRight"|"LookUp"|"LookDown"}`. Validated
     against `NAVIGATION_ACTIONS`. Calls `engine.step(agent_id,
     direction)` under the controller mutex. Returns new state +
     pending `human_message`.
     **After the step lands, the server captures FPV + overhead
     server-side and writes a frame-capture event to trace.jsonl with
     `seen_by_agent: false` — the response body does NOT include the
     images (no extra bytes to the agent).** This is what gives the
     HTML report smooth frame coverage between observations.
     **Spec on ordering:** `/move` before any `/observe` succeeds with
     a 200, plus a warning field `server_warning: "move before first
     observe"` in the response AND a warning event in trace.jsonl. We
     don't block the agent — the skill's kickoff prompt already says
     "start by calling observe".
   - `POST /done` — body `{"reason": "<str>"}`. Sets a `done_event`
     on the server; the kickoff call's wait-loop watches this.
     Idempotent: a second `/done` returns 200 with the same body and
     leaves the event set (no error).
     Returns `{"status": "ok"}`.
3. Thread-safety:
   - **One controller mutex** (`threading.Lock`) wraps every
     `engine.step()` and `engine.get_frame()` call. AI2-THOR is not
     reentrant.
   - **One human-message queue** (`collections.deque(maxlen=10)`).
     Stdin thread appends; tool handler `popleft()`s one per response.
     When maxlen is reached, oldest entries silently drop (deque's
     native behavior), and the server writes a `queue_overflow` event
     to trace.jsonl so the drop is auditable.
4. Lifecycle:
   - All internal threads marked `daemon=True` so a process exit
     doesn't hang on them.
   - `close()` method joins the server thread within 2 s; timeout →
     hard-stop. Callers should wrap usage in `try/finally`.
5. Logging: every incoming request + response writes one JSONL row to
   `output/openclaw-autonomous/<run-id>/trace.jsonl` with `ts`, `tool`,
   `event` (`"request"`, `"response"`, `"frame_capture"`,
   `"queue_overflow"`, `"server_warning"`), `request`, `response`,
   `wallclock_elapsed`. Frame-capture events carry
   `{"seen_by_agent": bool, "fpv": b64, "overhead": b64,
   "agent_state": {...}}`.
6. Unit tests (mocked `MultiAgentEngine`):
   - `/observe` returns 200, JSON has expected keys; trace has
     `frame_capture` event with `seen_by_agent=true`.
   - `/move` with invalid direction → 400.
   - `/move` with valid direction → engine.step called once with right
     args; returns new state; trace has `frame_capture` event with
     `seen_by_agent=false`.
   - `/move` before any `/observe` → 200 with `server_warning` field.
   - `human_message` queue drains exactly one entry per tool call;
     empty queue returns `null`.
   - Human-message queue cap: append 12, drain 12, assert only the
     last 10 surface; trace has `queue_overflow` events.
   - Concurrent `/observe` + `/move` requests serialize through the
     mutex (assert via instrumented mock).
   - `/done` sets the event; exposed as an attribute testable from
     outside. `/done` called twice → second call returns 200, event
     still set, no error.
   - `SimHTTPServer.close()` joins the server thread within 2 s even
     when there's an in-flight long-running handler.

### T51: `skills/ai2thor-navigator/SKILL.md` tool declarations

**Files:** `skills/ai2thor-navigator/SKILL.md` (append tool block)

1. **Prereq:** T49 must have produced the canonical tool declaration
   format. This task uses T49's finding, does NOT re-research.
2. Append a `## Tools` section to SKILL.md declaring `observe`, `move`,
   `done` with the base URL pattern
   `http://host.docker.internal:18788`. Each declaration includes:
   - Tool name
   - HTTP method + path
   - Request body shape (for `move` / `done`)
   - Response body shape (including `server_warning` on `/move`)
   - One-sentence usage: *"Call `observe` when you need to see the
     world. Call `move` to take a physical step. Call `done` when the
     navigation goal is achieved or you're stuck."*
3. Append a `## Human messages` block: *"Tool responses may include a
   `human_message` field. When present, it is a directive from a human
   observer. Treat it as a high-priority hint — follow it when
   compatible with your current goal, acknowledge it in your reasoning
   either way."*
   This is the **durable** record of the contract; the kickoff prompt
   (T53) just points here, doesn't duplicate.
4. Validate by bootstrapping a gateway, firing a kickoff call with a
   probe prompt, and asserting the agent actually calls `observe`
   within 30 s. **Local-dev only.**

### T52: `OpenClawBridge.start_run(...)` kickoff + block

**Files:** `roboclaws/openclaw/bridge.py`, `tests/test_bridge_start_run.py`

1. New method on `OpenClawBridge`:
   ```python
   def start_run(
       self,
       agent_id: int,
       prompt: str,
       wall_budget_s: float,
       done_event: threading.Event,
   ) -> RunResult
   ```
   - Raises `OpenClawHTTPTimeout` on client-side timeout (we use a
     per-call `timeout=wall_budget_s + 60`, NOT a mutation of
     `self._client.timeout` — the shared client's default stays at
     180 s for `step()` callers).
   - Returns `RunResult(final_message: str, wallclock_s: float,
     terminated_by: Literal["done", "wall_clock", "error"])`.
2. **Workspace reset before kickoff.** Immediately before firing the
   POST, clear `agent-<id>`'s state/ dir inside the Gateway container
   via `docker exec openclaw-gateway sh -c 'rm -rf
   /home/node/.openclaw/workspaces/agent-<id>/state/*'`. Alternative:
   if the Gateway exposes a workspace-reset endpoint (T49 to confirm),
   prefer that. This prevents memory accumulation across runs on a
   long-lived gateway (matches logged
   [fixed-session-prefix-leaks-memory] pitfall).
3. Body: one POST to `/v1/chat/completions` with `model=openclaw/
   agent-<id>` and a single user message whose content is `prompt`.
   Gateway-side `TIMEOUT_SECONDS` must match (bootstrap already accepts
   this via env — T53 sets it).
4. Blocks on the call. `done_event` is set by the sim server's `/done`
   handler. Two termination paths:
   - Happy path: agent calls `done`, Gateway returns its final message,
     `start_run` returns with `terminated_by="done"`.
   - Wall-clock path: httpx timeout fires; we return with
     `terminated_by="wall_clock"` and a best-effort partial
     `final_message` pulled from the last-known state.
5. No retry. Unlike `step()`, a long-running run has no "try again in
   8s" semantics — if the single kickoff fails, the run fails.
6. Unit tests (mocked httpx transport):
   - Happy path returns `RunResult` with `terminated_by="done"`.
   - Timeout path returns `RunResult` with
     `terminated_by="wall_clock"`.
   - HTTP 5xx surfaces as `OpenClawUnavailable` (same as today).
   - **[CRITICAL regression]** After a `start_run()` call with a
     `wall_budget_s=600` (→ 660s per-call timeout), a subsequent
     `step()` call still honors the bridge's default 180s timeout.
     Asserts we didn't accidentally mutate the shared client's
     `timeout` attribute.
   - **[Workspace reset]** Mocked docker-exec call is fired exactly
     once per `start_run` with the correct `agent-<id>` path; asserts
     the reset happens BEFORE the `/v1/chat/completions` POST.

### T53: `examples/openclaw_nav_autonomous.py`

**Files:** `examples/openclaw_nav_autonomous.py`.

1. CLI: `--scene FloorPlan201 --max-moves 200 --wall-budget 600
   --output-dir output/openclaw-autonomous/<run-id>`. All defaults.
2. Flow (in a single top-level `try/finally`; teardown runs on SIGINT):
   a. Start `MultiAgentEngine(agents=1, scene=<scene>)`.
   b. Start `SimHTTPServer` on port 18788 in a background thread.
   c. Bootstrap Gateway via `scripts/openclaw-bootstrap.sh` (see
      T53-bis for the bootstrap edits it depends on).
   d. Start stdin reader thread if `sys.stdin.isatty()` — else log
      "interjection disabled (no TTY)" and skip.
   e. Build `OpenClawBridge` + call `start_run(agent_id=0,
      prompt=<kickoff>, wall_budget_s=<wall_budget>)`.
   f. On return, render `replay.gif` + `report.html` from trace.jsonl
      (per-tool frame captures, distinguishing `seen_by_agent`) + write
      `summary.json` with stats.
   g. **`finally`**: close sim server, tear down Gateway container,
      join daemon threads. Logged at INFO so a Ctrl+C shows clean
      teardown order.
3. Kickoff prompt template (terse — SKILL.md carries the contract):
   > "You are navigating a simulated indoor room. You have up to
   > `{max_moves}` physical moves before the run ends.
   >
   > Use the `observe`, `move`, `done` tools declared in your skill.
   > Watch for `human_message` in tool responses (see skill docs).
   >
   > Start by calling `observe`. Explore the room. Report what you see
   > as you go."
4. Termination: `wall_budget_s` is the hard ceiling. If the agent
   doesn't call `done` and doesn't return, kickoff times out → report.

### T53-bis: Bootstrap script updates (broken out, was "minor" in T53)

**Files:** `scripts/openclaw-bootstrap.sh`.

The original plan called this a "minor update". It isn't — it wires 3
separate things through. Enumerated so each change is reviewable:

1. Accept `SIM_SERVER_URL` env (default
   `http://host.docker.internal:18788`); write it into the agent
   workspace as an env the skill's tool declarations can reference.
2. Add `--add-host=host.docker.internal:host-gateway` to the
   `docker run` args unconditionally (Docker ≥20.10 resolves it as
   the host on Linux; macOS/Windows Docker Desktop resolves natively).
   `--network host` stays as the documented fallback (Linux-only) in
   Error & Rescue.
3. Existing `TIMEOUT_SECONDS` is already per-call; T53 passes
   `wall_budget + 60` through.
4. Update `docs/openclaw-local.md` with the new env + the --add-host
   rationale.

Tests: not directly testable in cloud CI (depends on docker). A
manual-run checklist lives in the task's checklist; T55 step 1 exercises
the networking end-to-end.

### T54: Trace → replay + HTML report renderer

**Files:** `scripts/render_autonomous_replay.py`,
`tests/test_render_autonomous_replay.py`,
`scripts/templates/autonomous_report.html.j2`

1. Reads `trace.jsonl`. Iterates `frame_capture` events and composites
   them into `replay.gif` (same visual language as existing
   `ReplayRecorder`). Both `seen_by_agent=true` and `seen_by_agent=false`
   frames are drawn — the GIF shows smooth coverage whether the agent
   observed every step or batched.
2. Also writes `summary.json` with:
   - `total_tool_calls` (broken down by observe / move / done)
   - `moves` (count)
   - `observes_by_agent` (count of `seen_by_agent=true` captures)
   - `frames_unseen_by_agent` (count of `seen_by_agent=false`)
   - `observe_to_move_ratio` (informative — high means over-observing)
   - `wallclock_seconds`
   - `terminated_by`
   - `human_messages_delivered`
3. **`report.html` — agent-consumption aware.** A single-file HTML
   report (Jinja2 template + inline CSS, no JS framework) with:
   - Header: run metadata, summary stats, termination reason.
   - **Frame timeline**: a horizontal scrollable grid of every frame
     capture in trace order. Each frame is a composite PNG (FPV +
     overhead), displayed at ~160×120 thumbnail.
   - **Per-frame badge + border:**
     - 👁 + green 3px border = `seen_by_agent=true` (came from
       `/observe`). The agent actually saw this.
     - 🚶 + grey 2px dashed border = `seen_by_agent=false` (server-side
       snapshot during `/move`). The agent chose not to look.
   - **Hover tooltip** on each frame: timestamp, agent state (position,
     rotation), and — if the frame was seen — any `human_message`
     delivered with it.
   - **Tool-call log**: below the timeline, a monospace transcript of
     every tool call (observe/move/done), with human-message
     deliveries highlighted inline.
   - **Unseen streak warnings**: if there are ≥5 consecutive
     `seen_by_agent=false` frames, the timeline highlights that run in
     amber with a "batched without observing (N moves)" label. Lets you
     spot over-confident or under-confident strategies visually.
4. Tests:
   - Synthetic trace with both true/false frame captures → assert GIF
     is non-empty, HTML file exists, contains both 👁 and 🚶 spans.
   - Synthetic trace with 7 consecutive false frames → assert HTML
     contains the amber "batched without observing" label.
   - Summary.json has all keys, counts match trace.
   - HTML is well-formed (parseable by stdlib `html.parser`).

### T55: Local-dev validation run

**Owner:** local-dev session (real `KIMI_API_KEY`, real AI2-THOR, real
Docker). Per `CLAUDE.md § cloud vs local development` +
`feedback_live_probe_gate.md`.

1. **Pre-flight**: bootstrap gateway, manually curl `/observe` from
   inside the container to assert host-network routing works:
   `docker exec openclaw-gateway curl -sf
   http://host.docker.internal:18788/observe | head -c 200`.
   This is the **live-probe gate** for this phase. Do NOT merge until
   this returns 200 with JSON.
2. **Dry run**: `python examples/openclaw_nav_autonomous.py --scene
   FloorPlan201 --max-moves 50 --wall-budget 300`. Success criteria:
   - Agent calls `observe` within 30 s of kickoff.
   - At least one `move` before wall-clock expires.
   - Termination via `done` OR wall-clock, both acceptable.
   - `replay.gif` + `report.html` both render.
   - `report.html` opens in a browser with both 👁 and 🚶 badges
     visible (assuming the agent did at least one observe + one move).
3. **Interjection probe**: same run, but 60 s in, type
   *"check the overhead map and describe what's around you"* into
   stdin. Assert:
   - Agent's subsequent reasoning references the request.
   - Human message appears in the trace JSONL on a tool response.
   - `report.html`'s tool-call log shows the human-message delivery
     inline.
4. **Failure-mode probe**: kill the container mid-run, assert the
   client returns with `terminated_by="error"` and a clean teardown.
5. **Memory-reset probe**: run twice back-to-back against a long-lived
   gateway (`make openclaw-gateway-up` then run the example twice).
   Assert the second run's first `/observe` response shows a fresh
   agent state (no stale reasoning references from run 1). This is the
   regression guard for the 2A workspace-reset work.
6. **SIGINT probe**: during a run, Ctrl+C. Assert: teardown logs fire,
   sim server port is released within 2 s, Gateway container is
   removed.

## Test Plan

| New codepath | Test | Location | Where it runs |
|---|---|---|---|
| `SimHTTPServer /observe` happy path + frame_capture event | mocked engine, assert JSON keys + seen_by_agent=true in trace | `tests/test_sim_server.py` | cloud |
| `SimHTTPServer /move` dispatches to engine + server-snapshot | mocked engine, assert call args + seen_by_agent=false in trace | `tests/test_sim_server.py` | cloud |
| `SimHTTPServer /move` rejects invalid direction | 400 on unknown direction | `tests/test_sim_server.py` | cloud |
| `SimHTTPServer /move` before any /observe | 200 + server_warning field | `tests/test_sim_server.py` | cloud |
| `SimHTTPServer` human_message queue drain | append / drain / empty = null | `tests/test_sim_server.py` | cloud |
| `SimHTTPServer` human_message queue cap (12→10 retained) | append 12, assert oldest 2 dropped + queue_overflow events | `tests/test_sim_server.py` | cloud |
| `SimHTTPServer` controller-mutex serializes | 2 concurrent requests → serialized | `tests/test_sim_server.py` | cloud |
| `SimHTTPServer /done` sets the event + idempotent second call | set + observable from outside; second call 200 no error | `tests/test_sim_server.py` | cloud |
| `SimHTTPServer.close()` joins threads within 2 s | start + long-running handler + close | `tests/test_sim_server.py` | cloud |
| `OpenClawBridge.start_run` happy path | mocked httpx, RunResult shape | `tests/test_bridge_start_run.py` | cloud |
| `OpenClawBridge.start_run` wall-clock timeout | mocked httpx ReadTimeout → `wall_clock` | `tests/test_bridge_start_run.py` | cloud |
| `OpenClawBridge.start_run` HTTP 5xx → OpenClawUnavailable | mocked httpx 500 | `tests/test_bridge_start_run.py` | cloud |
| **[REGRESSION]** `start_run` doesn't mutate step()'s timeout | call start_run, assert subsequent step() honours 180s default | `tests/test_bridge_start_run.py` | cloud |
| `start_run` wipes workspace state/ before kickoff | mocked docker-exec, assert called once pre-POST | `tests/test_bridge_start_run.py` | cloud |
| trace → replay GIF renders (both seen_by_agent true + false) | synthetic trace → non-empty GIF, HTML exists, both 👁 and 🚶 in DOM | `tests/test_render_autonomous_replay.py` | cloud |
| HTML "batched without observing" highlight | 7 consecutive seen_by_agent=false in synthetic trace → amber label | `tests/test_render_autonomous_replay.py` | cloud |
| summary.json key/count integrity | synthetic trace → expected keys + counts | `tests/test_render_autonomous_replay.py` | cloud |
| Skill tool declarations parse | bootstrap gateway + kickoff → first `observe` within 30 s | T51 step 4 | **local-dev** |
| Host-network container → host HTTP | `docker exec ... curl /observe` returns 200 | T55 step 1 | **local-dev** |
| End-to-end 50-move run | dry run success criteria | T55 step 2 | **local-dev** |
| Human interjection delivery | trace shows human_message; agent acknowledges; HTML shows it | T55 step 3 | **local-dev** |
| Gateway crash → client termination | kill container mid-run, clean teardown | T55 step 4 | **local-dev** |
| Back-to-back runs against long-lived gateway | second run has fresh state | T55 step 5 | **local-dev** |
| SIGINT clean teardown | Ctrl+C mid-run → port free within 2s, container removed | T55 step 6 | **local-dev** |

CI `lint-and-mock` covers all cloud tests. Nothing in CI hits real
AI2-THOR or real Gateway.

## Error & Rescue Registry

| Failure | Rescue |
|---|---|
| Gateway container can't reach `host.docker.internal:18788` | T55 step 1 is the gate. Default setup uses `--add-host=host.docker.internal:host-gateway` (Docker 20.10+, cross-platform). If that doesn't resolve on user's machine, fall back to `--network host` (Linux-only) — documented in `docs/openclaw-local.md`. |
| OpenClaw skill's tool declaration format unknown | T49's tool-format spike resolves this before T51 writes anything. If T49 can't determine the format (e.g., undocumented + unreadable in /app/dist), STOP and escalate. Do NOT guess. |
| Kickoff call exceeds `wall_budget_s + 60` | `httpx.ReadTimeout` → `start_run` returns `terminated_by="wall_clock"`, partial results. Server stays up. |
| Agent never calls `done`, never calls `move` either (stuck in reasoning) | Wall-clock cap fires. No rescue — this is a quality regression, not a crash. Investigate via trace: if `tool_calls == 0`, the skill declarations didn't land. |
| Agent calls `move` with invalid direction | `/move` returns 400. Agent's next tool call will see the error; skill should have enough context to retry with a valid direction. Log as a warning. |
| Agent calls `move` before any `/observe` | 200 + `server_warning` field in response AND trace event. Non-fatal; the agent can still observe later. |
| `stdin` thread blocks on a terminal that doesn't exist (e.g., pipe) | stdin reader detects `sys.stdin.isatty() == False` on startup and doesn't start. Log "interjection disabled (no TTY)". |
| Human message queue overflows | Hard cap at 10 queued messages; oldest silently drop (`deque(maxlen=10)`) AND a `queue_overflow` event is written to trace.jsonl. Human interjection is best-effort, auditable. |
| Memory accumulation across runs on long-lived Gateway | T52 step 2: `start_run` wipes `workspaces/agent-<id>/state/` before each kickoff. Matches [fixed-session-prefix-leaks-memory]. |
| User hits Ctrl+C mid-run | `try/finally` in T53 tears down sim server, Gateway container, daemon threads. T55 step 6 tests this end-to-end. |

## Failure Modes

- **Tool-call overhead dominates.** If every "thought" is 2-3 tool
  calls and each costs a VLM round-trip inside the Gateway, the agent
  could be *slower* than the push model. Diagnostic: T55 dry run
  reports `observe_to_move_ratio` + `tool_calls_per_move` in
  summary.json. If > 3, the agent is over-thinking; revisit the
  kickoff prompt.
- **Gateway long-poll semantics unknown.** Mitigated by T49 spike
  before any code. If T49 shows the Gateway can't long-poll, T52 will
  be redesigned (Gateway-polling instead of one blocking call) before
  implementation starts.
- **Skill format risk.** Mitigated by T49 spike. T51 builds on T49's
  resolved format, not a guess.
- **Human-message piggyback can be ignored.** Nothing forces the agent
  to read `human_message`. If it consistently ignores the field, the
  interjection channel fails silently. T55 step 3 is the test; if the
  agent routinely ignores human messages, strengthen the prompt's
  language around them (bold, prefix, etc.).
- **Multi-agent deferral may bite coverage/territory use cases.** The
  games need two agents moving in some interleaving. The pull model
  doesn't natively serialize two concurrent agent loops. Scope-call
  in v1, but the eventual multi-agent story needs a different
  abstraction than "two instances of this".
- **Over-observing inflates VLM cost.** If the agent calls `/observe`
  before every move, we're paying for image ingestion on every step
  (same cost profile as the push model we're trying to escape). HTML
  report's 👁-heavy timeline makes this visible; summary.json's
  `observe_to_move_ratio` makes it measurable.

## Effort Estimate

| Task | Where | Estimate |
|---|---|---|
| T49 pre-build spike (long-poll + tool format) | local-dev | ~30 min local + ~2 hrs cloud research |
| T50 sim_server + mocked tests (incl. frame-capture metadata, queue cap, close()) | cloud | 3-4 hrs |
| T51 skill declarations (T49 already resolved format) | cloud | 1 hr + 30 min local validation |
| T52 start_run + mocked tests (incl. regression + workspace reset) | cloud | 2-3 hrs |
| T53 example script + stdin thread + SIGINT teardown | cloud | 2-3 hrs |
| T53-bis bootstrap script updates (3 enumerated changes) | cloud | 1 hr |
| T54 trace → replay.gif + report.html with consumption hints | cloud | 2-3 hrs |
| T55 local-dev validation (6 sub-probes) | local | 1-2 hrs |
| **Total** | | **~1.5 cloud days + ~1 local evening** |

No additional VLM / API cost beyond what a single 50-move dry run uses
on Kimi (roughly one coverage-probe's worth, < $1).

## What already exists (reuse, don't rebuild)

- `OpenClawBridge` — reused; `start_run` is a new method alongside
  `step()` / `ping()`. Shared HTTP client, auth, error taxonomy. The
  timeout-isolation in T52 step 1 preserves step()'s existing
  behavior.
- `MultiAgentEngine.get_frame(agent_id)`, `.step(agent_id, action)`,
  `.render_overhead_map()` — serve the sim server's responses verbatim.
- `NAVIGATION_ACTIONS` — direction validation on `/move`.
- `scripts/openclaw-bootstrap.sh` — reused with 3 enumerated additions
  in T53-bis (`SIM_SERVER_URL` env, `--add-host` flag, unchanged
  `TIMEOUT_SECONDS` wiring).
- `skills/ai2thor-navigator/SKILL.md` — extended, not rewritten.
  SOUL.md files unchanged.
- `ReplayRecorder`'s visual language (composite FPV + overhead frame
  layout) — mirrored by T54's renderer so push-mode and autonomous-mode
  GIFs are side-by-side comparable.
- `output/openclaw-*` directory convention — kept for artifacts.

## What this DOES NOT change

- `bridge.step()` path and all push-model callers (`openclaw_demo.py`,
  `territory_game.py`, `coverage_game.py`). They keep working identically.
  T52's regression test enforces this.
- Phase 2.4 plan. Its A/B experiment runs in its own architecture. If
  2.5 lands and wins the "better than push" hypothesis, 2.4's
  experiment gets re-run inside this shape in a follow-up phase.
- OpenClaw bootstrap idempotency. The tool server runs in-process with
  the example; no container lifecycle changes.

## Open Questions (pre-code research items)

1. **~~Does the OpenClaw Gateway image 2026.4.14 support long-lived
   `/v1/chat/completions` calls?~~** → Resolved by T49 spike.
2. **~~What's the exact tool declaration format in SKILL.md for Gateway
   2026.4.14?~~** → Resolved by T49 spike.
3. **~~Docker host-routing default?~~** → Pinned to
   `--add-host=host.docker.internal:host-gateway` in T53-bis step 2.
   `--network host` is the Linux-only fallback in Error & Rescue.

All three original unknowns are resolved or pinned. T49 is the
remaining gate before coding starts.

## Worktree parallelization strategy

Largely sequential: **T49 gates everything** (spike must answer the two
unknowns). After T49:
- T50 can start.
- T51 can start in parallel with T50 once T49 is done (skill
  declarations don't depend on sim_server.py's code, only on the HTTP
  contract which is in the plan).
- T52, T53, T53-bis, T54 form a serial chain behind T50 + T51.
- T55 runs after all cloud work lands.

For a single developer, the sequential chain is fine. For two parallel
worktrees, split T50 (sim_server.py) and T51 (SKILL.md) into lanes —
they touch different files, no merge conflict risk. That's the only
fan-out win.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | ISSUES_RESOLVED | 5 issues surfaced, all resolved via plan updates; 1 CRITICAL regression test added |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | N/A (no UI) |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

**UNRESOLVED:** 0 decisions pending user input — all 5 AskUserQuestions answered.
**VERDICT:** ENG CLEARED (with plan updates applied). CEO + design + DX reviews skipped per user's "single-voice engineering review" choice. Ready to implement after T49 spike answers.
