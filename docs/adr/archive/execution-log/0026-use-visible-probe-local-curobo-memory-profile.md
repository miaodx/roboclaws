# 0026. Use Visible Probe-Local CuRobo Memory Profile

Date: 2026-05-09

## Status

Accepted

## Context

Phase 34 showed that RBY1M/CuRobo execute mode reaches policy run and then
OOMs during CuRobo trajectory planning. The memory profile is now explicit:
the probe has about 9.1 GiB free at `execute_policy_run_start`, then grows to
about 9.9 GiB PyTorch reserved at the exception.

Upstream MolmoSpaces exposes several planner knobs that directly affect the
number and size of CuRobo planning tensors:

- policy `batch_size`;
- policy `max_batch_plan_attempts`;
- planner `num_trajopt_seeds`;
- planner `num_ik_seeds`;
- planner `max_attempts`;
- planner `trajopt_tsteps`;
- planner `enable_finetune_trajopt`.

The probe needs a controlled way to retry with lower memory pressure without
silently changing what evidence means.

## Decision

Add a probe-local, report-visible CuRobo memory profile for RBY1M execute
probes. The low-memory profile should reduce planning tensor growth by
overriding batch and seed counts while preserving collision avoidance by
default.

The probe should:

- expose a named low-memory profile plus explicit override fields;
- apply overrides only inside the standalone probe process;
- record requested and effective values in `run_result.json`;
- render a `CuRobo Memory Profile` report section;
- checker-gate that section when requested;
- keep strict planner-backed readiness based on actual RBY1M/CuRobo execution
  and robot-state movement, not on the mere presence of tuning.

This is not an upstream MolmoSpaces patch, dependency pin, or cleanup primitive
replacement. It is a controlled target-runtime retry surface.

## Consequences

- A successful tuned probe can be reviewed as planner-backed RBY1M/CuRobo
  execution with visible tuning provenance.
- If the tuned probe still blocks, the artifact identifies whether memory
  pressure improved, moved to a planning-failure stage, or remains an OOM.
- Future cleanup primitive replacement can depend on target-runtime evidence
  only after the report and checker make the tuning state visible.
