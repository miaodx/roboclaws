# Phase 14 Verification

## Checklist

| Requirement | Evidence |
| --- | --- |
| Implement ADR-0003 public/private split | `roboclaws/molmo_cleanup/realworld_contract.py` defines `REALWORLD_CONTRACT = "realworld_cleanup_v1"` and exposes public metric-map, fixture-hint, waypoint observe, observed-handle manipulation, and done tools. |
| Agent View exposes only metric map, room fixture hints, public fixture IDs, and robot-local detections | `agent_view.json` contains `metric_map`, `fixture_hints`, `observed_objects`, and `public_tool_names`; checker `_assert_public_agent_view` enforces this shape. |
| No Generated Mess Set, target count, acceptable destination sets, `is_misplaced`, or global movable-object inventory in Agent View | `forbidden_agent_view_keys()` and checker `_assert_no_forbidden_keys` reject those keys in Agent View and all non-`done` trace events. Focused leak test mutates `agent_view["generated_mess_set"]` and asserts checker failure. |
| Small movable object IDs become available only as observed handles | Contract assigns stable `observed_###` handles and translates internally; tests assert every observed object ID starts with `observed_`. |
| Current global `scene_objects` is retired/restricted in this harness | `RealWorldCleanupContract.public_tool_names()` does not include `scene_objects`; demo trace test asserts no `"tool": "scene_objects"` lines. |
| Deterministic scoring remains authoritative | `done()` delegates to the existing backend private manifest scorer, then adds `mess_restoration_rate`, `sweep_coverage_rate`, `disturbance_count`, and `completion_status`. |
| Post-run private evaluation is separated from public agent input | Demo writes `agent_view.json` and `private_evaluation.json`; report renderer adds separate `Agent View` and `Private Evaluation` sections for `contract=realworld_cleanup_v1`. |
| ADR-0003 report has visual parity with the current-contract bridge report | `roboclaws/molmo_cleanup/semantic_timeline.py` is the shared timeline underlay for current-contract and ADR-0003 cleanup reports. `examples/molmospaces_realworld_cleanup.py` records `navigate_to_object -> pick -> navigate_to_receptacle -> open_receptacle? -> place/place_inside` robot-view phases and passes `robot_view_steps` into the shared report renderer; the checker can require the `Robot View Timeline`. |
| `run_result.json` records required ADR-0003 fields | Demo writes `backend`, `task_prompt`, `fixture_hint_mode`, `generated_mess_count`, `policy`, `policy_uses_private_truth=false`, `mess_restoration_rate`, `sweep_coverage_rate`, `disturbance_count`, and `primitive_provenance_summary`. |
| Three-seed real MolmoSpaces harness passes | `just harness::molmo-realworld-cleanup` passed and checker accepted `output/molmo-realworld-cleanup-harness/seed-{1,2,3}/run_result.json`. |
| Existing current-contract bridge/report path remains covered | Focused regression command included `tests/test_molmo_cleanup_report.py`, `tests/test_molmo_cleanup_demo.py`, and `tests/test_molmo_cleanup_mcp_server.py`; all passed. |

## Command Results

| Gate | Result |
| --- | --- |
| Dependency install | PASS: `uv pip install -e ".[dev]"` completed. |
| AI2-THOR import | PASS: `.venv/bin/python -c "import ai2thor; ..."` -> `ai2thor 5.0.0 ok`. Bare `python` is absent on PATH. |
| VLM key sanity | PASS after sourcing `.env`. No key values were printed. |
| Focused tests | PASS: `17 passed`. |
| Ruff | PASS: `.venv/bin/ruff check .` -> `All checks passed!`; `.venv/bin/ruff format --check .` -> `154 files already formatted`. |
| Whitespace | PASS: `git diff --check`. |
| Real MolmoSpaces harness | PASS: `molmo-realworld-cleanup ok: output/molmo-realworld-cleanup-harness (3 run(s))`; seeds 1, 2, and 3 each generated 23 robot timeline steps and 92 robot-view PNGs. |
| Composed verify recipe | PASS: `just verify::molmo-realworld-cleanup` ran focused pytest (`13 passed`) and the real three-seed harness checker. |
| Visual report parity check | PASS: `just harness::molmo-realworld-cleanup "1" "output/molmo-realworld-cleanup-harness-visual-check"` generated 23 robot timeline steps, 92 robot-view PNGs, and a `report.html` containing `Robot View Timeline`, `Agent View`, `Private Evaluation`, and the same object-level semantic phase shape as `output/molmo-agent-bridge-visual-codex/report.html`. |

## Real Run Summary

| Seed | Backend | Status | Exact Restoration | Coverage | Disturbance |
| --- | --- | --- | --- | --- | --- |
| 1 | `molmospaces_subprocess` | `success` | 4/5 (`mess_restoration_rate=0.8`) | 1.0 | 0 |
| 2 | `molmospaces_subprocess` | `success` | 4/5 (`mess_restoration_rate=0.8`) | 1.0 | 0 |
| 3 | `molmospaces_subprocess` | `success` | 4/5 (`mess_restoration_rate=0.8`) | 1.0 | 0 |

The missed exact object in each run is the pillow: the deterministic public
policy chose a semantically preferred bed, but the private scorer expected a
different bed. This is acceptable for v1 because the exact restoration rate is
above the 0.70 threshold, coverage is complete, and no disturbance occurred.

## Residual Scope

- Generated Mess Set size remains 5, inherited from the existing fixed
  MolmoSpaces target selector. The original draft's 10-20 object ambition is a
  follow-up, not part of this completed first ADR-0003 contract slice.
- No OpenClaw/coding-agent policy is evaluated here; the deterministic baseline
  intentionally proves the contract before model policies are reintroduced.
