# 0123. Render Proof Command Semantic Subphases

Date: 2026-05-10

## Status

Accepted

## Context

The MolmoSpaces cleanup reports use the shared semantic loop vocabulary:
`nav, pick, nav, open?, place`. ADR-0122 made the proof-bundle runner report the
requested proof-strength horizon before execution, but the generated proof
command rows still exposed mostly shell arguments. Reviewers could see that a
command was selected for an object/target pair, but not the cleanup subphase
sequence that command was meant to prove.

## Decision

Proof-bundle command manifest rows now preserve the cleanup tools and render
display-ready semantic subphases:

- raw cleanup tool phases;
- compact display labels such as `nav`, `pick`, and `place`;
- role details such as `object`, `target`, `surface`, or `inside`; and
- the same report rail style used by cleanup semantic substeps.

The proof-bundle runner checker validates the semantic subphase rail whenever a
command manifest row includes it.

## Consequences

- Dry-run proof reports show both command-strength intent and cleanup-loop
  intent before local RBY1M/CuRobo execution.
- The command report stays aligned with the shared cleanup visual underlay
  instead of becoming another shell-only proof view.
- This is still command intent, not proof success; strict proof artifacts remain
  authoritative after execution.

## Evidence

Implemented in Phase 132 on 2026-05-10.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_writes_dry_run_manifest_and_report_from_inline_requests tests/test_molmo_cleanup_report.py::test_planner_proof_bundle_runner_report_renders_commands tests/test_check_molmo_planner_proof_bundle_runner_result.py::test_checker_accepts_valid_runner_artifact`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json --output-dir output/debug-phase132-proof-command-subphases-dry-run --runner-python python --probe-script scripts/run_molmo_planner_manipulation_probe.py --cleanup-script examples/molmospaces_realworld_cleanup.py --molmospaces-python /home/mi/.cache/molmospaces/venv/bin/python --steps 2 --exclude-prior-covered --prior-covered-min-proof-steps 2`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase132-proof-command-subphases-dry-run/proof_bundle_run_manifest.json --require-proof-execution-horizon --min-selected-requests 1`
