# Direct Coding-Agent Robot Driver

Run AI2-THOR locally and let Docker-backed Codex or Claude Code drive the robot
through the existing `roboclaws__observe`, `roboclaws__move`, and
`roboclaws__done` MCP tools. This path does not use the OpenClaw Gateway: the
MCP server and AI2-THOR stay on the host, while the coding-agent CLI runs in
the pinned `Dockerfile.coding-agents` image.

## Start the Server

```bash
uv sync --extra dev --extra openclaw
python examples/mcp/coding_agent_nav_server.py --scene FloorPlan201
```

Preferred one-command workflow:

```bash
just code::cc
just code::codex
```

Cleanup:

```bash
just mcp::down
```

The `code::cc` and `code::codex` recipes start the MCP server, wait for it to
come up, register `roboclaws` inside the Docker-backed agent runtime, then
launch Claude Code or Codex and clean up everything on exit.

Both recipes run with full agent permissions for local demo operation:
`code::codex` uses Codex's bypass-approvals-and-sandbox mode, and `code::cc`
uses Claude Code's bypass-permissions mode. Docker is required. Run them only
in a trusted local checkout.

Bare host `codex` or `claude` launches are not part of the supported path. Use
them only when a human explicitly asks for a system-CLI debugging run, and label
that run as outside the supported demo path.

To run these demos without editing user-level Codex or Claude Code config, copy
`.env.example` to `.env` and fill the keys you have. Normal users configure
keys only; command shape controls behavior. Codex defaults to the internal
multi-model aggregator when `XM_LLM_API_KEY` is present (`mify`,
`xiaomi/mimo-v2.5`, Responses API, web search disabled). `CODEX_BASE_URL`
and `CODEX_API_KEY` remain available only for explicit non-mify Codex
debugging. Claude Code prefers `MIMO_TP_KEY` when present, then `KIMI_API_KEY`,
then `XM_LLM_API_KEY` through the `mify-anthropic` profile
(`xiaomi/mimo-v2.5`, Anthropic API). It otherwise falls back to the host system
provider only off the work network.

```bash
XM_LLM_BASE_URL=https://api.llm.mioffice.cn/v1
XM_LLM_ANTHROPIC_BASE_URL=https://api.llm.mioffice.cn/anthropic  # optional
XM_LLM_API_KEY=...
MIMO_TP_KEY=...
KIMI_API_KEY=...
```

The launchers select the model, base URL, API-key env var, and protocol for the
launched process. Those choices are recipe-owned for normal runs.

The `code::cc` and `code::codex` launchers also pass the selected coding-agent
model to the MCP server as `MODEL`. That lets `observe(auto)` use the model
capability catalog:

- `mimo-v2.5-pro` is text-only. It should use
  `observe_archived` for photo evidence or a configured vision bridge for
  ordinary navigation observations. `scene_objects` and `goto` are available
  only when the server is started with privileged helpers enabled.
- `mimo-v2.5` is the MiMo image-capable route and can receive raw `observe`
  images.
- `kimi-k2.6` is image-capable, but the Claude Code Kimi coding endpoint has
  shown intermittent generic server errors when a long skill-reading context is
  immediately followed by multiple inline PNG image blocks. For batch photo
  tasks, prefer `observe_archived` unless the agent genuinely needs visual
  reasoning.

Before a long Codex visual run, check the selected OpenAI-compatible endpoint
against the current Codex CLI wire API:

```bash
just code::codex-provider-smoke
```

The coding-agent image is `Dockerfile.coding-agents`; default package pins live
in `scripts/dev/coding_agent_toolchain.env`. The public launchers call this
Docker runtime directly. The agent container then sees only `/workspace/task`
and `/workspace/skills/ai2thor-navigator`; repo-root `AGENTS.md`,
`CLAUDE.md`, `.git`, and the source tree are not mounted into the agent
context.

