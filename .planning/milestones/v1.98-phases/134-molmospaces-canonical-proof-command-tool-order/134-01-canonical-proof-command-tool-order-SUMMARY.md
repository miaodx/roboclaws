# Phase 134 Summary: MolmoSpaces Canonical Proof Command Tool Order

Completed: 2026-05-10
Backfilled: 2026-05-11
Source plan: `134-01-canonical-proof-command-tool-order-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Make proof-bundle executable cleanup tool flags, proof command manifest rows,
and report semantic subphase rails use one shared `nav, pick, nav, open?, place`
ordering rule.

## Completed Tasks

- The source plan records completion in its Status/Result section.

## Recorded Status

Complete on 2026-05-10.

The bounded `proof_001` dry-run now uses the same canonical cleanup tool order
for the executable command flag, manifest data, and report rail.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/planner_observed_binding.py roboclaws/molmo_cleanup/planner_probe_primitive_executor.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/run_molmo_planner_manipulation_probe.py tests/test_molmo_planner_headless_renderer.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/planner_observed_binding.py roboclaws/molmo_cleanup/planner_probe_primitive_executor.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/run_molmo_planner_manipulation_probe.py tests/test_molmo_planner_headless_renderer.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_headless_renderer.py::test_cleanup_primitive_binding_promotes_only_matching_sampled_task tests/test_molmo_planner_proof_requests.py::test_build_probe_commands_rewrites_cleanup_tools_in_semantic_order tests/test_molmo_planner_proof_requests.py::test_canonical_cleanup_tool_sequence_uses_semantic_order tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_writes_dry_run_manifest_and_report_from_inline_requests`

[Backfill note: source section truncated; see the phase PLAN for full embedded evidence.]

## Evidence

- `.venv/bin/ruff check roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/planner_observed_binding.py roboclaws/molmo_cleanup/planner_probe_primitive_executor.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/run_molmo_planner_manipulation_probe.py tests/test_molmo_planner_headless_renderer.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/planner_observed_binding.py roboclaws/molmo_cleanup/planner_probe_primitive_executor.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/run_molmo_planner_manipulation_probe.py tests/test_molmo_planner_headless_renderer.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_headless_renderer.py::test_cleanup_primitive_binding_promotes_only_matching_sampled_task tests/test_molmo_planner_proof_requests.py::test_build_probe_commands_rewrites_cleanup_tools_in_semantic_order tests/test_molmo_planner_proof_requests.py::test_canonical_cleanup_tool_sequence_uses_semantic_order tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_writes_dry_run_manifest_and_report_from_inline_requests`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json --output-dir output/debug-phase134-canonical-tool-order-dry-run --runner-python python --probe-script scripts/run_molmo_planner_manipulation_probe.py --cleanup-script examples/molmospaces_realworld_cleanup.py --molmospaces-python /home/mi/.cache/molmospaces/venv/bin/python --steps 2 --exclude-prior-covered --prior-covered-min-proof-steps 2 --request-id proof_001`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase134-canonical-tool-order-dry-run/proof_bundle_run_manifest.json --require-proof-execution-horizon --min-selected-requests 1 --max-selected-requests 1`

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.
