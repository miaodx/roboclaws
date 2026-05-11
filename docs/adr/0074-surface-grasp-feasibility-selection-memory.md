# 0074. Surface Grasp-Feasibility Selection Memory

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0073 classifies proof results that clear robot placement but fail through
post-placement grasp/candidate rejection as `grasp_feasibility`.

The next gap is selection memory. Proof request selection already excludes
generic task-feasibility-blocked requests and remembers blocked fallback alias
pairs, but it does not preserve the specific blocker kind through those
selection artifacts. That makes grasp-infeasible requests visible in result
summaries but easy to lose when deciding what to retry next.

## Decision

Carry `task_feasibility_blocker_kind` and
`task_feasibility_blocker_summary` into proof request selection artifacts.

Selection now records those fields on:

- excluded source requests;
- generated fallback request provenance;
- filtered fallback alias pairs;
- target-feasibility blocker rows.

The runner report also renders a dedicated `Grasp Feasibility Blockers` view and
`Grasp blockers` metric so review can distinguish grasp/candidate rejection
from broader target task-feasibility failure.

## Consequences

- Future selection phases can skip or replace grasp-infeasible exact aliases
  without reopening per-proof report tables.
- Existing generic task-feasibility filters remain compatible because blocker
  kind/detail fields are optional.
- This still does not claim planner-backed cleanup readiness; it only preserves
  memory about why a proof request should not be retried unchanged.

## Evidence

Phase 83 validates the selection-memory path with focused tests for:

- source-request grasp blocker propagation;
- generated fallback provenance;
- filtered fallback pair memory;
- runner report rendering;
- checker validation of the new visual fields.

Verification on 2026-05-10:

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- Manual Phase 81 artifact selection check reports
  `excluded_count=1`, `grasp_feasibility_blocker_count=1`,
  `fallback_status=exhausted`, and blocker detail
  `17 grasp failures; 15 candidate-removal calls`.
