# 0098. Require Valid Cleanup Scene Binding

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0097 correctly moved exact pickup candidate binding to the upstream pickup
selection hook, but the local Phase 106 evidence had a weaker premise than the
ADR intended. The probe was launched with a stale cleanup scene XML path:

`/home/mi/.cache/molmospaces/assets/objathor_base/2023_09_23/val_0.xml`

That path did not exist, so the probe reported `cleanup_scene_xml_missing` and
the upstream sampler fell back to its default scene before producing the
invalid planner-object `KeyError`. The run still proved the adapter hook fired,
but it was not strong evidence about the exact cleanup scene.

The canonical seed-10 cleanup artifact already carried the valid scene path in
its planner proof request manifest:

`/home/mi/.cache/molmospaces/assets/L3RtcC9yb2JvY2xhd3MtbW9sbW9zcGFjZXMtc3Bpa2UvbW9sbW9zcGFjZXM/scenes/procthor-10k-val/val_0.xml`

Future exact-scene proof evidence needs a hard checker gate for this condition,
or a missing scene path can masquerade as an alias or task-feasibility blocker.

## Decision

Add **Valid Cleanup Scene Binding** as a required checker mode for exact-scene
planner probes.

The planner manipulation checker now supports
`--require-cleanup-scene-bound`. When enabled, it requires:

- `cleanup_task_config.applied=true`;
- a non-empty `cleanup_task_config.scene_xml`;
- the scene XML path exists on disk;
- no `cleanup_scene_xml_missing` blocker is present.

The shared planner report now renders exact task config blocker codes in both
standalone planner reports and proof-bundle result cards, so stale scene paths
are visible in `report.html` instead of only in JSON.

## Consequences

- The old Phase 106 artifact is no longer acceptable under the stricter
  exact-scene gate because it contains `cleanup_scene_xml_missing`.
- A corrected Phase 107 rerun against the canonical seed-10 scene passed the
  new gate and kept all shared visual views.
- The corrected evidence shows the requested bread alias exists in the valid
  cleanup scene. The exact pickup adapter binds the pool from 17 unrelated
  candidates to that requested alias, robot placement succeeds, and the run
  now blocks after one grasp failure with zero candidate-removal calls.
- The next blocker is therefore post-placement grasp feasibility for the exact
  requested object, not invalid aliasing and not missing scene binding.
- This does not change ADR-0097's adapter decision; it strengthens the proof
  quality gate required before interpreting exact-scene blockers.
