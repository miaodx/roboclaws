# Phase 32 Verification: RBY1M CuRobo Cache Isolation

Date: 2026-05-11
Source plan: `32-01-rby1m-curobo-cache-isolation-PLAN.md`
Backfill status: reconstructed from existing phase evidence.

## Verification Scope

This verification artifact repairs the missing GSD closeout file for Phase
32. It is based on the source plan's embedded status, tasks, acceptance
criteria, and recorded verification evidence. No fresh phase execution was run
as part of this backfill.

## Acceptance Evidence From Plan

- Runtime diagnostics record the effective Torch extension cache directory.
- `run_result.json` records known CuRobo extension `.so` and lock state.
- `report.html` renders a `CuRobo Extension Cache` section when cache
  diagnostics are present.
- Blocked mode remains explicit and checker-gated.
- Strict RBY1M/CuRobo readiness still requires execute-mode planner-backed
  evidence.

## Recorded Verification Evidence

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- Local RBY1M/CuRobo isolated-cache artifact under
  `output/molmo-planner-rby1m-curobo-cache-isolation/`.

## Artifact Integrity Checks

- Source plan exists: `32-01-rby1m-curobo-cache-isolation-PLAN.md`.
- Source plan contains a completion date or result marker: `2026-05-09`.
- Backfilled summary exists: `32-01-rby1m-curobo-cache-isolation-SUMMARY.md`.
- Backfilled verification exists: `32-VERIFICATION.md`.

## Verdict

GSD artifact closure is repaired for Phase 32 based on the existing
committed phase evidence. Treat this as a documentation repair. If a future
claim depends on real MolmoSpaces, real RBY1M/CuRobo, real VLM, Docker, GPU,
or API-key behavior, rerun the recorded commands or a current equivalent before
using the phase as fresh runtime proof.
