# MolmoSpaces Agibot Contract Rehearsal

**Status:** Implemented local evidence captured, simulated rehearsal only
**Created:** 2026-05-21
**Source:** Agibot integration review, `CONTEXT.md`,
`vendors/agibot_sdk/CONTEXT.md`, and
`docs/plans/agibot-robot-map-9-dry-run-rehearsal.md`
and `docs/plans/agibot-robot-map-9-semantic-actions-rehearsal.md`
**Workflow:** Pre-GSD plan implemented directly through `intuitive-flow`; use
this file as the evidence/handoff source unless the work is later ingested into
GSD.

## Problem

The current Agibot `robot_map_9` dry-run and semantic-actions reports are useful
and accepted confidence layers, but they do not exercise a robot-like runtime
loop in simulation through Agibot-shaped runner semantics. Before real G2
testing, Roboclaws still needs a richer and more realistic sim step:

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

The original contract rehearsal remains a lightweight contract smoke. The
current pre-hardware direction is stricter: `backend=agibot_molmospaces_sim`
should also provide a **minimal-map pre-hardware rehearsal** that starts from a
sparse/minimal map view, performs an online `semantic-map-build` sweep, writes
`runtime_metric_map.json`, and then allows `household-cleanup` to consume the
same runtime-map evidence before a real G2 session.

## Locked Boundary

This rehearsal is not:

- `robot_map_9` map/SDK dry-run replay;
- `robot_map_9` semantic cleanup mock evidence;
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

## Follow-up Slice: Cleanup Action Rehearsal

After the contract-only MVP is stable, add an explicit cleanup-action rehearsal
mode that exercises simulated pick/place semantics while keeping the confidence
claim separate from both real Agibot GDK execution and planner-backed
manipulation proof.

Default behavior remains contract-only:

- `--rehearsal-mode contract` is the default.
- The run exports Agibot-shaped preflight artifacts, observes through the
  simulated policy-camera boundary, navigates one or more public waypoints, and
  reports manipulation tools as `blocked_capability`.
- Existing reports may continue to say "MolmoSpaces Agibot Contract Rehearsal".

The new action layer is opt-in:

- `--rehearsal-mode cleanup-actions` enables simulated semantic cleanup actions.
- In the pre-hardware flow, `household-cleanup` includes this cleanup-action
  rehearsal by default so local testing can exercise semantic-map-build plus
  cleanup before hardware. The evidence is still simulated and does not claim
  physical manipulation readiness.
- The run should select a small deterministic public target set from observed
  visible detections and public fixture hints.
- The action sequence should preserve public substeps:
  `navigate_to_object -> pick -> navigate_to_receptacle -> open_receptacle? ->
  place/place_inside -> close_receptacle?`.
- The report title or prominent section label should say
  "MolmoSpaces Agibot Cleanup Action Rehearsal" or an equivalent explicit
  cleanup-action label.
- Before/after images and `semantic_substeps` should show the simulated object
  movement.
- Runtime export should record the selected `rehearsal_mode`, attempted object
  count, completed object count, and final object locations.

The action layer is still not:

- real Agibot GDK execution;
- physical robot navigation or manipulation proof;
- planner-backed RBY1M/CuRobo cleanup proof;
- evidence that Agibot physical manipulation is ready.

All cleanup-action evidence must keep the simulation labels:

- `simulated=true`
- `physical_robot=false`
- `execution_backend=molmospaces_sim`
- no `agibot_gdk_normal_navi` provenance

Use a clear manipulation provenance such as `api_semantic` or
`agibot_shaped_molmospaces_sim_cleanup_action`; either is acceptable if the
report makes the simulated state-edit boundary obvious.

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
- Do not implement manipulation in the default contract-only mode.
- Do not present cleanup-action rehearsal pick/place as physical manipulation
  proof.
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
- In default `contract` mode, manipulation tools remain blocked and visible in
  the report.
- The report distinguishes this layer from:
  Agibot Map Visual Dry Run, Agibot SDK Dry Run, semantic cleanup mock evidence,
  and real Agibot GDK execution.
- Focused tests prove that no real GDK import or real movement gate is required.
- Focused tests prove that no simulated result uses
  `agibot_gdk_normal_navi` provenance.
- A separate `cleanup-actions` mode can generate a report with non-empty
  `semantic_substeps`, visible before/after object movement, and explicit
  simulated cleanup-action labels.
- Focused tests prove that `cleanup-actions` mode includes `pick` and `place`
  or `place_inside` substeps while still reporting `physical_robot=false` and
  not claiming planner-backed or Agibot GDK manipulation proof.
