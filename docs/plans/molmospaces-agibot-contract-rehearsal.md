# MolmoSpaces Agibot Contract Rehearsal

**Status:** Proposed next Agibot integration slice
**Created:** 2026-05-21
**Source:** Agibot integration review, `CONTEXT.md`,
`vendors/agibot_sdk/CONTEXT.md`, and
`docs/plans/agibot-robot-map-9-dry-run-rehearsal.md`
**Workflow:** Pre-GSD plan. Run review/autoplan before implementation or ingest
into `.planning/` when ready.

## Problem

The current Agibot `robot_map_9` report is useful and accepted, but it does not
exercise a robot-like runtime loop in simulation through Agibot-shaped runner
semantics. Before real G2 testing, Roboclaws still needs a richer and more
realistic sim step:

- consume Agibot-shaped task and runner artifacts;
- expose the same public cleanup tool semantics that a real Agibot backend will
  support;
- drive a MolmoSpaces simulation backend for observe and waypoint navigation;
- produce report evidence that looks like an Agibot runner contract rehearsal
  while staying explicitly simulated.

This is the missing **MolmoSpaces Agibot Contract Rehearsal** layer from
`CONTEXT.md`.

## Goal

Build a MolmoSpaces-backed, non-GDK Agibot-shaped sim backend that validates the
contract before real robot testing:

- reuse `real_robot_cleanup_v1` public tool semantics where possible;
- consume Agibot-shaped preflight artifacts such as agent-view, waypoint
  sequence, and runner task inputs;
- implement simulated `observe` and `navigate_waypoint` behavior against
  MolmoSpaces;
- emit Agibot-shaped runtime artifacts and Roboclaws cleanup report evidence;
- label every result as simulated and never as physical Agibot GDK execution.

## Locked Boundary

This rehearsal is not:

- `robot_map_9` replay;
- a digital twin of the Agibot lab floor;
- a GDK wrapper;
- physical navigation proof;
- manipulation proof.

It is:

- an **Agibot-Shaped Sim Backend**;
- a MolmoSpaces-backed rehearsal of Agibot-shaped task artifacts and runner
  semantics;
- a contract and report validation step before running the same public tool
  flow against real Agibot G2 hardware.

## MVP Scope

First implementation should cover only:

1. **Agent View Export**
   Convert or generate a MolmoSpaces scene view into Agibot-shaped
   `agent_view` style artifacts. Public map and fixture fields should match the
   runner shape consumed by Roboclaws.

2. **Observe**
   Capture simulated policy observations from MolmoSpaces and write
   SDK-runner-shaped observe evidence. The result should map to the public
   `observe` tool.

3. **Navigate Waypoint**
   Execute simulated waypoint navigation in MolmoSpaces and write
   SDK-runner-shaped navigation evidence. The result should map to
   `navigate_to_waypoint`.

Manipulation remains blocked in the MVP: `pick`, `place`, `place_inside`,
`open_receptacle`, and `close_receptacle` should report `blocked_capability`.

## Provenance And Labels

All report and JSON evidence must distinguish simulation from real GDK:

- `physical_robot=false`
- `simulated=true`
- `execution_backend=molmospaces_sim`
- `navigation_backend=molmospaces_sim` or another explicit simulated backend
  label chosen during implementation
- do not use `primitive_provenance=agibot_gdk_normal_navi`
- use a separate provenance such as
  `agibot_shaped_molmospaces_sim_normal_navi` if a fine-grained primitive label
  is needed

The report should say that the rehearsal validates contract shape, stage
sequencing, and evidence plumbing. It must not claim Agibot navigation
execution or real-robot readiness by itself.

## Implementation Sketch

- Add a Roboclaws-side backend boundary for the SDK runner contract:
  `dry-run`, `molmospaces-sim`, and later `agibot-gdk`.
- Keep MolmoSpaces dependencies in Roboclaws, not in `vendors/agibot_sdk`.
- Reuse existing cleanup report components where possible, but add explicit
  section labels for "MolmoSpaces Agibot Contract Rehearsal".
- Preserve SDK-runner stage names where useful:
  `agent-view`, `observe`, `navigate-waypoint`.
- Preserve public tool mapping:
  `agent_view_export -> metric_map, fixture_hints`,
  `observe -> observe`,
  `navigate_waypoint -> navigate_to_waypoint`.
- Generate a deterministic report fixture so CI/mock tests can verify the
  contract without real MuJoCo or real GDK.

## Non-Goals

- Do not import Agibot GDK.
- Do not run `--execute`.
- Do not use real Agibot map artifacts as the MolmoSpaces scene source.
- Do not claim physical robot motion, arrival, or observation.
- Do not implement manipulation.
- Do not expose Agibot-specific public tool names to the cleanup agent.
- Do not replace the real Agibot G2 pilot. This is a preflight layer only.

## Acceptance Criteria

- A local command can run a MolmoSpaces-backed Agibot contract rehearsal and
  write a top-level report.
- The report clearly says "MolmoSpaces Agibot Contract Rehearsal".
- The run consumes Agibot-shaped preflight artifacts and emits Agibot-shaped
  runtime artifacts.
- Simulated `observe` and `navigate_waypoint` produce successful simulated
  evidence with explicit simulated backend labels.
- Manipulation tools remain blocked and visible in the report.
- The report distinguishes this layer from:
  Agibot Map Visual Dry Run, Agibot SDK Dry Run, semantic cleanup mock evidence,
  and real Agibot GDK execution.
- Focused tests prove that no real GDK import or real movement gate is required.
- Focused tests prove that no simulated result uses
  `agibot_gdk_normal_navi` provenance.

## Open Implementation Choices

- Exact CLI spelling: `--execution-backend molmospaces-sim`,
  `--runtime molmospaces-sim`, or a separate Roboclaws script.
- Whether the first runner should reuse `scripts/molmo_cleanup/` entrypoints or
  introduce a dedicated Agibot contract rehearsal script.
- Exact schema location for Agibot-shaped preflight and runtime exports.
- Whether the first MolmoSpaces scene should be a committed lightweight fixture
  or generated from an existing MolmoSpaces cleanup scenario.
