# Skill Library

Roboclaws treats reusable agent behavior as skills first. MCP tools remain the
bounded robot capability surface; skills are allowed to compose tools, call
small scripts, hold prompt strategy, and evolve after traces show repeated
behavior.

Each maintained skill has:

- `SKILL.md` for agent-facing instructions.
- `skill.json` for a lightweight manifest that humans and tests can inspect.
- Optional `scripts/` for deterministic helpers that should live outside the
  core MCP server.

## Manifest Fields

`skill.json` uses schema `roboclaws_skill_manifest_v1` and records:

- the skill name, role, status, and abstraction level;
- the MCP contract profile(s), if any;
- required, optional, and privileged tools;
- script paths owned by the skill;
- evidence outputs expected from a run;
- lifecycle notes for when to refactor the skill or promote behavior into MCP.

The default decision is: add or improve a skill. Promote behavior into MCP only
when multiple skills need the same stable capability, the IO belongs in one
profile, public/private boundaries are clear, and traces can preserve substeps.

See `docs/human/mcp-skills-and-semantic-profiles.md` for the architecture
rationale and abstraction ladder.
