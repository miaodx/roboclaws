# Phase 26 Verification

Verified: 2026-05-09

## Commands

```bash
uv run ruff check roboclaws/molmo_cleanup/planner_proof_attachment.py examples/molmospaces_realworld_cleanup.py roboclaws/molmo_cleanup/realworld_mcp_server.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_planner_proof_attachment.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py
```

Result: passed.

```bash
uv run ruff format --check roboclaws/molmo_cleanup/planner_proof_attachment.py examples/molmospaces_realworld_cleanup.py roboclaws/molmo_cleanup/realworld_mcp_server.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_planner_proof_attachment.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py
```

Result: passed.

```bash
./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_attachment.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py
```

Result: passed, 24 tests.

```bash
.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --require-planner-backed output/molmo-planner-manipulation-probe-headless/run_result.json
```

Result: passed.

```bash
.venv/bin/python examples/molmospaces_realworld_cleanup.py --output-dir output/molmo-realworld-cleanup-planner-proof --backend molmospaces_subprocess --include-robot --record-robot-views --planner-proof-run-result output/molmo-planner-manipulation-probe-headless/run_result.json
```

Result: passed. Generated `run_result.json`, `report.html`, attached planner
proof views, and 176 robot-view PNGs plus 2 planner-proof PNGs.

```bash
.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --expect-backend molmospaces_subprocess --require-robot-views --require-advisory-scoring --require-planner-proof-attachment output/molmo-realworld-cleanup-planner-proof/run_result.json
```

Result: passed.

## Report Sections Confirmed

- `Attached Planner-Backed Proof`
- `Planner Initial`
- `Planner Final`
- `Semantic Substeps`
- `Robot View Timeline`
- `Agent View`
- `Advisory Review`
- `Private Evaluation`

## Remaining Gap

Planner-backed cleanup-loop primitive replacement is still future work. This
phase only attaches strict standalone proof beside the cleanup artifact.
