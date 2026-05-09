# 44-01 Planner Proof Bundle Cleanup Plan

## Goal

Let ADR-0003 cleanup artifacts use multiple bound planner proofs so every
cleaned object can be matched to its own proof-backed primitive executor.

## Status

Completed 2026-05-10.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context.
2. [x] Add a proof-bundle schema/helper for multiple strict planner proof
   attachments.
3. [x] Preserve backward-compatible single-proof attachment behavior.
4. [x] Extend the cleanup harness to accept/select multiple proof attachments
   by observed handle and target fixture.
5. [x] Render multiple attached proof views in the shared Cleanup Artifact
   Report.
6. [x] Update checker/bridge validation so full proof coverage can pass the
   existing cleanup primitive and planner bridge gates.
7. [x] Add focused tests for full coverage, partial coverage, mismatches, and
   report rendering.
8. [x] Run focused verification gates.

## Acceptance

- Default ADR-0003 cleanup runs remain `api_semantic`.
- Existing single `--planner-proof-run-result` artifacts remain accepted.
- Multiple strict bound proofs can be attached to one cleanup run.
- The harness uses only the proof whose binding matches the current observed
  handle and target fixture.
- A full synthetic cleanup with matching proof coverage for every cleaned object
  passes `require_planner_backed_cleanup_primitives` and
  `require_planner_cleanup_bridge_ready`.
- Partial or mismatched proof bundles leave uncovered objects on
  `api_semantic` and keep the bridge blocked.
- The report keeps one shared visual underlay and shows every attached proof's
  initial/final views.

## Verification

- Passed: `uv run ruff check roboclaws/molmo_cleanup/planner_proof_attachment.py roboclaws/molmo_cleanup/planner_proof_bundle.py roboclaws/molmo_cleanup/planner_cleanup_bridge.py roboclaws/molmo_cleanup/manipulation_provenance.py roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/__init__.py examples/molmospaces_realworld_cleanup.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_planner_proof_attachment.py tests/test_molmo_planner_cleanup_bridge.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py`
- Passed: `uv run ruff format --check roboclaws/molmo_cleanup/planner_proof_attachment.py roboclaws/molmo_cleanup/planner_proof_bundle.py roboclaws/molmo_cleanup/planner_cleanup_bridge.py roboclaws/molmo_cleanup/manipulation_provenance.py roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/__init__.py examples/molmospaces_realworld_cleanup.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_planner_proof_attachment.py tests/test_molmo_planner_cleanup_bridge.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py`
- Passed: `./scripts/run_pytest_standalone.sh -q tests/test_molmospaces_realworld_cleanup.py tests/test_molmo_planner_probe_primitive_executor.py tests/test_molmo_planner_proof_attachment.py tests/test_molmo_planner_cleanup_bridge.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py`
- Passed: current real visual artifact checker against
  `output/molmospaces-planner-cleanup-bridge-readiness/run_result.json` with
  bridge accepted as blocked.

## Risks

- Treating a proof bundle as blanket target readiness could hide a missing
  object binding. Bundle readiness must require each selected proof to remain
  strict and object/target-bound.
- Changing single-proof fields could break existing artifacts and checker
  gates. Keep the single-proof path backward compatible.

## Completion Notes

`planner_backed_cleanup_proof_bundle_v1` now lets one cleanup artifact attach
multiple strict planner proofs without overwriting their visual files. The
ADR-0003 cleanup harness accepts repeated `--planner-proof-run-result` values
or `planner_proof_run_results` in-process, selects the attachment matching the
current observed handle and target fixture, and keeps uncovered objects on the
normal semantic path.

The synthetic seed-7 regression now proves full cleanup gate readiness with
five bound proofs: the cleanup primitive gate and planner cleanup bridge both
pass only when every cleaned object has matching proof-backed subphase
evidence. This does not claim live multi-object proof generation.
