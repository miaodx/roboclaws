---
refactor_scope: runtime-render-state-parity
status: DONE
accepted_severities:
  - P0
  - P1
  - P2
last_verified: 2026-06-05
---

# Runtime Render State Parity

**Status:** DONE
**Created:** 2026-06-05
**Source:** `$intuitive-reduce-entropy` audit after repeated MuJoCo/Isaac/Genesis
visual-parity refactors and the user-reviewed box-open mismatch.
**Workflow:** `$intuitive-flow` architecture/refactor route. This file is the
canonical gate for the slice until it is promoted into a larger GSD phase.

## Problem

The scene-camera comparison currently passes only MuJoCo runtime object center
positions into candidate renderers. Genesis applies those as translation-only
visual overlays, and Isaac mostly consumes prepared static USD state. That can
make object positions line up while articulated child state still diverges.

The concrete failure is `Box_10`: MuJoCo renders closed flaps from live `qpos`,
while Isaac/Genesis can still show an open/static-rest visual state. Existing
diagnostics may report `runtime_pose_match` because they compare only object
center distance, not child joint/articulation state.

## Goal

Create an explicit runtime render-state contract so reports can distinguish:

- `static_prepared_state`;
- `translation_only_runtime_pose`;
- `articulated_runtime_state_applied`;
- `articulated_runtime_state_unsupported`.

The first implementation slice must make articulated state visible and block
false-green parity for articulated objects. It does not need to solve real
Genesis/Isaac joint application in the same commit.

## Non-Goals

- Do not tune Isaac or Genesis lighting in this slice.
- Do not add a new public runnable task.
- Do not claim Genesis or Isaac full cleanup backend support.
- Do not add one-off per-object-id rendering hacks.
- Do not hide unsupported articulation by changing visual thresholds.

## Accepted Checklist

- [x] P0: MuJoCo state exposes a named runtime render-state payload for objects,
  including body pose, articulation joints under the object subtree, and qpos
  values needed to interpret those joints.
- [x] P0: Scene-camera requests carry this runtime render-state payload to
  candidate lanes separately from legacy `runtime_object_positions`.
- [x] P0: Genesis movable-object visibility diagnostics no longer call an
  articulated object a `runtime_pose_match` solely because the parent bounds
  center is close.
- [x] P1: Reports show articulated object counts and unsupported-articulation
  status near the existing Genesis movable-object visibility table.
- [x] P1: CI-safe tests cover a box-like object with flap joints and verify the
  report/manifest classify it as unsupported rather than pose-matched.
- [x] P2: Existing translation-only pose overlay behavior remains available for
  non-articulated movable clutter.

## Evidence Ladder

- L1: Unit/contract tests for runtime render-state extraction and diagnostics.
- L2: Scene-camera report test proving unsupported articulation is visible in
  HTML and manifest data.
- L4: Later local GPU rerun showing `Box_10` either matches MuJoCo in Genesis
  and Isaac, or remains explicitly blocked by unsupported articulation.

## Stop Condition

Stop this slice when focused tests pass and the generated diagnostics can no
longer label an articulated object with only translation/position parity as
`runtime_pose_match`.

## Verification

2026-06-05:

- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_scene_camera_comparison.py tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py`
  passed.
- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_scene_camera_comparison.py::test_scene_camera_request_carries_runtime_render_state_for_candidate_lanes tests/contract/molmo_cleanup/test_scene_camera_comparison.py::test_scene_camera_genesis_movable_visibility_blocks_articulated_pose_false_green tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py::test_worker_runtime_render_state_records_object_articulation_joints`
  passed.
- `ruff check roboclaws/household/scene_camera_comparison.py scripts/genesis_cleanup/genesis_backend_worker.py scripts/molmo_cleanup/molmospaces_subprocess_worker.py tests/contract/molmo_cleanup/test_scene_camera_comparison.py tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py`
  passed.
- `ruff format --check roboclaws/household/scene_camera_comparison.py scripts/genesis_cleanup/genesis_backend_worker.py scripts/molmo_cleanup/molmospaces_subprocess_worker.py tests/contract/molmo_cleanup/test_scene_camera_comparison.py tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py`
  passed.
- `python -m py_compile roboclaws/household/scene_camera_comparison.py scripts/genesis_cleanup/genesis_backend_worker.py scripts/molmo_cleanup/molmospaces_subprocess_worker.py`
  passed.

The synthetic box/flap report test now records
`articulated_runtime_state_unsupported` even when parent geometry delta is
`0.0`, so translation/position parity no longer produces a false
`runtime_pose_match` for articulated objects.

## Parked Items

- Apply articulated child transforms in the Genesis visual package instead of
  only reporting unsupported articulation.
- Apply MuJoCo runtime articulation state to Isaac prepared USD or explicitly
  classify the Isaac lane as static-prepared for articulated objects.
- Create a corpus-level registry for drawers, doors, lids, appliances, and
  other categories after the first box-focused gate is reliable.
- Revisit lighting parity after state parity is honest.
