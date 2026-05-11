# 0104. Bind Grasp Cache Preflight To Runtime Assets Dir

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0103 added grasp-cache availability preflight, but MolmoSpaces has two
relevant cache roots:

- `DATA_CACHE_DIR`, where archives are stored by version;
- `ASSETS_DIR`, the runtime symlink root used by the loader.

The exact proof command carries a planner scene XML under the runtime
`ASSETS_DIR`. If the report displays only the data-cache root, it can still
name the right missing file shape, but it does not show the actual path the
loader tried.

## Decision

Derive the preflight assets root from `planner_scene.scene_xml` when a
proof-bundle manifest has a planner scene. The preflight records
`assets_dir_source=planner_scene` and keeps both:

- loader-relative paths, such as
  `grasps/droid/Bread_1/Bread_1_grasps_filtered.npz`;
- symlink-resolved paths, such as
  `~/.cache/molmo-spaces-resources/grasps/droid/20251116/Bread_1/Bread_1_grasps_filtered.npz`.

The proof-bundle report renders the resolved paths, and the checker validates
them when present.

## Consequences

- Missing-cache reports now match the exact runtime loader root.
- The next cache-generation or restore slice can target the symlink-resolved
  storage location while preserving loader-relative semantics.
- Environment or default roots remain fallback behavior only when no planner
  scene XML is available.
- Cleanup Artifact Reports remain unchanged; this is still an opt-in
  planner/proof report diagnostic.

## Evidence

Implemented in Phase 113 on 2026-05-10.

Artifact:

- `output/debug-phase113-runtime-assets-grasp-cache-preflight/proof_bundle_run_manifest.json`
- `output/debug-phase113-runtime-assets-grasp-cache-preflight/report.html`

Key result:

- `assets_dir_source=planner_scene`
- `assets_dir=/home/mi/.cache/molmospaces/assets/...`
- droid rigid loader probe resolves to
  `/home/mi/.cache/molmo-spaces-resources/grasps/droid/20251116/Bread_1/Bread_1_grasps_filtered.npz`
