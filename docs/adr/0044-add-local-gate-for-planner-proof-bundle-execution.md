# 0044. Add Local Gate For Planner Proof Bundle Execution

Date: 2026-05-10

## Status

Accepted

## Context

The MolmoSpaces cleanup path now has a repeatable dry-run proof-bundle runner,
runner reports, runner checks, and cleanup rerun artifact tracking. The
remaining gap is operational: executing the generated bound planner probes and
rerunning cleanup with their proof outputs still requires hand-assembling a
long local command.

That hand assembly is risky because it can skip one of the strict gates:
per-proof output existence, cleanup rerun artifact existence, or the final
ADR-0003 cleanup checker that verifies planner-backed cleanup primitive and
bridge readiness.

## Decision

Add an explicit local-dev harness/verify gate for proof-bundle execution and
cleanup rerun.

The gate will:

- generate a fresh ADR-0003 synthetic cleanup artifact;
- run the proof-bundle runner with `--execute-probes` and `--rerun-cleanup`;
- require proof outputs and cleanup rerun outputs in the runner checker;
- run the ADR-0003 cleanup checker on the final cleanup rerun artifact with
  strict planner-backed cleanup primitive and bridge requirements.

This remains a local-dev gate. It is not part of the cheap CI/default verify
path because it requires the MolmoSpaces runtime, CUDA, and RBY1M/CuRobo
planner execution.

## Consequences

- Local operators get one named command for the end-to-end proof-bundle path.
- The final cleanup rerun cannot be treated as accepted until both the runner
  checker and cleanup checker pass.
- CI remains fast because the default dry-run gate stays separate from the
  local execution gate.
