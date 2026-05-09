# MolmoSpaces Real-World Agent Dogfood

**Status:** Accepted for execution 2026-05-09 under GSD Phase 17
**Created:** 2026-05-09
**Source:** `CONTEXT.md`, ADR-0003, ADR-0006, ADR-0007, Phase 16 verification
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 16 exposed the ADR-0003 public cleanup contract through MCP and proved it
with a deterministic smoke policy. That is not the same as dogfooding an
external coding agent against the stricter surface. The repo still needs a
repeatable way to launch an agent, give it only the ADR-0003 public-tool
instructions, and validate the resulting artifact as a clean real-world-style
Agent-Driven Cleanup Run.

## Decision

Implement ADR-0007 as the direct coding-agent dogfood slice for the
`molmo_cleanup_realworld` MCP server.

This phase should add:

- a dedicated real-world cleanup skill for external agents;
- a direct server entrypoint that prints Codex, Claude Code, and OpenClaw setup
  commands for the ADR-0003 MCP surface;
- checker support for clean real-world agent-run criteria;
- focused tests and `just` recipes for the dogfood kit;
- at least one local direct-agent evidence attempt if tooling is available.

OpenClaw Gateway dogfood can follow once the direct-agent skill/checker loop is
stable.

## Non-Goals

- Do not use the current-contract `scene_objects` bridge.
- Do not claim planner-backed RBY1M/Franka manipulation.
- Do not make an advisory LLM scorer authoritative.
- Do not require OpenClaw success in this phase.
- Do not expose private Generated Mess Set data or acceptable destination sets
  to the agent.

## Deliverables

- ADR-0007 and this source plan.
- `.planning/phases/17-molmospaces-realworld-agent-dogfood/17-01-realworld-agent-dogfood-PLAN.md`.
- `skills/molmo-realworld-cleanup/SKILL.md`.
- A direct server entrypoint for the ADR-0003 MCP surface.
- Checker/tests/recipes for clean real-world agent artifacts.
- Verification docs with local evidence and any external-agent gaps called out.

## Acceptance Criteria

- The direct entrypoint prints working setup guidance for Codex, Claude Code,
  and OpenClaw using `molmo_cleanup_realworld`.
- The real-world skill instructs agents to use `metric_map`, `fixture_hints`,
  waypoint `observe`, Observed Object Handles, and semantic cleanup tools, and
  explicitly forbids `scene_objects` and private files.
- The checker can enforce a clean ADR-0003 agent run: contract/server metadata,
  agent-driven policy, no private-truth use, no `scene_objects` trace events,
  ADR-0003 pass thresholds, semantic substeps, and required report sections.
- `just harness::molmo-realworld-agent-dogfood-kit` proves the kit with the
  synthetic backend and focused checks.
- If local external-agent tooling runs successfully, at least one Codex or
  Claude artifact is checker-validated. If not, the verification document must
  record the exact blocked command and why it is not counted as acceptance.
- Real visual report evidence must retain Agent View, Private Evaluation,
  Score, Cleanup Trace, and Robot View Timeline when robot-view capture is
  enabled.
