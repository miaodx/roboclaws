# Phase 113-01: Runtime Assets Grasp Cache Preflight

## Goal

Bind grasp-cache availability evidence to the same MolmoSpaces runtime
`ASSETS_DIR` root used by the exact proof command.

## Tasks

- Derive the runtime assets root from `planner_scene.scene_xml`.
- Prefer that root over process-local defaults when building
  `grasp_cache_availability_preflight`.
- Record symlink-resolved probe paths for rigid grasp loader files.
- Render resolved loader/object paths in the shared proof-bundle report.
- Checker-gate the new fields when present.
- Regenerate the proof-bundle report from Phase 109 missing-cache evidence.

## Acceptance

- The Phase 113 artifact reports `assets_dir_source=planner_scene`.
- The report shows the runtime `~/.cache/molmospaces/assets/...` root.
- The droid loader probe resolves through the local cache shard
  `grasps/droid/20251116/Bread_1/...`.
- Focused ruff, pytest, checker, and artifact-derived report checks pass.

## Result

Completed on 2026-05-10. The Phase 113 dry-run report renders
`Grasp Cache Availability Preflight` using the runtime assets root derived from
the planner scene XML. The same report shows symlink-resolved droid and
droid-objaverse probe paths under `~/.cache/molmo-spaces-resources/grasps/...`
while preserving the loader-relative paths used by MolmoSpaces.

Artifact:
`output/debug-phase113-runtime-assets-grasp-cache-preflight/report.html`.
