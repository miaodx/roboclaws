# MolmoSpaces Planner Proof Quality Report Reuse

**Status:** Completed under GSD Phase 128 on 2026-05-10
**Created:** 2026-05-10
**Source:** ADR-0118, Phase 127, `CONTEXT.md`, `docs/retrospectives/plans/molmospaces-manipulation-spike.md`
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 127 made attached cleanup proofs carry proof quality, but standalone
planner-probe reports and proof-bundle runner reports still described proof
strength through scattered lower-level fields.

That left one remaining report architecture gap: the same proof could look like
`steps_executed=1` in the standalone report, a `planner_backed_count` in the
runner report, and `one_step_motion` in the cleanup report.

## Decision

Reuse Planner Proof Quality Evidence across the proof pipeline:

- embed proof quality in planner-backed probe evidence;
- render `Planner Proof Quality` in standalone probe reports;
- carry `proof_quality` and `proof_quality_summary` in proof-bundle summaries;
- render quality tiers in proof-bundle runner reports;
- add checker flags for standalone and bundled proof-quality requirements.

## Non-Goals

- Do not run new local MolmoSpaces/CuRobo proofs.
- Do not claim full pick/place or containment from existing one-step proof.
- Do not change cleanup primitive provenance.
- Do not introduce a second report renderer.

## Acceptance Criteria

- Standalone planner-probe reports render `Planner Proof Quality`.
- Proof-bundle summaries include per-result and aggregate proof-quality data.
- Proof-bundle runner reports render proof-quality tiers.
- Standalone and runner checkers can require proof quality and minimum executed
  steps for planner-backed results.
- Focused lint, format, and pytest gates pass.

## Result

Complete.

Standalone proof reports, proof-bundle runner reports, and cleanup reports now
share the same proof-quality vocabulary. A future stricter proof gate can raise
the minimum executed-step requirement without adding report-specific logic.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/manipulation_provenance.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/manipulation_provenance.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py::test_planner_manipulation_probe_report_uses_shared_underlay tests/test_molmo_cleanup_report.py::test_planner_manipulation_probe_report_renders_proof_quality tests/test_molmo_planner_proof_requests.py::test_proof_result_summary_classifies_task_feasibility_and_views tests/test_molmo_planner_proof_requests.py::test_proof_result_summary_carries_planner_proof_quality tests/test_check_molmo_planner_manipulation_probe.py::test_checker_can_require_planner_probe_proof_quality tests/test_check_molmo_planner_proof_bundle_runner_result.py::test_checker_can_require_proof_quality_for_planner_backed_result`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase125-curobo-pregrasp-exception-context/run_result.json --require-planner-backed --accept-rby1m-curobo-blocked --require-curobo-extension-cache --require-warp-compatibility --require-cuda-memory --require-curobo-memory-profile --require-cleanup-scene-bound --require-proof-quality --require-proof-min-steps 1`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase90-broader-selected-proof-execution/proof_bundle_run_manifest.json --require-proof-outputs --require-proof-quality --require-planner-backed-proof-min-steps 1`
