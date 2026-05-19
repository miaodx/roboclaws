# MolmoSpaces Canonical Proof Command Tool Order

**Status:** Completed under GSD Phase 134 on 2026-05-10
**Created:** 2026-05-10
**Source:** ADR-0003, ADR-0123, ADR-0124, `CONTEXT.md`,
`docs/retrospectives/plans/molmospaces-manipulation-spike.md`
**Workflow:** `hybrid-phase-pipeline`

## Problem

The proof-bundle runner now renders proof command rows with semantic subphases,
but the actual executable `--cleanup-tools` argument can still come from older
request bindings that sorted tools alphabetically. That produces a visible
split: the report says `nav, pick, nav, open?, place`, while the command can say
`nav, nav, open, pick, place`.

## Decision

Add a shared canonical cleanup tool-order helper and route proof request,
binding, probe, and command construction through it.

## Non-Goals

- Do not execute the real RBY1M/CuRobo proof in this phase.
- Do not change proof selection, fallback generation, or proof quality rules.
- Do not rewrite report layout beyond the data order supplied to it.

## Acceptance Criteria

- Shared helper returns cleanup tools in `nav, pick, nav, open?, place` order.
- Observed-handle bindings and probe-side cleanup bindings use the shared
  helper instead of alphabetical set order.
- Proof command construction rewrites `--cleanup-tools` from canonical request
  tools before writing the command manifest.
- Bounded dry-run for `proof_001` emits canonical `--cleanup-tools`.
- Focused lint, format, pytest, and dry-run checker pass.

## Result

Complete.

`proof_001` now emits:

```text
navigate_to_object,pick,navigate_to_receptacle,open_receptacle,place_inside
```

for the executable `--cleanup-tools` flag, the manifest `tools` row, and the
report semantic subphase rail.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/planner_observed_binding.py roboclaws/molmo_cleanup/planner_probe_primitive_executor.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/run_molmo_planner_manipulation_probe.py tests/test_molmo_planner_headless_renderer.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/planner_observed_binding.py roboclaws/molmo_cleanup/planner_probe_primitive_executor.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/run_molmo_planner_manipulation_probe.py tests/test_molmo_planner_headless_renderer.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_headless_renderer.py::test_cleanup_primitive_binding_promotes_only_matching_sampled_task tests/test_molmo_planner_proof_requests.py::test_build_probe_commands_rewrites_cleanup_tools_in_semantic_order tests/test_molmo_planner_proof_requests.py::test_canonical_cleanup_tool_sequence_uses_semantic_order tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_writes_dry_run_manifest_and_report_from_inline_requests`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json --output-dir output/debug-phase134-canonical-tool-order-dry-run --runner-python python --probe-script scripts/run_molmo_planner_manipulation_probe.py --cleanup-script examples/molmospaces_realworld_cleanup.py --molmospaces-python /home/mi/.cache/molmospaces/venv/bin/python --steps 2 --exclude-prior-covered --prior-covered-min-proof-steps 2 --request-id proof_001`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase134-canonical-tool-order-dry-run/proof_bundle_run_manifest.json --require-proof-execution-horizon --min-selected-requests 1 --max-selected-requests 1`
