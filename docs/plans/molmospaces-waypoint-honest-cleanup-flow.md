# MolmoSpaces Waypoint-Honest Cleanup Flow

**Status:** Proposed source plan
**Created:** 2026-05-11
**Source:** Codex MolmoSpaces demo review, waypoint-prior discussion, real-robot
contract alignment preflight
**Workflow:** Pre-GSD plan. Ingest or pass to `gsd-plan-phase` before
implementation.

## Problem

The current `molmo_cleanup_realworld` Codex demo proves that a coding agent can
drive the ADR-0003 public cleanup tools without private generated-mess truth,
but the resulting behavior is visually confusing. The agent receives public
`inspection_waypoints`, follows the current instruction to sweep rooms, and can
produce a report where many `observe` steps happen before any `pick` or
`place`.

That behavior is contract-safe, but it reads like the robot may have been given
a cleanup oracle or a batch plan. Before moving into
`docs/plans/molmospaces-real-robot-contract-alignment.md`, the demo should make
the waypoint boundary and cleanup policy easier to audit:

- inspection waypoints are static map/fixture coverage scaffolding, not mess
  hints;
- movable objects are still discovered only through runtime observations;
- the agent should prefer a local cleanup loop over a full up-front survey;
- the report should show a natural object-level or room-level sequence.

## Goal

Make the current MolmoSpaces coding-agent cleanup demo satisfying enough to
serve as the baseline for real-robot contract alignment.

The desired primary flow is:

```text
metric_map / fixture_hints
-> choose an unvisited waypoint or current-room scan
-> navigate_to_waypoint
-> observe
-> inspect and enqueue visible cleanup candidates
-> pick one candidate
-> navigate_to_receptacle
-> place or place_inside
-> observe current room/fixture area
-> continue from the updated worklist and unvisited-waypoint set
```

This phase should keep the public/private boundary unchanged while improving
agent policy, worklist state, report readability, and checker evidence.

## Decisions Locked

- `inspection_waypoints` may remain a public static-map coverage scaffold in
  this phase.
- `inspection_waypoints` must not be described as generated from mess, target
  objects, acceptable destinations, or private scoring truth.
- The demo should not require a live ROS/Nav2 stack.
- The demo should not require OpenClaw; Codex-only acceptance is enough.
- The first implementation should stay synchronous: observations happen when
  the agent explicitly calls `observe` at a waypoint, object, receptacle, or
  post-place location.
- Asynchronous route perception during navigation is deferred to `TODOS.md`.

## Behavior Model

Add or document explicit cleanup-agent state rather than relying on trace order:

- observed handles have states such as `observed`, `pending`,
  `navigating_to_object`, `held`, `placed`, `skipped`, `stale`, or
  `needs_reobserve`;
- waypoints have states such as `unvisited`, `visited`, and optionally
  `reobserve_recommended`;
- rooms have enough derived state to show whether they are unvisited,
  partially scanned, scanned, or have pending cleanup candidates.

When the robot is holding an object, the policy should normally finish that
delivery before cleaning anything else. It may record new observations after
arrival, but it should not interrupt a held-object delivery to pick a different
object.

After placing an object in room B, the policy should observe the current
room/fixture area before blindly returning to room A. The next action should be
chosen from the combined state of pending observed objects, unvisited waypoints,
and current location, not from a fixed "return to origin" rule.

## Public Contract And Skill Changes

Update the MCP/tool instructions and the real-world cleanup skill so agents
understand the intended loop:

- `metric_map` should say waypoints are static inspection coverage candidates
  derived from public map/fixture information.
- The instruction should prefer local cleanup after each useful observation
  instead of requiring a full sweep before manipulation.
- `fixture_hints` should remain the source of static receptacle/affordance
  hints, not runtime object observations.
- `observe` should remain the only source of new `observed_*` movable-object
  handles in the default visible-detection path.
- If the agent reaches a receptacle to place an object, the instructions should
  encourage a post-place `observe` before selecting the next task.

## Report And Checker Changes

The report should make the behavior audit-friendly:

- show the waypoint source as `static_map_coverage`, `fixture_coverage`, or an
  equivalent honest label;
- avoid presenting all scan observations as the primary cleanup timeline when
  the real behavior is object-centric;
