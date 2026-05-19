# Phase 21 Verification

## Gates Run

```bash
./scripts/run_pytest_standalone.sh -q \
  tests/test_molmo_cleanup_advisory_scoring.py \
  tests/test_molmo_cleanup_report.py \
  tests/test_molmospaces_realworld_cleanup.py \
  tests/test_molmo_realworld_mcp_server.py \
  tests/test_check_molmo_realworld_cleanup_result.py \
  tests/test_verify_just_recipes.py
```

Result: 28 passed.

```bash
.venv/bin/ruff check \
  roboclaws/molmo_cleanup/advisory_scoring.py \
  roboclaws/molmo_cleanup/__init__.py \
  roboclaws/molmo_cleanup/report.py \
  roboclaws/molmo_cleanup/realworld_mcp_server.py \
  examples/molmospaces_realworld_cleanup.py \
  scripts/check_molmo_realworld_cleanup_result.py \
  tests/test_molmo_cleanup_advisory_scoring.py \
  tests/test_molmo_cleanup_report.py \
  tests/test_molmospaces_realworld_cleanup.py \
  tests/test_molmo_realworld_mcp_server.py \
  tests/test_check_molmo_realworld_cleanup_result.py \
  tests/test_verify_just_recipes.py
```

Result: passed.

```bash
.venv/bin/ruff format --check \
  roboclaws/molmo_cleanup/advisory_scoring.py \
  roboclaws/molmo_cleanup/__init__.py \
  roboclaws/molmo_cleanup/report.py \
  roboclaws/molmo_cleanup/realworld_mcp_server.py \
  examples/molmospaces_realworld_cleanup.py \
  scripts/check_molmo_realworld_cleanup_result.py \
  tests/test_molmo_cleanup_advisory_scoring.py \
  tests/test_molmo_cleanup_report.py \
  tests/test_molmospaces_realworld_cleanup.py \
  tests/test_molmo_realworld_mcp_server.py \
  tests/test_check_molmo_realworld_cleanup_result.py \
  tests/test_verify_just_recipes.py
```

Result: passed.

```bash
just verify::molmo-realworld-agent-dogfood-kit
```

Result: passed. The generated artifact includes:

- `advisory_evaluation.authoritative=false`
- `advisory_evaluation.schema_version=advisory_cleanup_scoring_v1`
- `artifacts.advisory_evaluation=.../advisory_evaluation.json`
- `Advisory Review` in `report.html`

```bash
just verify::molmo-realworld-openclaw-dogfood-kit
```

Result: passed with `--require-advisory-scoring`.

## Authority Check

Advisory scoring is post-run evidence only. It does not modify
`cleanup_status`, `completion_status`, `mess_restoration_rate`,
`sweep_coverage_rate`, or `disturbance_count`.