- `backend=agibot_molmospaces_sim` can run `semantic-map-build` through the
  pre-hardware flow with `map_mode=minimal`, generated exploration candidates,
  online observations, and `runtime_metric_map.json`.
- The pre-hardware `semantic-map-build` gate is local-run oriented, not
  CI-oriented: use `camera-labels visual_grounding=grounding-dino` or
  `camera-raw`/RAW_FPV with `runtime=molmospaces-subprocess` for the evidence
  that matters before hardware.
- `household-cleanup backend=agibot_molmospaces_sim` can consume the same
  minimal-map runtime evidence and perform simulated cleanup-action rehearsal
  before real hardware testing.

## Implementation Evidence

Captured on 2026-05-22:

- Source implementation adds default `contract` mode plus opt-in
  `cleanup-actions` mode in
  `scripts/molmo_cleanup/run_molmospaces_agibot_contract_rehearsal.py` and
  `roboclaws/molmo_cleanup/agibot_contract_rehearsal.py`.
- Local MolmoSpaces subprocess cleanup-action rehearsal report:
  `output/agibot/molmospaces-contract-rehearsal/codex-progress-molmospaces-cleanup-actions-3/report.html`.
  Evidence summary: `runtime=molmospaces-subprocess`,
  `scene_source=molmospaces_subprocess`, `simulated=true`,
  `physical_robot=false`, `execution_backend=molmospaces_sim`,
  11 robot-view steps, and one completed simulated cleanup object with
  `api_semantic` manipulation provenance.
- Live Docker-backed Codex cleanup report:
  `output/molmo/codex-agibot-contract-progress/0522_1502/seed-7/report.html`.
  Evidence summary: `policy=codex_agent`, `agent_driven=true`,
  `backend=molmospaces_subprocess`, `cleanup_status=success`, 43 robot-view
  steps, 5 semantic cleanup substeps, exact restoration 4/5, and semantic
  acceptability 5/5.
- Focused contract tests cover blocked default manipulation, cleanup-action
  substeps, simulated provenance labels, and absence of
  `agibot_gdk_normal_navi`.

This evidence does not claim real Agibot GDK execution, physical robot
navigation, planner-backed manipulation, or physical cleanup readiness.

## Intuitive-Flow Review Reconciliation

Full external `autoplan` reviewer voices were not run in this continuation
because the active agent rules do not allow spawning reviewer subagents here.
The scope-preserving review decisions accepted into this plan are:

- Use a dedicated Roboclaws command under `scripts/molmo_cleanup/` rather than
  changing the Agibot SDK runner. This keeps MolmoSpaces dependencies in
  Roboclaws and keeps `vendors/agibot_sdk/` free of simulator coupling.
- Generate Agibot-shaped preflight artifacts from the selected MolmoSpaces
  scenario by default. Do not use `robot_map_9` or fetched Agibot map artifacts
  as the MolmoSpaces scene source for this layer.
- Provide two runtime modes: a deterministic fixture runtime for CI/report
  checks without MuJoCo, and an opt-in MolmoSpaces subprocess runtime for local
  simulator rehearsal when dependencies are installed.
- Keep the public tool names backend-neutral:
  `metric_map`, `fixture_hints`, `observe`, `navigate_to_waypoint`, and blocked
  manipulation tools. Agibot-specific details belong only in preflight/runtime
  artifact provenance and report labels.
- Add focused tests for the artifact contract, simulated provenance labels,
  blocked manipulation visibility, report contents, and absence of
  `agibot_gdk_normal_navi` from simulated results.

## Resolved Implementation Choices

- CLI spelling is
  `scripts/molmo_cleanup/run_molmospaces_agibot_contract_rehearsal.py
  --runtime fixture|molmospaces-subprocess --rehearsal-mode contract|cleanup-actions`.
- The stricter pre-hardware path uses the same script with `--flow prehardware
  --task-name semantic-map-build|household-cleanup --profile
  camera-labels|camera-raw|world-labels`. Public routing uses
  `just task::run <task> direct <lane> backend=agibot_molmospaces_sim ...`.
- The first runner is a dedicated Roboclaws script under
  `scripts/molmo_cleanup/`; it does not modify the Agibot SDK runner.
- Agibot-shaped preflight artifacts live under `preflight/`; runtime exports
  live under `runtime/`.
- CI-safe evidence uses a deterministic fixture projection. Local evidence can
  opt into `--runtime molmospaces-subprocess` to use a real MolmoSpaces scene
  generated from the cleanup scenario.
- For pre-hardware confidence, prefer local `runtime=molmospaces-subprocess`
  with RAW_FPV or `camera-labels visual_grounding=grounding-dino`; fixture runs
  are only fast contract checks.
