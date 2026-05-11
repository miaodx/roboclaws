# 0119. Render Planner Proof Quality Across Probe Reports

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0118 introduced **Planner Proof Quality Evidence** for attached cleanup
proofs. That made the ADR-0003 cleanup report honest about the current Phase
125 proof being `one_step_motion`.

The remaining report gap was cross-artifact drift. Standalone planner-probe
reports and proof-bundle runner reports still spoke in lower-level fields such
as `steps_executed`, `max_abs_qpos_delta`, and `planner_backed_count`.
Reviewing a proof therefore required translating between three report surfaces:
the individual proof report, the runner summary, and the cleanup artifact.

## Decision

Reuse the same Planner Proof Quality Evidence interface in:

- planner-backed manipulation probe evidence;
- standalone planner-probe reports;
- proof-bundle result summaries;
- proof-bundle runner reports;
- probe and runner checkers.

Planner-backed probe evidence now embeds `proof_quality`. Proof-result
summaries now carry per-proof quality plus a `proof_quality_summary`. The
standalone proof report and proof-bundle runner report both render `Planner
Proof Quality`, including the quality tier, executed steps, qpos delta, and
containment status.

The standalone checker can now require:

- `--require-proof-quality`;
- `--require-proof-min-steps N`.

The proof-bundle runner checker can now require:

- `--require-proof-quality`;
- `--require-planner-backed-proof-min-steps N`.

## Consequences

- The standalone proof report, proof-bundle runner report, and cleanup report
  now use the same proof-strength vocabulary.
- Future stricter gates can raise the minimum step horizon without duplicating
  proof-strength logic in each checker.
- Blocked proof results remain visible as `unknown` quality instead of being
  silently omitted from runner summaries.
- This does not execute new proofs or claim containment; it only removes report
  and checker drift around proof strength.

## Evidence

Implemented in Phase 128 on 2026-05-10.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/manipulation_provenance.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/manipulation_provenance.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py::test_planner_manipulation_probe_report_uses_shared_underlay tests/test_molmo_cleanup_report.py::test_planner_manipulation_probe_report_renders_proof_quality tests/test_molmo_planner_proof_requests.py::test_proof_result_summary_classifies_task_feasibility_and_views tests/test_molmo_planner_proof_requests.py::test_proof_result_summary_carries_planner_proof_quality tests/test_check_molmo_planner_manipulation_probe.py::test_checker_can_require_planner_probe_proof_quality tests/test_check_molmo_planner_proof_bundle_runner_result.py::test_checker_can_require_proof_quality_for_planner_backed_result`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py output/debug-phase125-curobo-pregrasp-exception-context/run_result.json --require-planner-backed --accept-rby1m-curobo-blocked --require-curobo-extension-cache --require-warp-compatibility --require-cuda-memory --require-curobo-memory-profile --require-cleanup-scene-bound --require-proof-quality --require-proof-min-steps 1`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase90-broader-selected-proof-execution/proof_bundle_run_manifest.json --require-proof-outputs --require-proof-quality --require-planner-backed-proof-min-steps 1`
