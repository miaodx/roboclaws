# Direct Coding-Agent Robot Driver

Run AI2-THOR locally and let Codex or Claude Code drive the robot through the
existing `roboclaws__observe`, `roboclaws__move`, and `roboclaws__done` MCP
tools. This path does not use the OpenClaw Gateway.

## Start the Server

```bash
uv sync --extra dev --extra openclaw
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
output/runs/<timestamp>/
```

Important files:

- `trace.jsonl` records every observe / move / done call.
- `run_result.json` records termination and server metrics.
- `snapshots/agent-0/` stores labeled photo PNGs plus `latest.*.png` live-view files.

To score a chair/sofa photo run:

```bash
python scripts/check_photo_task.py --run-dir output/runs/<timestamp>
```

## Notes

- Tool surface: `observe`, `observe_archived`, `move`, `scene_objects`,
  `goto`, `done`.
- `observe(label="...")` is the framing-and-archive action; the cheaper
  `observe_archived(label="...")` captures without inlining images when
  this turn does not need to see pixels.
- `scene_objects(filter_types="...")` is the room-wide object oracle —
  one call returns every object with world position, bounding box, and
  planar distance from the agent (sorted nearest-first).
- `goto(object_id, distance, face)` teleports to a reachable cell near a
  target's bbox center. Pairs with `scene_objects` for target-relative
  motion; replaces 5–10 grid-step move/rotate chains.
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
