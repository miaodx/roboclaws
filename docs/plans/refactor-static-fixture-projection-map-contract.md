---
refactor_scope: static-fixture-projection-map-contract
status: DONE
accepted_severities:
  - P1
  - P2
last_verified: 2026-06-19
---

# Refactor Scope: Static Fixture Projection Map Contract

## Status

DONE

## Target

Collapse `static_fixture_projection` out of the current Nav2/Base Navigation Map
contract surface. The current map code needs static landmarks for bundle
generation and route checks; it does not need a second public map/projection
concept beside Base Navigation Map and Runtime Metric Map.

## Accepted Severities

- P1: stale reachable APIs or tests that present `static_fixture_projection` as
  a current map truth or current bundle projection API.
- P2: target-local naming and call-shape cleanup that makes the current map
  ownership clearer without adding a new abstraction layer.

## Accepted Cleanup Checklist

- Replace `static_fixture_projection_from_bundle()` with a current bundle
  projection helper that exposes static landmarks only as internal/static map
  geometry.
- Rename Nav2 bundle writer and route-validation inputs from
  `static_fixture_projection` to `static_landmarks`.
- Keep `metric_map_from_bundle()` as the Base Navigation Map projection.
- Update current map bundle tests/scripts/callers to the new names and remove
  compatibility shims.
- Leave historical report/checker artifact readers for a separate cleanup slice
  unless they block the current API cleanup.

## Parked Cross-Seam / Future Ideas

- Consolidate B1 Map 12 label/review/promote tools.
- Rename or delete historical Agibot/cleanup artifact fields that still read old
  `static_fixture_projection` payloads.
- Revisit skill docs that mention old fixture projection guidance.

## Evidence Ladder

L2 contract tests for the map bundle and route contract, plus lint/format checks
for touched files.

## Stop Condition

The current `roboclaws/maps` Nav2 bundle API no longer exposes
`static_fixture_projection` as a bundle projection concept, focused map tests
pass, and remaining old-name references are either historical artifact readers
or parked cross-seam work.

## Execution Log

- 2026-06-19: Scope opened after user explicitly removed backward-compatibility
  requirements and asked to optimize for clearer map architecture.
- 2026-06-19: Replaced the current Nav2 bundle/route API with
  `metric_map + static_landmarks`, migrated checked-in Nav2 map assets to
  `semantics.static_landmarks`, and left old `static_fixture_projection`
  payloads only in historical/cleanup artifact surfaces.
- 2026-06-19: Verified with focused map, realworld, cleanup, B1 map, and
  operator preview tests plus Ruff lint/format checks.
