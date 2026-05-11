# 0025. Capture RBY1M CUDA Memory Headroom Evidence

Date: 2026-05-09

## Status

Accepted

## Context

Phase 33 moved the RBY1M/CuRobo execute probe past the installed Warp API
namespace mismatch. The target path now reaches `execute_policy_run_start` and
fails inside CuRobo trajectory planning with:

```text
torch.OutOfMemoryError
```

The current artifact records the exception text, but memory pressure is still
too implicit. The report does not show stage-by-stage CUDA free/total memory,
PyTorch allocated/reserved memory, allocator configuration, or whether the
headroom problem was present before policy construction, after reset, or only
during planning.

## Decision

Record CUDA memory headroom as first-class planner probe evidence. The probe
should:

- capture CUDA/PyTorch memory diagnostics in runtime diagnostics;
- record memory snapshots around RBY1M execute stages, including policy
  construction, reset, run start, and exception/finalization paths;
- preserve environment evidence such as `PYTORCH_CUDA_ALLOC_CONF` and visible
  CUDA devices;
- render a `CUDA Memory Headroom` report section;
- checker-gate that report evidence when requested;
- leave strict RBY1M/CuRobo readiness unchanged.

This phase observes memory pressure. It does not kill GPU processes, tune
planner memory knobs, clear caches, or make an OOM-blocked artifact pass strict
planner-backed readiness.

## Consequences

- The next RBY1M/CuRobo blocker is reviewable as resource evidence rather than
  a sparse traceback.
- Follow-up phases can decide whether to tune planner batch sizes, allocator
  settings, scene complexity, or hardware requirements from structured data.
- Reports keep runtime blockers separate from cleanup-loop primitive
  provenance, so `api_semantic` cleanup moves remain visibly distinct from real
  planner-backed manipulation.