- show worklist/object lifecycle for observed handles where practical;
- distinguish "coverage scan" from "cleanup action" and "post-place observe";
- make it obvious whether the agent did a deliberate full survey or an
  interleaved cleanup loop.

Add an opt-in checker mode that can require the new readability contract for
Codex demo review. The checker should not make semantic restoration stricter
than the existing private scorer; it should verify evidence shape and policy
honesty.

## Implementation Sketch

- Adjust `RealWorldMolmoCleanupMCPServer._augment_response()` guidance for
  `metric_map`, `fixture_hints`, and possibly manipulation responses.
- Update `skills/molmo-realworld-cleanup/SKILL.md` with the waypoint-honest
  local cleanup loop.
- Add a lightweight worklist/lifecycle summary to `agent_view.json` or
  `run_result.json` using existing trace and observed-handle data where
  possible.
- Update the report renderer to surface scan/cleanup/post-place roles without
  cloning the visual core.
- Extend `scripts/check_molmo_realworld_cleanup_result.py` with an optional
  flag for waypoint-honest agent behavior.
- Add focused tests for instruction text, worklist/lifecycle serialization,
  report labels, and checker enforcement.
- Run one Codex-only MolmoSpaces demo as local evidence if tooling and network
  policy allow it.

## Non-Goals

- Do not implement Nav2, EasyNav, or a real robot backend.
- Do not add asynchronous in-transit perception events during navigation.
- Do not expose private generated mess objects, target counts, acceptable
  destination sets, or `is_misplaced` labels.
- Do not remove `inspection_waypoints`; clarify and constrain their meaning.
- Do not require OpenClaw or Claude Code for acceptance.
- Do not claim planner-backed manipulation unless existing proof gates already
  support that claim.
- Do not redesign the report renderer from scratch.

## Acceptance Criteria

- The plan and docs clearly state that inspection waypoints are static
  map/fixture coverage scaffolding, not mess or cleanup hints.
- The Codex-facing skill and MCP instructions prefer
  `navigate -> observe -> clean visible candidate(s) -> post-place observe`
  over an up-front all-waypoint survey.
- `run_result.json` or `agent_view.json` includes enough lifecycle/worklist
  information to explain why the agent chose the next object or waypoint.
- `report.html` labels waypoint scans, cleanup actions, and post-place
  observations clearly enough for a human reviewer to tell whether behavior was
  interleaved or survey-first.
- The checker has an opt-in waypoint-honesty/readability gate.
- Existing ADR-0003 public/private leak tests and clean-agent checker behavior
  continue to pass.
- At least one Codex-only demo artifact is produced for review, or the exact
  local/tooling blocker is recorded.

## Verification Plan

- Focused tests for `RealWorldMolmoCleanupMCPServer` instruction payloads.
- Focused tests for observed-handle lifecycle/worklist serialization.
- Report tests for waypoint-source labels and scan/cleanup/post-place grouping.
- Checker tests for the optional waypoint-honesty gate.
- Run the relevant non-OpenClaw focused test set through the repo-local
  `.venv/` using `uv`/the standalone pytest wrapper.
- Local Codex demo run using `just code::codex` style full permissions when
  available and allowed by the current network.

## GSD Handoff

This is a single coherent gap phase before
`molmospaces-real-robot-contract-alignment`.

Preferred handoff:

```text
gsd-ingest-docs --manifest <manifest including this plan> --mode merge
gsd-plan-phase <created-or-existing-phase> --prd docs/plans/molmospaces-waypoint-honest-cleanup-flow.md
```

If a matching roadmap phase already exists, skip ingest and run:

```text
gsd-plan-phase <phase> --prd docs/plans/molmospaces-waypoint-honest-cleanup-flow.md
```

The stop condition is a Codex-reviewable cleanup artifact whose report makes
the waypoint prior, object discovery, and cleanup sequence clear without
claiming real-robot navigation or manipulation capability.

## Follow-Up

After this phase, proceed to
`docs/plans/molmospaces-real-robot-contract-alignment.md`.

Async route perception is intentionally parked in `TODOS.md`; it should become
a later phase only after the synchronous waypoint-honest loop is stable.
