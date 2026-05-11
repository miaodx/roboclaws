# 0040. Check Planner Proof Bundle Runner Artifacts

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0039 makes the local planner proof bundle runner write a visual
`report.html` next to `proof_bundle_run_manifest.json`. That gives local
operators a readable command handoff, but there is not yet a checker that can
fail fast when the manifest/report pair drifts.

The rest of the MolmoSpaces artifact pipeline has focused checkers for cleanup
runs and planner probes. The proof-bundle runner needs the same treatment before
real RBY1M/CuRobo proof generation, because a stale or incomplete command report
would send the operator into an expensive local run with weak evidence.

## Decision

Add a dedicated checker for planner proof bundle runner output. The checker will
accept either an output directory or `proof_bundle_run_manifest.json`, validate
the runner schema, command counts, expected proof artifact paths, and required
report sections, and optionally enforce that each expected proof run result
already exists.

The checker validates command/report integrity only. It does not replace the
strict planner probe checker for each generated proof.

## Consequences

- Dry-run bundle handoffs can be gated before local GPU execution.
- Executed bundle runs can opt into proof-output existence checks.
- Real proof success remains owned by individual planner probe artifacts and
  checkers.
