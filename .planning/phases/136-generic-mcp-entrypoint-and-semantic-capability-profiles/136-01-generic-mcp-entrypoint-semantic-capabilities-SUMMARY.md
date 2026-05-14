# Phase 136 Plan 01 Summary: Generic MCP Entrypoint Semantic Capabilities

Date: 2026-05-14
Implementation commit: `b620a44`
Source plan: `136-01-generic-mcp-entrypoint-semantic-capabilities-PLAN.md`

## What Shipped

- Added semantic MCP contract profile declarations under `roboclaws/mcp/`.
- Added built-in profiles for `ai2thor_navigation_v1` and
  `molmospaces_cleanup_v1`.
- Added a generic profile router that registers only the selected profile's
  public tool handlers.
- Added contract tests for profile validation, accelerator exclusion, privacy
  exclusion, and router registration.
- Updated the AI2-THOR navigation docs/skill and MolmoSpaces settings docs to
  distinguish task prompts, semantic capability profiles, demo recipes, and
  accelerators.

## Important Boundaries

- Existing MCP servers and demo recipes were not replaced.
- `scene_objects` and `goto` remain available on the AI2-THOR demo server, but
  the canonical `ai2thor_navigation_v1` profile excludes them from public tools.
- The MolmoSpaces cleanup profile serializes only public agent metadata and
  rejects configured private evaluator terms.
- No Docker, live Gateway, VLM key, GPU, ROS/Nav2, or real-robot validation was
  run or claimed.

## Verification

See `136-VERIFICATION.md`.
