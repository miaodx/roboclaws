# MolmoSpaces Real-World Agent MCP

**Status:** Implemented and verified 2026-05-09 under GSD Phase 16
**Created:** 2026-05-09
**Source:** `CONTEXT.md`, ADR-0003, ADR-0004, ADR-0005, ADR-0006, Phase 15 verification
**Workflow:** `hybrid-phase-pipeline`

## Problem

The repo now has two cleanup execution paths:

- current-contract agent bridge: external-agent viable, but exposes
  `scene_objects` and is explicitly not ADR-0003;
- ADR-0003 real-world harness: public/private correct, visually reviewable, and
  scaled to 10 hidden objects, but driven directly by the deterministic harness
  rather than an MCP tool surface.

That leaves the next `CONTEXT.md` gap: before running Codex, Claude Code, or
OpenClaw against ADR-0003, the repo needs an agent-facing MCP contract that
does not reintroduce the global movable-object inventory shortcut.

## Decision

Implement ADR-0006 as a new real-world MCP surface for the existing
`RealWorldCleanupContract`.

The first executable slice should:

- expose only ADR-0003 public tools through MCP;
- keep current-contract `scene_objects` out of the real-world surface;
- write the same Agent View, Private Evaluation, Score, Cleanup Trace, and
  Robot View Timeline report surfaces as Phase 14/15;
- add a deterministic MCP smoke agent that drives the real-world tool surface
  from public tool responses only;
- keep direct external Codex/Claude/OpenClaw dogfood as a later phase.

## Non-Goals

- Do not delete or rewrite the current-contract MCP bridge.
- Do not claim an external model policy has passed ADR-0003 yet.
- Do not add raw FPV-only perception.
- Do not claim planner-backed RBY1M/Franka manipulation.

## Deliverables

- ADR-0006 and this source plan.
- `.planning/phases/16-molmospaces-realworld-agent-mcp/16-01-realworld-agent-mcp-PLAN.md`.
- Real-world Molmo cleanup MCP server/factory and focused contract tests.
- A deterministic MCP smoke runner for the ADR-0003 tool surface.
- Checker support for agent-driven real-world MCP artifacts.
- `just harness::molmo-realworld-agent-mcp` and
  `just verify::molmo-realworld-agent-mcp`.
- One real MolmoSpaces/RBY1M visual evidence run that preserves all report
  views.

## Acceptance Criteria

- Real-world MCP `observe` exposes visible detections and Observed Object
  Handles only after waypoint observation.
- Real-world MCP does not register or accept `scene_objects`.
- `trace.jsonl` for the real-world MCP smoke contains `metric_map`,
  `fixture_hints`, `observe`, semantic cleanup tools, and no `scene_objects`.
- `run_result.json` records `contract=realworld_cleanup_v1`,
  `adr_0003_satisfied=true`, `agent_driven=true`, `mcp_server`, and
  `policy_uses_private_truth=false`.
- The checker can validate the real-world MCP smoke with
  `--expect-policy realworld_contract_smoke_agent`.
- The real visual report includes Agent View, Private Evaluation, Score,
  Cleanup Trace, and Robot View Timeline.

## Implementation Result

Phase 16 added a separate `molmo_cleanup_realworld` MCP server for the
ADR-0003 contract. It reuses `RealWorldCleanupContract` plus the shared cleanup
report/semantic timeline underlay, but deliberately does not expose the
current-contract `scene_objects` shortcut.

The deterministic smoke agent drives only the public MCP surface:

`metric_map -> fixture_hints -> navigate_to_waypoint -> observe -> nav/pick/nav/(open)/place -> done`

Real seed-1 evidence:

- `output/molmo-realworld-agent-mcp-harness/seed-1/run_result.json`
- `contract`: `realworld_cleanup_v1`
- `mcp_server`: `molmo_cleanup_realworld`
- `policy`: `realworld_contract_smoke_agent`
- `agent_driven`: `true`
- `adr_0003_satisfied`: `true`
- `generated_mess_count`: 10
- `mess_restoration_rate`: 0.8
- `sweep_coverage_rate`: 1.0
- `semantic_substeps`: 10
- `robot_view_steps`: 44
- robot-view PNGs: 176

Residual follow-ups from the original `CONTEXT.md` discussion remain separate:
direct Codex/Claude/OpenClaw policy dogfood against this stricter MCP surface,
an advisory model/scorer layer, raw FPV-only perception, and planner-backed
RBY1M/Franka manipulation.
