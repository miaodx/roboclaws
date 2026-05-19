# Phase 134 Plan: MolmoSpaces Canonical Proof Command Tool Order

## Goal

Make proof-bundle executable cleanup tool flags, proof command manifest rows,
and report semantic subphase rails use one shared `nav, pick, nav, open?, place`
ordering rule.

## Tasks

1. Add a shared canonical cleanup tool sequence helper in the semantic timeline
   module.
2. Replace local alphabetical tool normalization in observed-handle bindings,
   probe-side binding parsing, probe binding promotion, and proof-request tool
   extraction.
3. Rewrite proof command `--cleanup-tools` from canonical request tools during
   command construction.
4. Add focused tests for helper ordering, command rewriting, and promoted
   cleanup binding order.
5. Regenerate a bounded dry-run for `proof_001` and validate it with the runner
   checker.
6. Update ADR, plan, `CONTEXT.md`, pilot plan, and `.planning/STATE.md`.

## Acceptance Checks

- `proof_001` dry-run command contains
  `navigate_to_object,pick,navigate_to_receptacle,open_receptacle,place_inside`.
- Command manifest `tools` and `semantic_subphases` match the executable
  `--cleanup-tools` value.
- Focused lint, format, pytest, dry-run, and checker pass.

## Result

Complete on 2026-05-10.

The bounded `proof_001` dry-run now uses the same canonical cleanup tool order
for the executable command flag, manifest data, and report rail.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/planner_observed_binding.py roboclaws/molmo_cleanup/planner_probe_primitive_executor.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/run_molmo_planner_manipulation_probe.py tests/test_molmo_planner_headless_renderer.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/planner_observed_binding.py roboclaws/molmo_cleanup/planner_probe_primitive_executor.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/run_molmo_planner_manipulation_probe.py tests/test_molmo_planner_headless_renderer.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_headless_renderer.py::test_cleanup_primitive_binding_promotes_only_matching_sampled_task tests/test_molmo_planner_proof_requests.py::test_build_probe_commands_rewrites_cleanup_tools_in_semantic_order tests/test_molmo_planner_proof_requests.py::test_canonical_cleanup_tool_sequence_uses_semantic_order tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_writes_dry_run_manifest_and_report_from_inline_requests`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json --output-dir output/debug-phase134-canonical-tool-order-dry-run --runner-python python --probe-script scripts/run_molmo_planner_manipulation_probe.py --cleanup-script examples/molmospaces_realworld_cleanup.py --molmospaces-python /home/mi/.cache/molmospaces/venv/bin/python --steps 2 --exclude-prior-covered --prior-covered-min-proof-steps 2 --request-id proof_001`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase134-canonical-tool-order-dry-run/proof_bundle_run_manifest.json --require-proof-execution-horizon --min-selected-requests 1 --max-selected-requests 1`
