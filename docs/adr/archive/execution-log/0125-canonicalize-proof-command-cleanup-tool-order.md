# 0125. Canonicalize Proof Command Cleanup Tool Order

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0123 made proof-bundle reports render command semantic subphases as
`nav, pick, nav, open?, place`. The report rail was correct, but the executable
probe command could still inherit a stale or alphabetically sorted
`--cleanup-tools` argument from a proof request binding, such as
`navigate_to_object,navigate_to_receptacle,open_receptacle,pick,place_inside`.

That means reviewers could see the intended semantic loop in `report.html`
while the actual command line asked the probe to bind tools in a different
order. The difference is small at the shell level but large at the architecture
level: MolmoSpaces demos should share one cleanup semantic underlay, not
separate report-only and command-only interpretations.

## Decision

Cleanup tool lists now normalize through one shared semantic-order helper:
`canonical_cleanup_tool_sequence`.

The helper preserves the cleanup loop order:

1. `navigate_to_object`
2. `pick`
3. `navigate_to_receptacle`
4. `open_receptacle`
5. `place` / `place_inside`

Observed-handle planner bindings, probe-side requested cleanup bindings,
promoted cleanup primitive bindings, proof-request derivation, proof command
manifests, and generated `--cleanup-tools` command arguments all use that
shared order.

## Consequences

- Proof-bundle `report.html` semantic rails and executable probe command flags
  describe the same cleanup loop.
- The semantic-order rule has locality in `semantic_timeline.py` instead of
  being reimplemented with `sorted(set(...))` in several call sites.
- Future MolmoSpaces demos can reuse the same underlying cleanup vocabulary for
  current-contract, ADR-0003, probe, proof-bundle, and report paths.
- Unknown tool names are preserved after known cleanup phases so the helper
  remains compatible with future extensions.

## Evidence

Implemented in Phase 134 on 2026-05-10.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/planner_observed_binding.py roboclaws/molmo_cleanup/planner_probe_primitive_executor.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/run_molmo_planner_manipulation_probe.py tests/test_molmo_planner_headless_renderer.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/planner_observed_binding.py roboclaws/molmo_cleanup/planner_probe_primitive_executor.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/run_molmo_planner_manipulation_probe.py tests/test_molmo_planner_headless_renderer.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_headless_renderer.py::test_cleanup_primitive_binding_promotes_only_matching_sampled_task tests/test_molmo_planner_proof_requests.py::test_build_probe_commands_rewrites_cleanup_tools_in_semantic_order tests/test_molmo_planner_proof_requests.py::test_canonical_cleanup_tool_sequence_uses_semantic_order tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_writes_dry_run_manifest_and_report_from_inline_requests`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json --output-dir output/debug-phase134-canonical-tool-order-dry-run --runner-python python --probe-script scripts/run_molmo_planner_manipulation_probe.py --cleanup-script examples/molmospaces_realworld_cleanup.py --molmospaces-python /home/mi/.cache/molmospaces/venv/bin/python --steps 2 --exclude-prior-covered --prior-covered-min-proof-steps 2 --request-id proof_001`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase134-canonical-tool-order-dry-run/proof_bundle_run_manifest.json --require-proof-execution-horizon --min-selected-requests 1 --max-selected-requests 1`
