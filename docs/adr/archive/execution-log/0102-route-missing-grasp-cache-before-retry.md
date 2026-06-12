# 0102. Route Missing Grasp Cache Before Retry

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0101 classified the exact bread blocker as
`subkind=grasp_cache_missing` while preserving the top-level
`grasp_feasibility` blocker category. That made the evidence visible, but the
runner still left the next action implicit: rotate to another source pool or
mitigate the missing cached grasps for `Bread_1`.

Those are different routes. Source rotation can produce unrelated unproven
requests, but it cannot make a known exact-scene `Bread_1` retry valid if the
upstream grasp loader still raises before collision masking.

## Decision

Proof-bundle manifests now include a
`grasp_feasibility_mitigation_decision` summary. When grouped
grasp-feasibility evidence contains missing cached grasp assets, the primary
route is `grasp_cache_mitigation`.

The decision still records source-rotation state separately. A runner may show
selected unproven source-rotation requests, but those requests are not treated
as a retry path for the known missing-cache asset.

## Consequences

- Reports now show the cache-vs-rotation decision as a first-class visual panel.
- `Bread_1` is routed to grasp-cache mitigation before another exact retry.
- Source rotation remains available for selected unproven requests, but no
  longer hides the known missing-cache blocker.
- The next implementation slice should either restore/generate the missing
  grasp cache for `Bread_1` or explicitly execute different selected source
  requests without claiming that `Bread_1` has been mitigated.

## Evidence

Implemented in Phase 111 on 2026-05-10.

Artifact:

- `output/debug-phase111-grasp-cache-routing-decision/proof_bundle_run_manifest.json`
- `output/debug-phase111-grasp-cache-routing-decision/report.html`

Key result:

- `primary_route=grasp_cache_mitigation`
- `recommendation=mitigate_missing_grasp_cache_before_retry`
- `missing_grasp_asset_uids=["Bread_1"]`
- `source_rotation_state=available_for_unproven_requests`
