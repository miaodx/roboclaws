# 0088. Render Post-Placement Rejection Views

Date: 2026-05-10

## Status

Accepted

## Context

Phase 96 made blocked planner probes visually reviewable even when normal
initial/final planner screenshots do not exist. The next remaining blocker is
the shared RBY1M `grasp_feasibility` path: after wide robot placement succeeds,
the upstream task sampler repeatedly reports grasp failures and candidate
removals before raising `HouseInvalidForTask`.

Those rejection details were available in tables and metrics, but not as a
stable report visual. That kept the most important current blocker visually
weaker than successful planner views and risked another report-specific
presentation path.

## Decision

Render post-placement grasp/candidate rejection evidence as a shared diagnostic
view:

- standalone planner reports show `Post-Placement Rejection Views` inside the
  existing `Post-Placement Candidate Rejections` section;
- proof-bundle result cards render the same rejection view whenever a result
  carries `task_sampler_failure_diagnostics.grasp_failures`;
- checker gates require that visual when grasp-failure diagnostics are present.

The view is diagnostic evidence only. It explains the current
`grasp_feasibility` blocker and does not promote planner-backed cleanup
readiness.

## Consequences

- Current and future blocked proof reports have a visual path for the
  post-placement rejection sequence, not just tables.
- The report remains one shared underlay; current-contract, ADR-0003, planner
  probe, prior-proof, and proof-bundle views reuse the same renderer helpers.
- Existing artifacts can be rerendered locally to gain the new visual without
  rerunning MolmoSpaces.

## Evidence

Implemented in Phase 97 on 2026-05-10.

Verification:

- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
