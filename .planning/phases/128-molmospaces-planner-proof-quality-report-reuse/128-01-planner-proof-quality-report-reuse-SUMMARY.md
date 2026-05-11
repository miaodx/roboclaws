# Phase 128 Summary: MolmoSpaces Planner Proof Quality Report Reuse

Completed: 2026-05-10
Backfilled: 2026-05-11
Source plan: `128-01-planner-proof-quality-report-reuse-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Reuse Planner Proof Quality Evidence across standalone planner probes and
proof-bundle runner reports so all MolmoSpaces proof report surfaces describe
proof strength the same way.

## Completed Tasks

- The source plan records completion in its Status/Result section.

## Recorded Status

Complete on 2026-05-10.

Planner-backed probe evidence now embeds `proof_quality`; proof-bundle result
summaries aggregate it; standalone and runner reports render it; and the
checkers can require it.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/manipulation_provenance.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/manipulation_provenance.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`

[Backfill note: source section truncated; see the phase PLAN for full embedded evidence.]

## Evidence

- `.venv/bin/ruff check roboclaws/molmo_cleanup/manipulation_provenance.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/manipulation_provenance.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py::test_planner_manipulation_probe_report_uses_shared_underlay tests/test_molmo_cleanup_report.py::test_planner_manipulation_probe_report_renders_proof_quality tests/test_molmo_planner_proof_requests.py::test_proof_result_summary_classifies_task_feasibility_and_views tests/test_molmo_planner_proof_requests.py::test_proof_result_summary_carries_planner_proof_quality tests/test_check_molmo_planner_manipulation_probe.py::test_checker_can_require_planner_probe_proof_quality tests/test_check_molmo_planner_proof_bundle_runner_result.py::test_checker_can_require_proof_quality_for_planner_backed_result`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase125-curobo-pregrasp-exception-context/run_result.json --require-planner-backed --accept-rby1m-curobo-blocked --require-curobo-extension-cache --require-warp-compatibility --require-cuda-memory --require-curobo-memory-profile --require-cleanup-scene-bound --require-proof-quality --require-proof-min-steps 1`

[Backfill note: source section truncated; see the phase PLAN for full embedded evidence.]

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.
