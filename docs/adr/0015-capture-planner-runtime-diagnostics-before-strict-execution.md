# 0015. Capture Planner Runtime Diagnostics Before Strict Execution

Date: 2026-05-09

## Status

Accepted

## Context

ADR-0014 added a strict proof gate for planner-backed manipulation. The first
local probes showed two different blockers:

- Franka `execute` mode terminated with `SIGSEGV` before emitting planner proof
  JSON.
- RBY1M config import failed with `ModuleNotFoundError: No module named
  'curobo'`.

Those failures are useful, but the artifacts need enough runtime context to
make the next local-dev fix actionable. A bare signal or missing-module message
does not show the MolmoSpaces Python environment, optional planner dependency
availability, or Python-level stack around a native crash.

## Decision

Extend the planner manipulation probe with runtime diagnostics before attempting
strict planner execution:

- Enable Python faulthandler for worker subprocesses so native crashes emit the
  active Python stack to stderr when possible.
- Record module/dependency availability for MolmoSpaces, MuJoCo, JAX/JAXLIB,
  CuRobo, Warp, and related optional planner packages.
- Render a `Runtime Diagnostics` section in the same shared-underlay planner
  probe report.
- Keep `blocked_capability` semantics unchanged. Diagnostics make blockers
  actionable; they do not satisfy planner-backed proof.

## Consequences

- Strict planner-backed execution remains gated by ADR-0014.
- Future local runs can distinguish install/dependency blockers from execution
  crashes without reading ad hoc shell logs.
- Report parity is preserved because diagnostics render through
  `roboclaws/molmo_cleanup/report.py`.
