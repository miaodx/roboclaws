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

## Maintained Skills

- `ai2thor-navigator`: base AI2-THOR navigation skill over the public navigation
  MCP surface.
- `capture-object-photo`: photo-capture behavior that may opt into privileged
  AI2-THOR demo helpers.
- `molmo-realworld-cleanup`: household cleanup behavior over public household
  world, manipulation, and episode capabilities.
- `codex-cleanup-harness8`: repeatable eight-case Codex cleanup regression
  grid for source and cleanup-skill changes.
- `raw-fpv-visual-labeler`: perception-only RAW-FPV frame-group labeling
  contract for visible cleanup-relevant movable objects.
- `actionable-semantic-map-conversion`: offline robot semantic-memory conversion
  into `actionable_semantic_map_snapshot_v1` for downstream household tasks.
- `scene-gaussian-map-alignment`: scene-specific alignment workflow for
  Gaussian/splat, USD/mesh, and robot semantic-map assets, with explicit evidence
  tiers and honest B1/Map12-style report labels.
- `visual-result-showcase`: post-run renderer for blog/README/demo GIFs,
  contact sheets, and visual proof artifacts from completed runs.

See `README.md` for the big-picture MCP and skill design principles, and
`docs/human/mcp-skills-and-semantic-profiles.md` for the detailed profile
reference.
