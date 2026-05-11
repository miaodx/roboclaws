# Phase 134 Verification: MolmoSpaces Canonical Proof Command Tool Order

Date: 2026-05-11
Source plan: `134-01-canonical-proof-command-tool-order-PLAN.md`
Backfill status: reconstructed from existing phase evidence.

## Verification Scope

This verification artifact repairs the missing GSD closeout file for Phase
134. It is based on the source plan's embedded status, tasks, acceptance
criteria, and recorded verification evidence. No fresh phase execution was run
as part of this backfill.

## Acceptance Evidence From Plan

- `proof_001` dry-run command contains
  `navigate_to_object,pick,navigate_to_receptacle,open_receptacle,place_inside`.
- Command manifest `tools` and `semantic_subphases` match the executable
  `--cleanup-tools` value.
- Focused lint, format, pytest, dry-run, and checker pass.

## Recorded Verification Evidence

- `.venv/bin/ruff check roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/planner_observed_binding.py roboclaws/molmo_cleanup/planner_probe_primitive_executor.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/run_molmo_planner_manipulation_probe.py tests/test_molmo_planner_headless_renderer.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/planner_observed_binding.py roboclaws/molmo_cleanup/planner_probe_primitive_executor.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/run_molmo_planner_manipulation_probe.py tests/test_molmo_planner_headless_renderer.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_headless_renderer.py::test_cleanup_primitive_binding_promotes_only_matching_sampled_task tests/test_molmo_planner_proof_requests.py::test_build_probe_commands_rewrites_cleanup_tools_in_semantic_order tests/test_molmo_planner_proof_requests.py::test_canonical_cleanup_tool_sequence_uses_semantic_order tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_writes_dry_run_manifest_and_report_from_inline_requests`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json --output-dir output/debug-phase134-canonical-tool-order-dry-run --runner-python python --probe-script scripts/run_molmo_planner_manipulation_probe.py --cleanup-script examples/molmospaces_realworld_cleanup.py --molmospaces-python /home/mi/.cache/molmospaces/venv/bin/python --steps 2 --exclude-prior-covered --prior-covered-min-proof-steps 2 --request-id proof_001`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase134-canonical-tool-order-dry-run/proof_bundle_run_manifest.json --require-proof-execution-horizon --min-selected-requests 1 --max-selected-requests 1`

## Artifact Integrity Checks

- Source plan exists: `134-01-canonical-proof-command-tool-order-PLAN.md`.
- Source plan contains a completion date or result marker: `2026-05-10`.
- Backfilled summary exists: `134-01-canonical-proof-command-tool-order-SUMMARY.md`.
- Backfilled verification exists: `134-VERIFICATION.md`.

## Verdict

GSD artifact closure is repaired for Phase 134 based on the existing
committed phase evidence. Treat this as a documentation repair. If a future
claim depends on real MolmoSpaces, real RBY1M/CuRobo, real VLM, Docker, GPU,
or API-key behavior, rerun the recorded commands or a current equivalent before
using the phase as fresh runtime proof.
