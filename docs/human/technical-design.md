# Roboclaws Technical Design

Roboclaws is a thin embodied-agent demo repo. Its current design target is
household-world cleanup, map building, open-ended household goals, and planner
proof evidence with honest public/private boundaries.

For the implementation map, read [`ARCHITECTURE.md`](../../ARCHITECTURE.md).
For domain vocabulary, read [`domain.md`](domain.md). Durable platform
decisions live in [`docs/adr/`](../adr/).

## Product Shape

Current public work is selected by a small launch catalog:

```text
surface + world + backend + intent + agent_engine + provider_profile + evidence_lane
```

The active surfaces are:

- `surface=household-world`
- `surface=planner-proof`

The household intents are:

- `intent=map-build`
- `intent=cleanup`
- `intent=open-ended`

The design goal is not to hide a whole task behind one opaque tool. Every
serious run should leave reviewable evidence: a goal contract, public MCP/tool
trace, runtime map or report artifacts, and a human-readable `report.html`.

## Household World Direction

The household stack starts from a Base Navigation Map: occupancy/free-space
context, generated exploration candidates, and public room-category hints when
available. Map-build and observations enrich that context into a Runtime Metric
Map. Downstream runs can consume either raw `runtime_metric_map.json` or the
canonical `actionable_semantic_map_snapshot_v1` package.

Cleanup separates:

- public agent-facing evidence;
- private evaluator truth;
- semantic scene mutation provenance;
- planner-backed manipulation proof;
- blocked-capability claims for work that has not been physically proven.

This is why the same report can show an agent-facing trace and private scoring
without leaking private truth into MCP profile metadata or agent inputs.

## Backend Strategy

Backends are variants under the same surface/intent contract:

- `mujoco` for standard MolmoSpaces local cleanup.
- `isaaclab` for GPU/high-fidelity scene and segmentation work.
- `agibot-gdk` for Agibot SDK map, observation, and navigation boundaries.

Backend-specific implementation details stay below the launch catalog. A new
backend should preserve public artifact names, profile requirements, and checker
semantics before claiming parity.

## Agent Strategy

Agent engines are product runtimes, not tasks:

- deterministic direct runner;
- Docker-backed Codex CLI;
- Docker-backed Claude Code;
- OpenAI Agents SDK;
- OpenClaw Gateway;
- script runner for proof/dry-run paths.

Reusable behavior belongs in skills. The maintained household cleanup skill can
drive cleanup, map-build, and open-ended household goals because the goal
contract and checker policy decide what completion means for a run.

## Current Non-Goals

- Do not reintroduce retired navigation/game surfaces as compatibility shims.
- Do not expose private generated mess truth or hidden acceptable destinations
  to agents.
- Do not claim physical manipulation readiness without planner-backed or
  robot-backed evidence.
- Do not add backend-specific public task ids when a backend variant can live
  under the existing household surface.
