# 0017. Attach Strict Planner Proof To Cleanup Artifacts

Date: 2026-05-09

## Status

Accepted

## Context

ADR-0014 created a strict proof gate for planner-backed manipulation, and
ADR-0016 made the standalone Franka proof pass locally. The ADR-0003 cleanup
loop still uses `api_semantic` primitives for object cleanup. Replacing every
cleanup `pick`/`place` primitive with a planner-backed primitive is larger than
the proof-gate work because it must map cleanup object handles, target fixtures,
and generated mess state into planner tasks.

The next useful integration step is to make cleanup artifacts carry the strict
planner proof beside the cleanup loop, without pretending the cleanup loop's
object moves were planner-backed.

## Decision

Add a planner-proof attachment to ADR-0003 cleanup artifacts:

- Accept a strict planner probe `run_result.json` as optional cleanup-run input.
- Validate the attached proof uses `status=planner_backed`,
  `strict_proof_eligible=true`, executed at least one step, and has nonzero
  robot-state movement.
- Copy proof view images into the cleanup run directory so the cleanup report is
  self-contained.
- Render an `Attached Planner-Backed Proof` panel in the shared Cleanup Artifact
  Report with proof status, qpos delta, renderer diagnostics, and initial/final
  proof views.
- Keep the cleanup artifact's object-move provenance as `api_semantic` until the
  cleanup loop itself calls planner-backed primitives.

## Consequences

- Reviewers can see ADR-0003 cleanup behavior and strict planner capability in
  one report.
- The artifact remains honest: attached proof is not the same as planner-backed
  cleanup execution.
- A later phase can replace cleanup primitives with planner-backed adapters and
  then change per-object primitive provenance.
