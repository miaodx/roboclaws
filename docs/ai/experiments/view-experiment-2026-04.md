# View Experiment Decision Note

**Date:** 2026-04-24
**Status:** Superseded before the full A/B/C sweep

## Decision

The supported runtime view family is now **`map-v2+chase` only**.

`baseline` and `map-v2` are no longer supported as user-selectable runtime
modes on the main examples.

## What Changed

- `examples/openclaw_demo.py`, `examples/territory_game.py`, and
  `examples/coverage_game.py` now use a fixed three-image prompt contract:
  FPV + structured overhead + chase cam.
- The user-facing `--views` flag was removed from those main example drivers.
- `examples/view_experiment.py` now sweeps scenes, seeds, and games for the
  single supported variant instead of exposing unsupported runtime variants.

## Rationale

- The repo had already drifted toward `map-v2+chase` as the only real runtime
  path, including the shipped Phase 2.6 autonomous MCP flow.
- Reintroducing `baseline` and `map-v2` only to satisfy the old Phase 2.4
  experiment plan created code/runtime inconsistency and broke adjacent paths.
- The historical analysis tooling remains useful for archival data, but the
  product surface is no longer an active A/B experiment.

## Planning Impact

- Phase `02.4-04` is superseded rather than executed as originally written.
- `.planning/ROADMAP.md`, `.planning/STATE.md`, and `PLAN.md` now treat the
  old multi-variant study as historical context.
- Future work should assume `map-v2+chase` is the single supported view
  contract unless a new phase explicitly reopens the decision.
