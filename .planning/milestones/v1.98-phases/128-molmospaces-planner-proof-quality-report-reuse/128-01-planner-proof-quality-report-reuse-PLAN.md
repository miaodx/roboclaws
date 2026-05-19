# Phase 128 Plan: MolmoSpaces Planner Proof Quality Report Reuse

## Goal

Reuse Planner Proof Quality Evidence across standalone planner probes and
proof-bundle runner reports so all MolmoSpaces proof report surfaces describe
proof strength the same way.

## Tasks

1. Embed proof quality in planner-backed probe evidence.
2. Render `Planner Proof Quality` in standalone planner-probe reports.
3. Carry per-result and aggregate proof quality in proof-bundle result
   summaries.
4. Render proof quality in proof-bundle runner reports.
5. Add checker flags for standalone and bundled proof-quality requirements.
6. Add focused tests and update ADR, plan, `CONTEXT.md`, pilot plan, and
   `.planning/STATE.md`.

## Acceptance Checks

- Standalone proof reports render proof quality.
- Proof-bundle summaries include `proof_quality` and `proof_quality_summary`.
- Proof-bundle runner reports render proof-quality tiers.
- Checkers reject planner-backed proof rows below a requested step horizon.
- Focused lint, format, and pytest gates pass.

## Result

Complete on 2026-05-10.

Planner-backed probe evidence now embeds `proof_quality`; proof-bundle result
summaries aggregate it; standalone and runner reports render it; and the
checkers can require it.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/manipulation_provenance.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/manipulation_provenance.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py::test_planner_manipulation_probe_report_uses_shared_underlay tests/test_molmo_cleanup_report.py::test_planner_manipulation_probe_report_renders_proof_quality tests/test_molmo_planner_proof_requests.py::test_proof_result_summary_classifies_task_feasibility_and_views tests/test_molmo_planner_proof_requests.py::test_proof_result_summary_carries_planner_proof_quality tests/test_check_molmo_planner_manipulation_probe.py::test_checker_can_require_planner_probe_proof_quality tests/test_check_molmo_planner_proof_bundle_runner_result.py::test_checker_can_require_proof_quality_for_planner_backed_result`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase125-curobo-pregrasp-exception-context/run_result.json --require-planner-backed --accept-rby1m-curobo-blocked --require-curobo-extension-cache --require-warp-compatibility --require-cuda-memory --require-curobo-memory-profile --require-cleanup-scene-bound --require-proof-quality --require-proof-min-steps 1`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase90-broader-selected-proof-execution/proof_bundle_run_manifest.json --require-proof-outputs --require-proof-quality --require-planner-backed-proof-min-steps 1`
