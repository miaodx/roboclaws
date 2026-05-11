# Phase 35 Verification: RBY1M CuRobo Memory Profile

Date: 2026-05-11
Source plan: `35-01-rby1m-curobo-memory-profile-PLAN.md`
Backfill status: reconstructed from existing phase evidence.

## Verification Scope

This verification artifact repairs the missing GSD closeout file for Phase
35. It is based on the source plan's embedded status, tasks, acceptance
criteria, and recorded verification evidence. No fresh phase execution was run
as part of this backfill.

## Acceptance Evidence From Plan

- No-profile probes keep current default behavior.
- Low-memory profile overrides are visible in `run_result.json` and
  `report.html`.
- The default low-memory profile keeps collision avoidance enabled.
- Blocked mode remains explicit and checker-gated.
- Strict RBY1M/CuRobo readiness still requires execute-mode planner-backed
  robot-state movement.

## Recorded Verification Evidence

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- Local RBY1M/CuRobo execute artifact under
  `output/molmo-planner-rby1m-curobo-memory-profile-execute/`.

## Artifact Integrity Checks

- Source plan exists: `35-01-rby1m-curobo-memory-profile-PLAN.md`.
- Source plan contains a completion date or result marker: `2026-05-09`.
- Backfilled summary exists: `35-01-rby1m-curobo-memory-profile-SUMMARY.md`.
- Backfilled verification exists: `35-VERIFICATION.md`.

## Verdict

GSD artifact closure is repaired for Phase 35 based on the existing
committed phase evidence. Treat this as a documentation repair. If a future
claim depends on real MolmoSpaces, real RBY1M/CuRobo, real VLM, Docker, GPU,
or API-key behavior, rerun the recorded commands or a current equivalent before
using the phase as fresh runtime proof.
