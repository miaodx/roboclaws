# 0042. Add Dry-Run Harness For Planner Proof Bundle Runner

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0037 through ADR-0040 created the private cleanup proof request manifest,
the local planner proof bundle runner, a runner `report.html`, and a checker for
that runner artifact. The operator can now assemble the commands manually, but
there is no single repo recipe that proves the full handoff from a fresh
ADR-0003 cleanup artifact to a checked runner report.

Real RBY1M/CuRobo proof execution remains a local-dev/GPU gate. The missing
repo-level architecture is a safe dry-run harness that exercises every artifact
seam without running planner probes.

## Decision

Add a `just` harness and verify gate that generate a fresh synthetic ADR-0003
cleanup artifact, run `run_molmo_planner_proof_bundle_from_requests.py` in
dry-run mode, and check the resulting runner manifest/report with
`check_molmo_planner_proof_bundle_runner_result.py`.

The recipe must not pass `--execute-probes` by default. Real proof execution and
cleanup rerun remain explicit local-dev operations.

## Consequences

- The local proof-bundle handoff becomes repeatable from a single recipe.
- CI-safe verification can catch broken request manifests, runner reports, and
  checker drift without GPU or MolmoSpaces planner execution.
- The harness still does not prove planner-backed cleanup primitives; it proves
  the command handoff is ready for a local operator to execute.
