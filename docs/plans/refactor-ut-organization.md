---
refactor_scope: ut-organization
status: DONE
accepted_severities:
  - P1
last_verified: 2026-05-11
---

# Refactor Scope: UT Organization

## Status

DONE

## Target

The current pytest suite under `tests/` is functionally useful but structurally
flat. The first target is test organization, not production behavior.

## Accepted Severities

- P1: Add a reliable taxonomy for running and reviewing tests by purpose without
  breaking existing explicit path entrypoints.

## Accepted P0/P1 Checklist

- [x] Create the reusable `intuitive-ut` skill from the UT best-practice research.
- [x] Register test-purpose markers with strict marker checking.
- [x] Auto-classify the existing flat `tests/test_*.py` modules into practical
  layers while preserving current paths.
- [x] Add developer-facing docs for how to choose and run each layer.
- [x] Apply one small low-signal UT cleanup as a tracer bullet.
- [x] Verify collection and representative layer runs.

## Parked P2 / Future Ideas

- Physically move test files into `tests/unit/`, `tests/contract/`,
  `tests/integration/`, and `tests/regression/` after explicit path consumers
  are updated.
- Extract shared Molmo proof/request factories once the repeated dict builders
  are handled in a dedicated slice.
- Use mutation testing only for critical pure logic once the layer split is
  stable.

## Evidence Ladder

- L0: `ruff check` / `ruff format --check` on changed files.
- L1: focused unit tests for changed unit module.
- L2: pytest collection and marker-layer smoke runs.

## Stop Condition

Stop when the marker taxonomy collects successfully, representative `unit`,
`contract`, and `regression` selections run, and low-priority physical moves are
parked.

## Execution Log

- 2026-05-11: Scope gate opened for marker-first UT organization refactor.
- 2026-05-11: Added `intuitive-ut`, pytest layer markers, `tests/conftest.py`
  auto-classification, `tests/README.md`, and `just dev::test`
  `unit`/`contract`/`regression` selectors.
- 2026-05-11: Pruned low-signal dataclass mechanics checks and merged SOUL
  initialization tests in `tests/test_skill.py`.
- 2026-05-11: Verified with:
  `uv pip install -e ".[dev]"`;
  `.venv/bin/python -c "import ai2thor; print(f'ai2thor {ai2thor.__version__} ok')"`;
  `./scripts/run_pytest_standalone.sh --collect-only -q`;
  `./scripts/run_pytest_standalone.sh --collect-only -m unit -q`;
  `./scripts/run_pytest_standalone.sh --collect-only -m contract -q`;
  `./scripts/run_pytest_standalone.sh --collect-only -m regression -q`;
  `./scripts/run_pytest_standalone.sh --collect-only -m integration -q`;
  `./scripts/run_pytest_standalone.sh -q tests/test_skill.py`;
  `./scripts/run_pytest_standalone.sh -m unit -q --durations=5`;
  `./scripts/run_pytest_standalone.sh -m contract -q --durations=5`;
  `./scripts/run_pytest_standalone.sh -m regression -q --durations=5`;
  `just dev::test regression`;
  `.venv/bin/ruff check pyproject.toml tests/conftest.py tests/test_skill.py`;
  `.venv/bin/ruff format --check tests/conftest.py tests/test_skill.py`.
