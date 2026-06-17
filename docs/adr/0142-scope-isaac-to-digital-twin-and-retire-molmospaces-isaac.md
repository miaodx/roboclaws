# ADR-0142: Scope Isaac To Digital Twin And Retire MolmoSpaces Isaac

Status: Accepted

Date: 2026-06-15

Plan:
[`docs/plans/2026-06-15-separate-digital-twin-isaac-from-molmospaces-mainline.md`](../plans/2026-06-15-separate-digital-twin-isaac-from-molmospaces-mainline.md)

## Context

Roboclaws currently has two different Isaac-shaped histories:

- B1 / Map 12 digital twin runs in Isaac Lab and still needs active support.
- MolmoSpaces household scenes were previously explored in Isaac Lab for
  renderer, segmentation, and backend parity, but the current product and eval
  mainline uses MolmoSpaces through MuJoCo.

Keeping MolmoSpaces Isaac reachable through launch metadata, operator-console
routes, generic backend overrides, or `molmo-isaac-*` recipes creates false
support expectations. This repo has no backward-compatibility requirement for
obsolete demo surfaces.

## Decision

Scope active Isaac support to B1 / Map 12 digital twin and generic Isaac
runtime proof needed by that route.

MolmoSpaces household scenes use MuJoCo as the active backend. MolmoSpaces
Isaac support is retired rather than hidden behind compatibility routes,
generic `backend=isaaclab_subprocess` overrides, or maintainer convenience
recipes.

Public route policy:

- `world=b1-map12 backend=isaaclab` remains current.
- `world=molmospaces/... backend=mujoco` remains current.
- `world=molmospaces/... backend=isaaclab` is not a current route.

Reusable Isaac runtime/preflight helpers may remain only when they are named and
owned as generic Isaac or B1 proof. MolmoSpaces-specific Isaac recipe names and
code paths should be deleted or renamed during execution if their implementation
is still useful for B1.

Genesis remains retired from active backend and comparison support.

## Rejected Alternatives

- Keep MolmoSpaces Isaac as a hidden or maintainer-only backend. Rejected
  because hidden compatibility keeps the old support burden alive.
- Preserve `molmo-isaac-*` recipe names as convenience wrappers. Rejected
  because the names imply an active MolmoSpaces backend lane.
- Remove Isaac entirely. Rejected because B1 / Map 12 digital twin still runs
  in Isaac.
- Create a backend plugin framework for optional MolmoSpaces Isaac support.
  Rejected because the problem is stale support surface, not missing
  abstraction.

## Consequences

- Launch catalog and operator-console routes should preserve B1 Isaac and
  remove MolmoSpaces Isaac.
- Generic `agent::run` and backend override paths should not provide a
  MolmoSpaces Isaac escape hatch.
- Historical MolmoSpaces Isaac plans and reports may remain, but active docs
  must label them superseded or evidence-only.
- Tests should protect both sides of the boundary: B1 Isaac still works, and
  MolmoSpaces Isaac does not silently return.
