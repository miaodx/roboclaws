# 0076. Ingest Standalone Prior Proof Results

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0074 and ADR-0075 make prior proof memory durable enough to avoid
retrying exact-scene cleanup pairs already known to be grasp-infeasible. The
proof-bundle runner could consume prior proof-bundle manifests, but some of the
best diagnostic evidence comes from standalone planner-probe `run_result.json`
artifacts, such as the Phase 81 warmed probe that captured post-placement
candidate rejection for `Book_23`.

That left a workflow gap: reviewers could see standalone probe evidence in its
own report, but the bundle runner selection path could not consume it without
wrapping it in a synthetic prior bundle. The architecture had two useful
artifact shapes and only one reusable selection interface.

## Decision

The proof-bundle runner will accept standalone prior planner-probe run results
through `--prior-planner-probe-run-result`.

Before request selection, each standalone probe result is normalized into the
same private **Planner Proof Result Summary** shape used by executed
proof-bundle manifests. The normalization reads the cleanup-facing binding from
`manipulation_evidence.requested_cleanup_primitive_binding` or
`cleanup_primitive_binding`, derives a stable synthetic request ID, preserves
the source run-result/report paths, and then lets existing selection memory
match by request ID first or cleanup object/target pair.

## Consequences

- Standalone local-dev probe evidence can directly inform proof request
  selection without a manual wrapper manifest.
- Bundle manifests and standalone probes now share the same selection,
  fallback, blocker, and report rendering path after normalization.
- The runner remains conservative: missing cleanup binding in a standalone
  probe means no prior proof summary is created.
- Standalone probe ingestion does not prove feasibility or change cleanup
  primitive readiness; it only carries prior blocker evidence into the next
  proof-bundle selection pass.

## Evidence

Phase 85 validates standalone prior probe ingestion with focused tests for:

- loading a standalone planner-probe `run_result.json`;
- normalizing cleanup object/target binding into a prior proof result summary;
- excluding a regenerated proof request by cleanup-pair memory;
- preserving `prior_result_match_kind=object_target`;
- carrying `grasp_feasibility` blocker detail into runner reports.

Verification on 2026-05-10:

- `uv run ruff check scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `uv run ruff format --check scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_ingests_standalone_prior_probe_run_result_by_cleanup_pair tests/test_check_molmo_planner_proof_bundle_runner_result.py::test_checker_accepts_partial_selection_with_exhausted_fallbacks`
- Manual dry-run against `output/debug-real-binding/run_result.json` plus
  `output/debug-phase81-post-placement-rejections/run_result.json` selected one
  remaining request, excluded the known grasp-infeasible cleanup pair by
  `object_target`, rendered `grasp_feasibility`, and passed the runner checker.
