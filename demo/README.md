# demo/

Empty CWD for testing the direct coding-agent driver in isolation.

Running `claude` (or `codex`) from inside this folder means **no repo
`CLAUDE.md` / `AGENTS.md` auto-load** — the agent must rely solely on
[`../skills/ai2thor-navigator/SKILL.md`](../skills/ai2thor-navigator/SKILL.md)
as its operating doc. If the agent can drive the robot from here,
SKILL.md is genuinely self-contained.

## Run

Two terminals, both started from repo root:

```bash
# terminal 1 — start the MCP server
python examples/coding_agent_nav_server.py --scene FloorPlan201

# terminal 2 — attach an agent in this folder, NOT repo root
cd demo
claude mcp add --transport http roboclaws http://127.0.0.1:18788/mcp
claude
```

Kickoff message: "Read `../skills/ai2thor-navigator/SKILL.md`, then call
`roboclaws__observe`." Run artifacts land in
`../output/coding-agent-nav/<timestamp>/`.

## When the test fails

If the agent gets stuck or asks for context that isn't in `SKILL.md`,
**fix `skills/ai2thor-navigator/SKILL.md`** — don't add a `CLAUDE.md`
here. The point of this folder is to keep SKILL.md honest about what it
owns.
