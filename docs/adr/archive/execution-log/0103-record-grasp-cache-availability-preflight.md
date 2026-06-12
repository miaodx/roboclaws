# 0103. Record Grasp Cache Availability Preflight

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0102 routed the exact `Bread_1` blocker to grasp-cache mitigation before
another retry. That decision identified the route, but it still left one gap:
the proof-bundle report did not show whether `Bread_1` was missing as an
object asset or whether only the rigid grasp files consumed by MolmoSpaces'
loader were absent.

Upstream `load_grasps_for_object` checks three rigid-object cache locations:

- `grasps/droid/{asset_uid}/{asset_uid}_grasps_filtered.npz`
- `grasps/droid_objaverse/{asset_uid}/{asset_uid}_grasps_filtered.npz`
- `grasps/rum/{asset_uid}/{asset_uid}_grasps_filtered.json`

The droid joint file may satisfy upstream folder probing, but it does not make
the rigid-object loader ready.

## Decision

Proof-bundle manifests now include
`grasp_cache_availability_preflight` whenever they are assembled from a
grasp-feasibility mitigation decision.

The preflight:

- probes the exact rigid loader files for each missing grasp asset;
- reports the droid joint file as `has_grasp_folder_only`;
- records whether matching local THOR object XML/OBJ assets exist;
- classifies each missing asset as `ready` or `missing_cache`;
- renders a `Grasp Cache Availability Preflight` report panel;
- is validated by the proof-bundle runner checker.

## Consequences

- `Bread_1` evidence now separates "object asset exists" from "rigid grasp
  cache missing."
- Reports show the precise paths to generate, restore, or install before an
  exact retry.
- Source rotation remains separate from cache mitigation.
- The next implementation slice should generate or restore one of the rigid
  loader-compatible cache files for `Bread_1`, then retry the exact proof to
  determine whether the blocker moves to collision masking or clears.

## Evidence

Implemented in Phase 112 on 2026-05-10.

Artifact:

- `output/debug-phase112-grasp-cache-availability-preflight/proof_bundle_run_manifest.json`
- `output/debug-phase112-grasp-cache-availability-preflight/report.html`

Key result:

- `grasp_cache_availability_preflight.status=missing_cache`
- `cache_missing_asset_uids=["Bread_1"]`
- `object_asset_status=present`
- all rigid loader probes for droid, droid-objaverse, and RUM sources report
  `exists=false`
