# MolmoSpaces Proof-Bundle Local Runtime Preflight

**Status:** Completed under GSD Phase 99 on 2026-05-10
**Created:** 2026-05-10
**Source:** `CONTEXT.md`, ADR-0090, Phase98 local-dev handoff
**Workflow:** `hybrid-phase-pipeline`

## Problem

The next broader step is either proof-source rotation or grasp-feasibility
reduction, but real proof execution depends on the local MolmoSpaces Python
runtime. The runner must check the canonical `molmo_spaces` package import so a
real execution attempt cannot fail before it writes a manifest or report.

## Decision

Add a local runtime preflight to the proof-bundle runner:

- run it only when `--execute-probes` is requested;
- check the configured MolmoSpaces Python import path;
- short-circuit to `local_runtime_blocked` when the import fails;
- render the preflight in the runner report;
- make the checker validate the preflight evidence.

## Non-Goals

- Do not install or repair MolmoSpaces.
- Do not execute real RBY1M/CuRobo proof commands when preflight is blocked.
- Do not change proof request selection.
- Do not commit ignored `output/` artifacts.

## Acceptance Criteria

- A blocked local runtime still produces `proof_bundle_run_manifest.json` and
  `report.html`.
- The manifest status is `local_runtime_blocked`.
- The report renders `Local Runtime Preflight`.
- Proof and warmup commands do not execute after a blocked preflight.
- The proof-bundle checker accepts the blocked status only with preflight
  evidence.
- Focused lint and pytest pass.

## Result

Complete on 2026-05-10.

Implemented:

- execution-time MolmoSpaces import preflight;
- `local_runtime_blocked` runner status;
- report section for local runtime preflight evidence;
- checker support for the blocked status and preflight section;
- focused tests proving blocked preflight writes artifacts and suppresses proof
  execution.

Verification:

- `.venv/bin/ruff format --check scripts/run_molmo_planner_proof_bundle_from_requests.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff check scripts/run_molmo_planner_proof_bundle_from_requests.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py`
- Local blocked evidence: `output/debug-phase99-local-runtime-preflight-blocked/proof_bundle_run_manifest.json`
