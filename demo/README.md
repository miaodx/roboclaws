# demo/

Empty CWD for testing the direct coding-agent driver in isolation.

Running `claude` (or `codex`) from inside this folder means **no repo
`CLAUDE.md` / `AGENTS.md` auto-load** — the agent must rely solely on
[`../skills/ai2thor-navigator/SKILL.md`](../skills/ai2thor-navigator/SKILL.md)
as its operating doc. If the agent can drive the robot from here,
SKILL.md is genuinely self-contained.

When the pinned Docker `codex` / `claude` shims are used through
`just code::cc` or `just code::codex`, this isolation is stricter: the container
mounts a minimal `/workspace` containing only this demo folder and the
`ai2thor-navigator` skill. Repo-root `AGENTS.md`, `CLAUDE.md`, and the source
tree are not mounted into the agent container.

## Kickoff (paste this as your first message)

```
Read ../skills/ai2thor-navigator/SKILL.md, then call roboclaws__observe(label="preflight") to verify the MCP is alive. After that, wait for my actual task.
```

The `label="preflight"` step is load-bearing: it doubles as a health
check AND drops a baseline snapshot to disk so the run produces an
artifact even if the MCP later disconnects.

## Run

Two terminals, both started from repo root:

```bash
# terminal 1 — start the MCP server
python examples/mcp/coding_agent_nav_server.py --scene FloorPlan201

# terminal 2 — attach an agent in this folder, NOT repo root
cd demo
claude mcp add --transport http roboclaws http://127.0.0.1:18788/mcp
claude
```

Then paste the kickoff prompt above. Run artifacts land in
`../output/coding-agent-nav/<timestamp>/`.

## When the test fails

If the agent gets stuck or asks for context that isn't in `SKILL.md`,
**fix `skills/ai2thor-navigator/SKILL.md`** — don't add a `CLAUDE.md`
here. The point of this folder is to keep SKILL.md honest about what it
owns.
