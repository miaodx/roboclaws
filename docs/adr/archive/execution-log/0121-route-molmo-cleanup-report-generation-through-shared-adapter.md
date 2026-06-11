# 0121. Route Molmo Cleanup Report Generation Through Shared Adapter

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0009 and ADR-0021 require MolmoSpaces cleanup demos to share one Cleanup
Artifact Report underlay. Phase 120 and Phase 124 proved that stale
current-contract and ADR-0003 artifacts can regenerate through the shared
adapter and keep the `nav, pick, nav, open?, place` visual rhythm.

The remaining architecture gap was command-surface ambiguity. The repo still
has an older generic replay reporter for AI2-THOR/OpenClaw game replays. A
developer asking to "generate report.html" for a Molmo cleanup artifact could
hit the wrong reporting family or assume that visually different reports meant
there were multiple Molmo cleanup implementations.

## Decision

The generic report entrypoint now detects Molmo cleanup `run_result.json`
artifacts and delegates to the Cleanup Report Artifact Adapter.

The adapter accepts either a run directory or a `run_result.json` path. The
`scripts/regenerate_molmo_cleanup_report.py` command uses the same artifact-path
adapter. Custom output paths remain unsupported for Molmo cleanup reports
because those reports intentionally live next to adjacent robot-view assets.

## Consequences

- `roboclaws.core.reporter.generate(path)` no longer routes Molmo cleanup
  artifacts toward the older replay report family.
- Developers can pass either a cleanup run directory or `run_result.json` and
  get the same shared Cleanup Artifact Report visual underlay.
- The AI2-THOR/OpenClaw replay reporter remains available for `replay.json`
  artifacts; this ADR does not merge unrelated report products.
- The report-family distinction is explicit in code instead of living in
  tribal memory or ignored `output/` artifacts.

## Evidence

Implemented in Phase 130 on 2026-05-10.

Verification:

- `.venv/bin/ruff check roboclaws/core/reporter.py roboclaws/molmo_cleanup/artifact_report.py scripts/regenerate_molmo_cleanup_report.py tests/test_reporter.py tests/test_molmo_cleanup_artifact_report.py`
- `.venv/bin/ruff format --check roboclaws/core/reporter.py roboclaws/molmo_cleanup/artifact_report.py scripts/regenerate_molmo_cleanup_report.py tests/test_reporter.py tests/test_molmo_cleanup_artifact_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_reporter.py::TestGenerate::test_molmo_cleanup_run_dir_routes_to_shared_underlay tests/test_reporter.py::TestGenerate::test_molmo_cleanup_run_result_routes_to_shared_underlay tests/test_reporter.py::TestGenerate::test_molmo_cleanup_route_rejects_custom_output_path tests/test_molmo_cleanup_artifact_report.py::test_rerender_cleanup_report_from_artifact_path_accepts_run_directory tests/test_molmo_cleanup_artifact_report.py::test_rerender_cleanup_reports_from_artifact_paths_reuses_directory_adapter`
- `.venv/bin/python -m roboclaws.core.reporter output/molmo-agent-bridge-visual-codex` preserved the existing `report.html` hash, proving the generic entrypoint routes the reference artifact through the shared cleanup adapter.
