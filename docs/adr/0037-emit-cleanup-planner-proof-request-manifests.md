# 0037. Emit Cleanup Planner Proof Request Manifests

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0035 lets a cleanup artifact attach multiple strict bound planner proofs
and select the matching proof per observed handle and target fixture. That
closed the artifact coverage model, but the remaining local-dev gap is
repeatable proof generation. A future operator should not have to reverse
engineer observed handles, target fixtures, planner aliases, and probe command
arguments from a finished cleanup run.

The cleanup run already knows the private observed-handle to planner-task alias
binding through `RealWorldCleanupContract.planner_observed_handle_binding`.
That binding must stay out of Agent View, but it can be recorded as private
artifact metadata for local proof generation.

## Decision

ADR-0003 cleanup artifacts will emit a private planner proof request manifest.
Each request binds one observed cleanup handle to its target fixture, source
fixture, planner-facing pickup alias, planner-facing placement alias, and the
semantic cleanup tools covered by the proof. A separate local runner will read
that manifest and build exact `scripts/run_molmo_planner_manipulation_probe.py`
commands for each ready request.

The runner defaults to a dry run so normal CI and cloud sessions do not start
expensive RBY1M/CuRobo execution accidentally. Local sessions can opt in to
`--execute-probes`, then optionally rerun the cleanup harness with the generated
proof results as a proof bundle.

## Consequences

- Cleanup artifacts become actionable proof-generation inputs rather than
  report-only evidence.
- The observed-handle to planner-alias mapping remains private artifact
  metadata and is not exposed in Agent View or public traces.
- Real multi-proof cleanup artifacts still depend on local RBY1M/CuRobo
  execution; this ADR provides the repeatable bridge to run them, not a claim
  that CI generated real proofs.
