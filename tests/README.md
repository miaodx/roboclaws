# Test Organization

The suite is currently path-compatible with the historical flat
`tests/test_*.py` layout. New organization should be expressed with pytest
markers first, then file moves after recipes and docs no longer depend on exact
paths.

## Layers

- `unit`: fast, isolated behavior through public module APIs.
- `contract`: public schemas, CLI/recipe shapes, MCP tools, reports, replay
  artifacts, and compatibility promises.
- `integration`: process, Docker, external CLI, provider, simulator, or other
  environment-bound tests.
- `regression`: known-bug or artifact-regression coverage.
- `local`: requires local GPU, paid API key, real simulator, or real Gateway.
- `slow`: CI-safe but expensive enough to keep out of tight loops.

## Common Commands

```bash
./scripts/run_pytest_standalone.sh -m unit -q
./scripts/run_pytest_standalone.sh -m contract -q
./scripts/run_pytest_standalone.sh -m regression -q
./scripts/run_pytest_standalone.sh -m "not integration" -q
```

`tests/conftest.py` auto-marks the legacy flat files. Prefer adding explicit
markers or moving files in a focused follow-up when touching a module anyway.

## Keep Or Delete

Keep tests that protect parser fallback behavior, safety defaults, public tool
contracts, trace/replay/report schemas, CLI output, or a known regression.

Merge or delete tests that only assert dataclass mechanics, copied constants,
private helper calls, or file existence without a runtime/package contract.
