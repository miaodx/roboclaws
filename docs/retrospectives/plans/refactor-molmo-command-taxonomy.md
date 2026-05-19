---
refactor_scope: molmo-command-taxonomy
status: DONE
accepted_severities:
  - P0
  - P1
last_verified: 2026-05-12
---

# Refactor Scope: Molmo Command Taxonomy

## Status

DONE

## Target

The operator-facing `just` command surface for MolmoSpaces cleanup reports and
checks.

## Accepted Severities

- P0: none identified.
- P1: command names imply live Codex, Claude Code, or OpenClaw agents when the
  recipe is actually a deterministic smoke or policy-labeled artifact path.
- P1: `verify::*` and `harness::*` are too close for daily operator use, making
  it hard to choose a report command aligned with
  `docs/human/molmospaces-settings.md`.

## Accepted P0/P1 Checklist

- [x] Add a `molmo::*` operator namespace that exposes `driver`, `runtime`, and
  `evidence` axes.
- [x] Preserve `verify::*` as confidence gates and `harness::*` as lower-level
  execution rigs.
- [x] Reserve `codex`, `claude`, and `openclaw` report names for live external
  agent paths; label deterministic substitutes as `mcp-smoke` or
  `openclaw-smoke`.
- [x] Update human docs and README entrypoints to prefer the new command names.
- [x] Add cheap contract coverage proving the new module is registered and the
  operator aliases map to the intended axes.

## Parked P2 / Future Ideas

- Fully automate non-interactive Codex/Claude cleanup runs once the preferred
  CLI invocation pattern is stable enough to encode without prompt pasting.
- Collapse old long `harness::molmo-realworld-*` recipe names after downstream
  docs and local operator muscle memory have moved to `molmo::*`.

## Evidence Ladder

- L0: `just --list molmo`.
- L1/L2: focused `tests/contract/dev_tools/test_verify_just_recipes.py`.
- L5 skipped: live Codex/Claude/OpenClaw validation is local operator evidence,
  not required to prove this naming refactor.

## Stop Condition

Stop when the `molmo::*` recipes are listed, the focused command-surface
contract tests pass, and docs explain which commands are smoke versus live.

## Execution Log

- 2026-05-12: Created gate for the approved command taxonomy refactor.
- 2026-05-12: Added `just/molmo.just`, registered it in the root `justfile`,
  updated README and `docs/human/molmospaces-settings.md`, and added focused
  command-surface tests.
- 2026-05-12: Evidence passed:
  - `just --list molmo`
  - `just molmo::quick-check`
  - `just molmo::cleanup driver=direct runtime=synthetic evidence=semantic seeds=7 output_dir=output/molmo/cleanup-prefix-test`
  - `./scripts/run_pytest_standalone.sh -q tests/contract/dev_tools/test_verify_just_recipes.py`
  - `.venv/bin/ruff check tests/contract/dev_tools/test_verify_just_recipes.py`
  - `.venv/bin/ruff format --check tests/contract/dev_tools/test_verify_just_recipes.py`
  - `git diff --check`
- 2026-05-12: L5 live Codex/Claude/OpenClaw report runs were not executed; those
  require local operator credentials/network/Gateway context and are explicitly
  represented by the new live commands.
