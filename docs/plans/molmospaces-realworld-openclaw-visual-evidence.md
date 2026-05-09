# MolmoSpaces Real-World OpenClaw Visual Evidence

**Status:** Accepted for execution 2026-05-09 under GSD Phase 19
**Created:** 2026-05-09
**Source:** `CONTEXT.md`, ADR-0003, ADR-0008, ADR-0009, ADR-0010, Phase 18 verification
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 18 proved that OpenClaw Gateway can load the ADR-0003 cleanup skill,
connect to `molmo_cleanup_realworld`, call public MCP tools, avoid
`scene_objects`, and complete a synthetic cleanup run. The broader
`CONTEXT.md` plan still requires report visual parity: OpenClaw evidence should
also show the real MolmoSpaces/RBY1M visual report views, not only synthetic
before/after images.

## Decision

Implement ADR-0010 as the visual-evidence slice for OpenClaw on
`molmo_cleanup_realworld`.

This phase should:

- add a focused visual OpenClaw artifact gate that exercises
  `backend=molmospaces_subprocess`, `--include-robot`, and
  `--record-robot-views`;
- keep the external Gateway attempt separate from deterministic smoke evidence;
- run a local OpenClaw Gateway attempt against the real visual ADR-0003 server
  when the local environment is available;
- validate generated artifacts with the OpenClaw minimum checker and
  `--require-robot-views`;
- record whether the visual Gateway attempt reached only minimum viability or
  also clean cleanup success.

## Non-Goals

- Do not introduce planner-backed RBY1M/Franka pick/place.
- Do not add raw FPV-only object inference.
- Do not make advisory LLM scoring authoritative.
- Do not clone another report renderer.
- Do not use the current-contract `scene_objects` bridge.

## Deliverables

- ADR-0010 and this source plan.
- `.planning/phases/19-molmospaces-realworld-openclaw-visual-evidence/19-01-realworld-openclaw-visual-evidence-PLAN.md`.
- A focused visual OpenClaw dogfood-kit recipe and tests.
- Local Gateway artifact or an exact blocker log.
- Verification docs proving the report includes Agent View, Private
  Evaluation, Score, Semantic Substeps, and Robot View Timeline with FPV,
  chase, map, and verification images.

## Acceptance Criteria

- A deterministic OpenClaw-labeled visual kit gate writes a
  `molmospaces_subprocess` artifact with robot views and passes the checker
  with `--require-openclaw-minimum --require-robot-views`.
- The local OpenClaw Gateway command uses `skills/molmo-realworld-cleanup`,
  `ROBOCLAWS_MCP_URL=http://host.docker.internal:<port>/mcp`, and a server
  bound with `--host 0.0.0.0`.
- Any Gateway artifact is labeled `policy=openclaw_agent`,
  `contract=realworld_cleanup_v1`, `mcp_server=molmo_cleanup_realworld`, and
  `agent_driven=true`.
- The checker verifies no `scene_objects` trace events and at least one public
  ADR-0003 MCP request.
- The report includes Agent View, Private Evaluation, Score, Semantic
  Substeps, and Robot View Timeline.
- Robot View Timeline cards include FPV, chase, map, and verification PNGs.
- Phase summary/verification docs clearly state whether the Gateway artifact is
  minimum-only or also a clean cleanup success.
