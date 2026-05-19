# MolmoSpaces Fallback Runtime Alias Discovery

**Status:** Completed on 2026-05-10
**ADR:** `docs/adr/0055-discover-fallback-runtime-aliases-from-keyerrors.md`
**GSD phase:** `.planning/milestones/v1.98-phases/64-molmospaces-fallback-runtime-alias-discovery/`

## Problem

Phase 63 filtered invalid upstream/display aliases out of generated fallback
commands, but that left the current artifact with no executable fallback
commands. Phase 62 proof outputs already contain exact-scene valid-name lists
inside `KeyError` blocker messages. The runner should mine those lists for
runtime sibling aliases before asking for another local proof execution.

## Scope

- Merge prior proof-bundle selection exclusions into the prior result summary
  so a warmed fallback manifest can be used as the single prior input.
- Discover runtime sibling aliases from prior `KeyError` valid-name lists.
- Feed discovered runtime aliases into generated fallback request selection.
- Render discovered aliases in the proof-bundle runner report.
- Extend checker and tests for discovered-alias evidence.
- Dry-run the current cleanup artifact against the Phase 62 warmed fallback
  manifest.

## Result

The proof-bundle runner can now derive exact-scene runtime sibling aliases from
prior fallback `KeyError` evidence and use them as bounded generated fallback
commands.

The local dry-run:

- used `output/debug-real-binding/run_result.json`;
- used `output/debug-phase62-warmed-fallback-execute/proof_bundle_run_manifest.json`
  as the prior manifest;
- generated four fallback proof commands;
- discovered five runtime aliases;
- kept four upstream/display aliases filtered;
- passed the proof-bundle runner checker.

Discovered aliases included:

- `book_be4d759484637aeb579b28e6a954b18d_1_1_8`
- `book_be4d759484637aeb579b28e6a954b18d_1_2_8`
- `shelf_140ccb7e1f5028c7d773229dfe6e1a04_1_1_2`
- `bowl_46a21212675e4d90993a86b1232e6f40_1_1_8`
- `sink_07e796f32d0d3efce9acf4be00f3bc53_1_1_5`

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase64-runtime-alias-discovery-dry-run --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase62-warmed-fallback-execute/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 2`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase64-runtime-alias-discovery-dry-run`
