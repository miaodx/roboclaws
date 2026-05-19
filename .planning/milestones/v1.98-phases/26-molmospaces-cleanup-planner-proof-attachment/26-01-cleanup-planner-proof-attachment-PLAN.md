# 26-01 Cleanup Planner Proof Attachment Plan

## Goal

Render strict standalone Franka planner proof inside ADR-0003 cleanup artifacts
without mislabeling cleanup-loop `api_semantic` object moves as planner-backed
execution.

## Status

Completed 2026-05-09.

## Tasks

- [x] Add ADR/source-plan documentation and update roadmap/state/context references.
- [x] Add a proof-attachment helper that validates strict planner probe artifacts
   and copies proof images into the cleanup run directory.
- [x] Add cleanup harness and MCP-server support for optional proof attachment.
- [x] Render `Attached Planner-Backed Proof` in the shared cleanup report.
- [x] Add checker/tests and generate a local cleanup report with attached proof
   views.

## Outcome

The ADR-0003 cleanup harness and MCP server can now attach a strict standalone
Franka planner probe result. The attachment validator rejects non-strict proof,
copies proof images into the cleanup artifact, renders the proof beside the
shared cleanup report, and keeps cleanup-loop object-move provenance as
`api_semantic`.

Local evidence:

- `output/molmo-realworld-cleanup-planner-proof/run_result.json`
- `output/molmo-realworld-cleanup-planner-proof/report.html`
- `output/molmo-realworld-cleanup-planner-proof/planner_proof/`

## Verification

- `uv run ruff check` / `uv run ruff format --check` on changed Python files.
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_attachment.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py`
- `.venv/bin/python examples/molmospaces_realworld_cleanup.py --output-dir output/molmo-realworld-cleanup-planner-proof --backend molmospaces_subprocess --include-robot --record-robot-views --planner-proof-run-result output/molmo-planner-manipulation-probe-headless/run_result.json`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --expect-backend molmospaces_subprocess --require-robot-views --require-advisory-scoring --require-planner-proof-attachment output/molmo-realworld-cleanup-planner-proof/run_result.json`

All verification commands passed on 2026-05-09.

## Risks

- Attachment can be mistaken for cleanup-loop planner execution unless report
  copy and checker assertions keep cleanup primitive provenance explicit.
- The cleanup harness may be slow with robot views; keep tests focused and use a
  local artifact for full proof.