The same Docker isolation is task-skill driven rather than nav-specific:
`household-cleanup` live Codex/Claude runs mount only
`/workspace/skills/molmo-realworld-cleanup`, and a photo-capture coding-agent
task can mount only `/workspace/skills/capture-object-photo`. For Codex,
isolated runs also mount an empty read-only `CODEX_HOME/skills`, so
bundled/system Codex skills are not available; the task skill is read explicitly
from `../skills/<name>/SKILL.md`.

For Docker-backed Codex runs, use repo-local `.env` credentials. Host
`~/.codex` auth/config is not copied into repo workflows:

```bash
just code::codex
```

You can also manage the MCP lifecycle directly (shared with `chat::run` /
`appliance::run`; project policy is one roboclaws MCP per machine):

```bash
just mcp::up
just mcp::down
```

The server prints the MCP URL, artifact directory, and setup commands. By
default it listens on localhost:

```bash
http://127.0.0.1:18788/mcp
```

## Low-Level Debugging

For manual MCP debugging, keep the same Docker-backed runtime. In another
terminal from this repo:

```bash
scripts/dev/coding_agent_docker.sh run codex mcp add roboclaws --url http://127.0.0.1:18788/mcp
```

or:

```bash
scripts/dev/coding_agent_docker.sh run claude mcp add --transport http roboclaws http://127.0.0.1:18788/mcp
```

Then start the same Docker-backed Codex or Claude Code runtime and ask it to use
the tools. A good first message is:

```text
Read skills/ai2thor-navigator/SKILL.md. Use roboclaws__observe first, then
move with roboclaws__move. For photos, call roboclaws__observe with labels like
chair-1 or sofa-1. When finished, summarize the labels and call roboclaws__done.
```

For photo tasks, also read `skills/capture-object-photo/SKILL.md`. The photo
behavior is a skill-level composite action, not a separate MCP tool.

## Artifacts

Runs write to:

```text
output/runs/<timestamp>/
```

Important files:

- `trace.jsonl` records every observe / move / done call.
- `run_result.json` records termination and server metrics.
- `snapshots/agent-0/` stores labeled photo PNGs plus `latest.*.png` live-view files.

To score a chair/sofa photo run:

```bash
python scripts/openclaw/check_photo_task.py --run-dir output/runs/<timestamp>
```

## Notes

- Semantic contract profile: `ai2thor_navigation_v1` describes this server as
  an AI2-THOR navigation profile. Its canonical public capability tools are
  `observe`, `observe_archived`, `move`, and `done`.
- Privileged tools: `scene_objects` and `goto` are not part of the default
  server surface. Start `examples/mcp/coding_agent_nav_server.py` with
  `--allow-privileged-tools` only for photo tasks or harness iteration that
  intentionally needs simulator helpers. They are excluded from the canonical
  profile metadata and must not be described as real-robot perception or
  navigation capabilities.
- `observe(label="...")` is the framing-and-archive action; the cheaper
  `observe_archived(label="...")` captures without inlining images when
  this turn does not need to see pixels.
- `scene_objects(filter_types="...")` is the room-wide object oracle —
  one call returns every object with world position, bounding box, and
  planar distance from the agent (sorted nearest-first).
- `goto(object_id, distance, face)` teleports to a reachable cell near a
  target's bbox center. Pairs with `scene_objects` for target-relative
  motion; replaces 5–10 grid-step move/rotate chains.
- `skills/capture-object-photo/SKILL.md` owns the reusable photo flow and
  optional route-planning helper script. Keep that behavior in the skill unless
  it meets the MCP promotion rule in the root `README.md`.
- Stop the server with Ctrl-C, or let the agent call `roboclaws__done`.

## Self-improvement loop

The skill driving this MCP path was tuned via a scripted loop that
spawns `just code::cc` agents, runs them on curated tasks, captures
trace.jsonl metrics, and logs results to an append-only logbook.

```bash
just harness::list-tasks
just harness::run photo-living-room
just harness::history
```

See [`harness/README.md`](../../harness/README.md) for operational details
and [`docs/ai/harness/self-improvement-loop.md`](../ai/harness/self-improvement-loop.md)
for design rationale and the worked example that produced the current
tool surface.
