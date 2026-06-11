# 0024. Use Probe-Local Warp Torch Compatibility Adapter

Date: 2026-05-09

## Status

Accepted

## Context

Phase 32 proved that an isolated Torch extension cache gets RBY1M/CuRobo config
import through `CuroboPickAndPlacePlannerPolicy`. Execute mode now reaches
`execute_policy_construct` and fails with:

```text
AttributeError: module 'warp' has no attribute 'torch'
```

The installed `warp-lang` package is version `1.13.0`. It exposes top-level
Torch bridge functions such as `device_from_torch`, `from_torch`, and
`stream_from_torch`, but it does not expose the older `warp.torch` namespace
that the installed CuRobo path calls in `WorldMeshCollision`.

## Decision

Add a probe-local Warp compatibility adapter before RBY1M/CuRobo policy
construction. The adapter should:

- inspect the installed Warp API shape;
- when `warp.torch` is missing but top-level `warp.device_from_torch` exists,
  attach a minimal namespace with `device_from_torch`;
- record the adapter state in runtime diagnostics and planner probe reports;
- keep the strict RBY1M/CuRobo readiness gate unchanged.

This is a probe-local compatibility adapter, not a global dependency pin or
vendor patch. It exists to determine whether the current runtime can reach
planner execution after adapting an API drift that is local to the installed
Warp/CuRobo combination.

## Consequences

- RBY1M execute-mode probes can move past the known `warp.torch` namespace
  mismatch if no deeper Warp/CuRobo incompatibility exists.
- Reports make the adapter visible so strict planner proof cannot hide runtime
  shims.
- If execution still fails, the next blocker should be recorded at a later
  worker stage without relabeling cleanup primitives.
