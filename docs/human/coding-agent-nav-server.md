# Direct Coding-Agent Robot Driver

Run AI2-THOR locally and let Codex or Claude Code drive the robot through the
existing `roboclaws__observe`, `roboclaws__move`, and `roboclaws__done` MCP
tools. This path does not use the OpenClaw Gateway.

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

The `code::cc` and `code::codex` recipes start the MCP server, wait for it to come
up, register `roboclaws`, then launch Claude Code or Codex and clean up everything
on exit.

Both recipes default to full agent permissions for local demo operation:
`code::codex` uses Codex's bypass-approvals-and-sandbox mode, and `code::cc`
uses Claude Code's bypass-permissions mode. Run them only in a trusted local
checkout.

To run these demos through Kimi or MiMo without changing the machine-wide Codex
or Claude Code defaults, add optional provider overrides to the repo-local
`.env`:

```bash
ROBOCLAWS_CODEX_PROVIDER=mimo-openai
ROBOCLAWS_CODEX_MODEL=mimo-v2.5-pro

ROBOCLAWS_CLAUDE_PROVIDER=kimi-anthropic
ROBOCLAWS_CLAUDE_MODEL=kimi-k2.6
```

Supported profiles are `system`, `kimi-openai`, and `mimo-openai` for Codex,
and `system`, `kimi-anthropic`, and `mimo-anthropic` for Claude Code.
`ROBOCLAWS_CODE_AGENT_PROVIDER` and `ROBOCLAWS_CODE_AGENT_MODEL` are accepted as
shared fallbacks. The Kimi/MiMo profiles select model, base URL, API-key env
var, protocol, and `CLAUDE_CODE_SIMPLE=1` together for the launched process
only; unset variables leave the CLIs on their normal configured defaults.

The `code::cc` and `code::codex` launchers also pass the selected coding-agent
model to the MCP server as `MODEL`. That lets `observe(auto)` use the model
capability catalog:

- `mimo-v2.5-pro` and `mimo-v2.5` are text-only. They should use
  `observe_archived` for photo evidence or a configured vision bridge for
  ordinary navigation observations. `scene_objects` and `goto` are available
  only when the server is started with privileged helpers enabled.
- `mimo-v2-omni` is the MiMo image-capable route and can receive raw
  `observe` images.
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

For version-stable local runs that match the live CI agent toolchain, use the
pinned Docker wrappers instead of the machine-wide `codex` / `claude` binaries:

```bash
just code::docker-install-wrappers .tmp/coding-agent-bin
PATH="$PWD/.tmp/coding-agent-bin:$PATH" just code::cc
```

The wrapper image is `Dockerfile.coding-agents`; default package pins live in
`scripts/dev/coding_agent_toolchain.env`.

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

## Connect a Coding Agent

In another terminal from this repo:

```bash
codex mcp add roboclaws --url http://127.0.0.1:18788/mcp
```

or:

```bash
claude mcp add --transport http roboclaws http://127.0.0.1:18788/mcp
```

Then start Codex or Claude Code normally and ask it to use the tools. A good
first message is:

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
