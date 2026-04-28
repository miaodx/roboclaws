# Direct Coding-Agent Robot Driver

Run AI2-THOR locally and let Codex or Claude Code drive the robot through the
existing `roboclaws__observe`, `roboclaws__move`, and `roboclaws__done` MCP
tools. This path does not use the OpenClaw Gateway.

## Start the Server

```bash
uv pip install -e ".[dev,openclaw]" || python -m pip install -e ".[dev,openclaw]"
python examples/coding_agent_nav_server.py --scene FloorPlan201
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

## Artifacts

Runs write to:

```text
output/coding-agent-nav/<timestamp>/
```

Important files:

- `trace.jsonl` records every observe / move / done call.
- `run_result.json` records termination and server metrics.
- `snapshots/agent-0/` stores labeled photo PNGs plus `latest.*.png` live-view files.

To score a chair/sofa photo run:

```bash
python scripts/check_photo_task.py --run-dir output/coding-agent-nav/<timestamp>
```

## Notes

- The tool surface is intentionally small: observe, move, done.
- `observe(label="...")` is the photo action.
- `observe` may include currently visible AI2-THOR object names/types, but it
  does not expose a room-wide object oracle or route planner.
- Stop the server with Ctrl-C, or let the agent call `roboclaws__done`.
