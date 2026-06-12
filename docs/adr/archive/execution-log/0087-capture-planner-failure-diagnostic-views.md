# 0087. Capture Planner Failure Diagnostic Views

Date: 2026-05-10

## Status

Accepted

## Context

Phase 95 executed four selected seed 9 proof commands through the shared
proof-bundle runner. All four reached task sampling with the wide RBY1M
placement profile, but all four were blocked by post-placement grasp
feasibility before policy execution produced the usual initial/final planner
views.

That left a report architecture gap. Successful planner probes and proof
bundles used the shared `image_artifacts` view path, while blocked
task-sampler probes fell back to tables and the message "No planner probe
views recorded." This made failure reports less reviewable and looked like a
second implementation despite the shared report underlay.

## Decision

Keep one planner visual evidence interface:

- successful probes continue writing `initial` and `final` image artifacts;
- blocked task-sampler probes may write bounded diagnostic camera artifacts
  after robot placement, using the same `image_artifacts` field;
- if an old blocked artifact has no image files, the shared report renderer
  still renders an inline task-sampler diagnostic view from placement and grasp
  diagnostics instead of showing an empty visual surface.

The runner captures at most one post-placement camera view per blocked proof
attempt to keep local proof bundles bounded. The proof-bundle summary and
standalone planner report both consume these views through the same report
renderer.

## Consequences

- Future grasp-feasibility failures should show visual post-placement evidence
  in standalone proof reports and bundle reports.
- Existing failure artifacts with placement/grasp diagnostics can be rerendered
  into a more useful report without rerunning MolmoSpaces.
- This does not claim new planner-backed cleanup readiness. It improves
  blocked-proof evidence and report locality.
- Ignored `output/` artifacts remain local evidence and are not committed.

## Evidence

Implemented in Phase 96 on 2026-05-10.

Verification:

- `.venv/bin/ruff format --check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
