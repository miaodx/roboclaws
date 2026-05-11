# Phase 14 Plan 01 Summary

## Implemented

- Added `RealWorldCleanupContract`, an ADR-0003 public boundary over the Molmo
  cleanup semantic backend.
- Added `examples/molmospaces_realworld_cleanup.py`, a deterministic sweep
  baseline that uses only public `metric_map`, room-level `fixture_hints`,
  waypoint `observe`, and `observed_*` handles.
- Added a focused checker and just recipes:
  `scripts/check_molmo_realworld_cleanup_result.py`,
  `just harness::molmo-realworld-cleanup`, and
  `just verify::molmo-realworld-cleanup`.
- Extended cleanup reports with explicit `Agent View` and `Private Evaluation`
  sections for `contract=realworld_cleanup_v1`.
- Added `roboclaws/molmo_cleanup/semantic_timeline.py` as the shared semantic
  timeline underlay for current-contract bridge artifacts and ADR-0003 harness
  artifacts.
- Added ADR-0003 visual report parity with the current-contract bridge report:
  real-world cleanup runs now record `navigate_to_object -> pick ->
  navigate_to_receptacle -> open_receptacle? -> place/place_inside` RBY1M
  FPV/chase/map/verification views and render the shared `Robot View Timeline`.
- Updated the source plan with implementation status and evidence.

## Evidence

- Preflight dependency install completed with `uv pip install -e ".[dev]"`.
- AI2-THOR import check passed with `.venv/bin/python` (`ai2thor 5.0.0 ok`);
  the bare `python` command is not on PATH on this host.
- VLM key sanity check passed after sourcing `.env`.
- Focused tests passed:
  `./scripts/run_pytest_standalone.sh -q tests/test_molmo_realworld_contract.py tests/test_molmospaces_realworld_cleanup.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_verify_just_recipes.py tests/test_molmo_cleanup_report.py tests/test_molmo_cleanup_demo.py tests/test_molmo_cleanup_mcp_server.py`
  -> `20 passed`.
- Static gates passed:
  `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`, and
  `git diff --check`.
- Real backend gate passed:
  `just harness::molmo-realworld-cleanup` ->
  `molmo-realworld-cleanup ok: output/molmo-realworld-cleanup-harness (3 run(s))`.
- Composed verify recipe passed:
  `just verify::molmo-realworld-cleanup` -> focused pytest `13 passed`, then
  `molmo-realworld-cleanup ok: output/molmo-realworld-cleanup-harness (3 run(s))`.
- Visual report parity check passed:
  `just harness::molmo-realworld-cleanup "1" "output/molmo-realworld-cleanup-harness-visual-check"`
  generated 23 robot timeline steps, 92 robot-view PNGs, and a report containing
  `Robot View Timeline`, `Agent View`, `Private Evaluation`, and the same
  object-level semantic phase shape as the current-contract bridge report.

## Notes

- The first ADR-0003 slice keeps the existing MolmoSpaces selected target count
  of 5. It proves the public/private agent boundary and deterministic scoring
  contract, but does not yet expand Generated Mess Set size to 10-20 objects.
- Exact private scoring restored 4/5 objects in each real run because the pillow
  was placed on a semantically preferred bed that was not the private target bed.
  The v1 threshold is still satisfied: `mess_restoration_rate=0.8`,
  `sweep_coverage_rate=1.0`, `disturbance_count=0`.
