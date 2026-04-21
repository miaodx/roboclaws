## Probe 1 — Live-probe gate (container → host routing)

- **Command**: `docker exec openclaw-gateway curl -sf http://host.docker.internal:18788/observe | head -c 200`
- **Outcome**: PASS
- **Response (first 200 chars)**: `{"fpv": "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAoHBwgHBgoICAgLCgoLDhgQDg0NDh0VFhEYIx8lJCIfIiEmKzcvJik0KSEiMEExNDk7Pj4+JS5ESUM8SDc9Pjv/2wBDAQoLCw4NDhwQEBw7KCIoOzs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs`
- **Docker version**: `Docker version 29.2.1, build a5c7197`
- **OS**: `Linux 6.17.0-20-generic`
- **Date**: `2026-04-21`
- **Gateway image digest**: `ghcr.io/openclaw/openclaw@sha256:7ea070b04d1e70811fe8ba15feaad5890b1646021b24e00f4795bd4587a594ed`

## Probe 2 — Dry-run end-to-end

- **Command**: `python examples/openclaw_nav_autonomous.py --scene FloorPlan201 --max-moves 50 --wall-budget 300`
- **Run dir**: `output/openclaw-autonomous/20260421T015940Z`
- **First observe at**: `+6.9s after kickoff` (pass: `< 30s`)
- **Total moves**: `4` (pass: `>= 1`)
- **terminated_by**: `done`
- **Artifacts**: `replay.gif ✓` `report.html ✓`
- **Badges**: `👁 ✓ (1)` `🚶 ✓ (4)`
- **Outcome**: PASS
- **Spend**: `$0.00` Kimi coding tier

## Probe 3 — Mid-run human interjection

- **Command shape**: start `examples/openclaw_nav_autonomous.py`, wait for the first
  completed move in `trace.jsonl`, then inject `check the overhead map and describe what's around you`
  on stdin.
- **Canonical run dir**: `output/openclaw-autonomous/probe3-midrun`
- **Trace evidence**:
  - `summary.json`: `human_messages_delivered = 1`
  - `summary.json`: `observe = 2`, `move = 5`, `done = 1`
  - `trace.jsonl`: the injected text appears on the move response as
    `human_message="check the overhead map and describe what's around you"`
  - `report.html`: the same `human_message` is rendered inline in the timeline
- **Behavioral result**: PARTIAL
- **Why partial**: transport works and the report captures the message, but the
  final agent summary in `run_result.json` still says `No human message was detected during observations`.
- **Interpretation**: the queueing / delivery path is correct; the remaining gap is
  model/runtime compliance with the instruction to acknowledge the message before `done`.

## Probe 4 — Kill Gateway mid-run

- **Command shape**: start `examples/openclaw_nav_autonomous.py`, wait for first trace
  activity, then `docker rm -f openclaw-gateway`.
- **Canonical run dir**: `output/openclaw-autonomous/probe4-kill`
- **Outcome**: PASS
- **Run result**: `terminated_by = error`
- **Final message**: `Gateway protocol error: Server disconnected without sending a response.`
- **Why it passes**: the example now catches `OpenClawUnavailable`, writes
  `run_result.json`, renders the replay artifacts, and still tears down the local sim
  cleanly instead of crashing out of the script.

## Probe 5 — Back-to-back runs against one long-lived Gateway

- **Bootstrap status**: the bootstrap script's own one-turn probe was flaky on this
  machine (`TOOLCALL[][]` instead of `PONG`), but the container still reached
  `/readyz` and served the real autonomous runs.
- **Gateway token source**: extracted from `/home/node/.openclaw/openclaw.json`
  inside the running container, then reused through `OPENCLAW_GATEWAY_TOKEN`.
- **Canonical run dirs**:
  - `output/openclaw-autonomous/probe5-run1`
  - `output/openclaw-autonomous/probe5-run2`
- **Command shape**: bootstrap once, then run
  `python examples/openclaw_nav_autonomous.py --skip-bootstrap ...` twice against the
  same container.
- **State reset evidence**:
  - After run 1, a sentinel file was created under
    `/home/node/.openclaw/workspaces/agent-0/state/sentinel.txt`
  - Before run 2 completed, that state directory was empty again
  - This confirms `OpenClawBridge.start_run()` wiped the agent workspace state at
    kickoff, which was the required leak-prevention behavior for the long-lived container path
- **Run summaries**:
  - Run 1: `observe = 1`, `move = 2`, `done = 0`, `terminated_by = wall_clock`
  - Run 2: `observe = 1`, `move = 6`, `done = 1`, `terminated_by = done`
- **Outcome**: PASS

## Probe 6 — SIGINT / Ctrl+C teardown

- **Command shape**: run the demo in its own process group, wait for first trace
  activity, then send process-group `SIGINT` to simulate terminal Ctrl+C.
- **Canonical run dir**: `output/openclaw-autonomous/probe6-sigint-pg`
- **Observed teardown**:
  - `teardown: stopping sim server`
  - `teardown: removing openclaw-gateway container`
  - `teardown: stopping stdin reader thread`
  - `teardown: stopping MultiAgentEngine`
- **Process result**: exited with code `130` after the expected `KeyboardInterrupt`
  traceback from the blocking HTTP call
- **Acceptance result**: PASS
- **Why it passes**: after the signal, port `18788` was free again within the probe
  window and the `openclaw-gateway` container was gone, so the cleanup contract held.

## Overall verdict

- **Pass**: probes 1, 2, 4, 5, 6
- **Partial**: probe 3
- **Summary**: the local-dev validation closed the architectural risks for the
  autonomous loop. Container-to-host routing works, the end-to-end loop runs, gateway
  death is converted into a structured error result, repeated runs reset workspace
  state correctly, and SIGINT teardown is reliable. The only remaining gap is that a
  delivered `human_message` is not always acknowledged faithfully by the model before
  `done`, even though the transport and replay pipeline record it correctly.
