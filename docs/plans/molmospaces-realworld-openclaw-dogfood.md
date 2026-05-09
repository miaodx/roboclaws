# MolmoSpaces Real-World OpenClaw Dogfood

**Status:** Accepted for execution 2026-05-09 under GSD Phase 18
**Created:** 2026-05-09
**Source:** `CONTEXT.md`, ADR-0003, ADR-0006, ADR-0007, ADR-0008, Phase 17 verification
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 17 proves direct coding-agent dogfood on the ADR-0003 MCP surface with a
clean Claude Code synthetic run. The broader `CONTEXT.md` plan still calls for
OpenClaw policy behavior on the same stricter surface. The current-contract
OpenClaw proof cannot be reused because it depended on `scene_objects`.

## Decision

Implement ADR-0008 as the OpenClaw dogfood slice for
`molmo_cleanup_realworld`.

This phase should:

- launch OpenClaw Gateway with `skills/molmo-realworld-cleanup` and
  `ROBOCLAWS_MCP_URL` pointed at the real-world MCP server;
- label artifacts with `policy=openclaw_agent`;
- add checker support for an OpenClaw minimum viability gate on the ADR-0003
  contract;
- preserve the stricter clean-run checker for any full success;
- record Gateway evidence separately from deterministic and direct-agent
  baselines.

## Non-Goals

- Do not use the current-contract `molmo_cleanup` server.
- Do not expose `scene_objects` or private scoring truth.
- Do not require planner-backed RBY1M/Franka manipulation.
- Do not make a full clean OpenClaw run mandatory for the first viability gate.
- Do not change OpenClaw global profiles beyond what this local dogfood run
  needs.

## Deliverables

- ADR-0008 and this source plan.
- `.planning/phases/18-molmospaces-realworld-openclaw-dogfood/18-01-realworld-openclaw-dogfood-PLAN.md`.
- OpenClaw-oriented checker support for ADR-0003 artifacts.
- A reproducible command/recipe or harness note for launching Gateway against
  `molmo_cleanup_realworld`.
- Local OpenClaw evidence when Gateway can run, or an exact blocker with logs.
- Verification docs distinguishing minimum tool-use viability from clean
  cleanup success.

## Acceptance Criteria

- OpenClaw startup guidance uses `skills/molmo-realworld-cleanup`, not
  `skills/molmo-cleanup`.
- OpenClaw artifacts are labeled `policy=openclaw_agent`,
  `contract=realworld_cleanup_v1`, and `mcp_server=molmo_cleanup_realworld`.
- The checker can enforce an OpenClaw minimum: at least one public MCP tool
  call, no `scene_objects`, no private-truth flags, trace/report artifacts, and
  an explicit `agent_driven=true` result.
- If OpenClaw reaches `done`, the result is validated with either the minimum
  gate or the clean-run gate, and the verification doc records which one passed.
- If Gateway cannot complete, the verification doc records the exact command,
  logs, and blocker instead of treating the deterministic or Claude evidence as
  OpenClaw evidence.
- Any report produced by a real visual run keeps Agent View, Private
  Evaluation, Score, Cleanup Trace/Semantic Substeps, and Robot View Timeline.
