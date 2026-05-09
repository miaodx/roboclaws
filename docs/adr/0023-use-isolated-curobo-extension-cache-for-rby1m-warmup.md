# 0023. Use Isolated CuRobo Extension Cache for RBY1M Warmup

Date: 2026-05-09

## Status

Accepted

## Context

ADR-0022 made the RBY1M/CuRobo warmup blocker precise:
`output/molmo-planner-rby1m-curobo-warmup/run_result.json` records
`last_worker_stage=rby1m_config_import` after a 300-second timeout. The local
stderr shows CuRobo CUDA extension JIT messages for `geom_cu`,
`kinematics_fused_cu`, `tensor_step_cu`, and `lbfgs_step_cu`.

The global Torch extension cache now contains compiled `py311_cu128` artifacts
for most of those extensions, but `lbfgs_step_cu` has object files and a
zero-byte `lock` file without a final `.so`. No compiler process is running.
That makes the next retry ambiguous: a subsequent import may wait on stale
global cache state instead of compiling or executing.

## Decision

Add a runtime-enablement slice that lets the planner probe use an explicit
isolated `TORCH_EXTENSIONS_DIR` for RBY1M/CuRobo retries and records CuRobo
extension cache state in the artifact.

The probe should:

- accept an optional cache directory for Torch/CuRobo extensions;
- pass that directory into the worker as `TORCH_EXTENSIONS_DIR`;
- record known CuRobo extension directories, lock files, `.so` outputs, and
  file timestamps in runtime diagnostics;
- render the cache state in the planner probe report;
- checker-gate cache-preflight evidence when requested;
- keep strict RBY1M/CuRobo readiness unchanged.

Do not delete files from the global cache in this phase. If a stale global lock
is the issue, the isolated cache retry should prove that without mutating the
user's cache.

## Consequences

- The next RBY1M retry can distinguish stale global cache state from a real
  CuRobo compile/runtime failure.
- Reports will show whether all expected extension `.so` files exist and
  whether lock files are present.
- Cleanup primitive replacement remains blocked unless the isolated-cache run
  reaches execute mode and passes the strict RBY1M/CuRobo readiness gate.
