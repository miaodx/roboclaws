# 0075. Match Proof Selection Memory by Cleanup Pair

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0074 makes grasp-feasibility blocker kind/detail durable inside proof
request selection. That memory still depends on matching prior proof results
primarily by `request_id`.

Request IDs are stable for a single manifest shape, but they are not the
cleanup contract identity. If proof requests are regenerated after substep
ordering or manifest composition changes, the same cleanup object/target pair
can receive a different request ID and lose prior blocker memory.

## Decision

Proof request selection should match prior proof results in this order:

1. exact `request_id`;
2. cleanup `object_id` plus `target_receptacle_id`.

Selection artifacts record `prior_result_match_kind` so reviewers can see
whether memory came from exact request identity or object/target cleanup
identity. Generated fallback provenance, excluded requests, target blockers,
grasp blockers, and runner report tables all render that match kind.

## Consequences

- Regenerated manifests can still avoid retrying known grasp-infeasible cleanup
  pairs.
- Exact request-id matches remain preferred when available.
- Object/target matching is intentionally cleanup-facing; it does not match on
  private planner aliases alone and does not claim a new alias is feasible.

## Evidence

Phase 84 validates cleanup-pair matching with focused tests for:

- excluding a regenerated request whose prior result has a different request ID;
- preserving `prior_result_match_kind=object_target`;
- retaining request-id match behavior for existing manifests;
- rendering/checking `Prior match` in runner reports.

Verification on 2026-05-10:

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- Manual regenerated-request selection check reports
  `selected_request_ids=[]`, `excluded_count=1`,
  `prior_result_match_kind=object_target`, and
  `grasp_feasibility_blocker_count=1`.
