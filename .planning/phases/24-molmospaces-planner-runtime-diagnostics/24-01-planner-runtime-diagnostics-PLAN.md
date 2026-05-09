# 24-01 Planner Runtime Diagnostics Plan

## Goal

Make planner-backed manipulation blockers actionable by recording dependency
availability and Python crash diagnostics in the existing planner probe artifact
and shared report underlay.

## Status

Planned 2026-05-09.

## Tasks

1. Add ADR/source-plan documentation and update roadmap/state/context references.
2. Enable faulthandler for planner worker subprocesses.
3. Record runtime diagnostics in worker payloads and blocked-capability evidence.
4. Render runtime diagnostics in the planner probe report.
5. Add focused tests, summary, and verification docs.

## Verification

- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_manipulation_provenance.py`
- `ruff check` / `ruff format --check` on changed Python files.
- `just verify::molmo-planner-manipulation-probe`

## Risks

- Diagnostics must not import expensive packages at Roboclaws top level.
- Diagnostics must not weaken the strict planner-backed proof checker.
- Native crashes may still terminate before JSON output; faulthandler stderr is
  the fallback evidence path for that case.
