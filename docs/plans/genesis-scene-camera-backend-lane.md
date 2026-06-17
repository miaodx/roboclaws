---
refactor_scope: genesis-scene-camera-visual-fidelity
status: PARK
accepted_severities:
  - P0
  - P1
  - P2
last_verified: 2026-06-04
---

# Genesis Scene-Camera Backend Lane

**Status:** PARK
**Created:** 2026-06-04
**Source:** Genesis World submodule addition and follow-up discussion about
adding Genesis as a backend variant like the Isaac path.
**Workflow:** `intuitive-flow` discussion plus `grill-with-docs-batch`
alignment. Keep this as the pre-GSD source of truth until it is promoted into a
phase or implemented directly as a scoped comparison slice.

**Retirement note, 2026-06-14:** the active Genesis scene-camera lane was
retired during the reduce-entropy cleanup. This file remains historical
evidence for the renderer experiment; current scene-camera work uses MuJoCo and
Isaac only.

## Problem

Roboclaws already has a render-only MolmoSpaces/MuJoCo versus Isaac scene-camera
comparison. That comparison is the right place to ask whether another simulator
can render the same canonical scene-camera views, because it does not execute
cleanup, pick/place, scoring, or robot control.

Genesis World is now available as a vendored submodule at
`vendors/genesis-world`. It supports USD import, camera sensors, RGB rendering,
and optional depth/segmentation outputs. However, adding Genesis directly as a
cleanup backend would mix two claims:

- Genesis can render the same prepared MolmoSpaces scene-camera request.
- Genesis can implement the Roboclaws household cleanup backend contract.

The first claim is smaller and should be proven first. The current comparison
code has the camera-control contract we need, but it still hard-codes two lanes:
`molmospaces-mujoco` and `isaaclab-prepared-usd`.

## Goals

- Add Genesis as an opt-in third lane for the existing scene-camera comparison.
- Treat Genesis as a backend variant / candidate lane, not a new public task or
  capability profile.
- Load the same prepared MolmoSpaces USD scene used by the Isaac lane, rather
  than introducing a separate scene conversion path in the first slice.
- Reuse the canonical Roboclaws camera-control request:
  `roboclaws.camera_control.render_views` with explicit `eye`, `target`, `up`,
  lens, lighting profile, color profile, and view ids.
- Keep Genesis dependencies and runtime state outside the core Roboclaws
  `.venv/`, likely in `.venv-genesis/`.
- Shape the Genesis worker as an early `GenesisSubprocessBackend` so later
  cleanup support can reuse the same runtime, USD loading, rendering, metadata,
  and artifact boundaries.
- Preserve honest report language: the first accepted result is render-only
  scene-camera evidence, not cleanup support.

## Non-Goals

- Do not add `backend=genesis_subprocess` to `household-cleanup` in this first
  slice.
- Do not claim Genesis manipulation, RBY1M robot control, planner-backed
  cleanup, or physical robot parity.
- Do not add Genesis dependencies to the core `.venv/` or `pyproject.toml`
  default runtime.
- Do not replace MuJoCo as the baseline lane or Isaac as the existing prepared
  USD comparison lane.
- Do not create a new public runnable task for Genesis visual comparison.
- Do not silently fall back to MuJoCo, Isaac, placeholder images, or synthetic
  output when Genesis runtime or rendering fails.
- Do not require depth or segmentation evidence for the first render-only
  acceptance gate.

## Accepted Alignment Decisions

| # | Area | Decision | Rationale |
|---|------|----------|-----------|
| 1 | First slice | Target `scene-camera-comparison` only. | It proves the shared camera-control contract before cleanup state, RBY1M pose, or manipulation enters. |
| 2 | Artifact source | Load the same prepared MolmoSpaces USD used by Isaac. | This makes Genesis a fair third render lane and avoids conflating rendering with scene conversion. |
| 3 | Claim boundary | Claim only that Genesis rendered the same canonical camera views. | Cleanup/backend parity needs scene index, state mutation, primitive provenance, and report gates. |
| 4 | Comparison shape | Refactor toward a baseline-plus-candidate lane registry. | Hard-coding a third lane would deepen the current two-lane coupling. |
| 5 | Command surface | Keep the existing comparison command with an opt-in Genesis lane. | Genesis is a backend variant/candidate lane, not a public task taxonomy change. |
| 6 | Later cleanup | Shape the worker so cleanup can reuse it later. | The first implementation should not be a throwaway benchmark-only script. |

## Implementation Shape

### Layer 1: Runtime And Worker

Create an isolated Genesis runtime, for example:

```text
.venv-genesis/
```

The first setup command can be documented by the implementation, but it should
not modify normal Roboclaws dependency installation. Genesis requires PyTorch to
be installed separately for the target platform, so the runtime preflight must
fail with a clear message when Python, Torch, Genesis, renderer, or display/GPU
requirements are missing.

Add a subprocess boundary similar in spirit to Isaac:

```text
roboclaws/household/genesis_backend.py
scripts/genesis_cleanup/genesis_backend_worker.py
```

The worker should initially support:

- `init`: load a prepared USD scene, record runtime metadata, and write a state
  artifact.
- `camera_views`: read `camera_control_request.json`, render all requested
  views, write image artifacts, and return a Roboclaws lane payload.

The wrapper should avoid importing Genesis during normal Roboclaws module
startup. CI-safe tests can use a fake worker protocol; real Genesis rendering is
local-dev evidence.

### Layer 2: Scene-Camera Lane Registry

Refactor the scene-camera comparison from fixed two-lane assumptions toward a
small registry:

```text
baseline: molmospaces-mujoco
candidates:
  - isaaclab-prepared-usd
  - genesis-prepared-usd
```

The first implementation can keep pairwise diagnostics as baseline-to-candidate
instead of making every diagnostic fully N-way. The report should still make the
visual review easy:

- contact sheet with all successful lanes;
- per-view images for MuJoCo, Isaac, and Genesis when available;
- pairwise visual metrics from MuJoCo baseline to each candidate;
- explicit lane failure rows when a candidate fails.

### Layer 3: Opt-In Command Surface

Keep the existing `just molmo::scene-camera-comparison` route and add an
opt-in Genesis control, for example:

```bash
just molmo::scene-camera-comparison genesis=on \
  scene_usd_path=output/isaaclab/flattened-semantic-usd/.../scene_semantic.usda
```

The exact flag name is an implementation default. The command must preflight the
Genesis Python executable when Genesis is requested and fail before rendering if
the runtime is unavailable.

## Lane Payload Contract

The Genesis lane should return the same core fields used by the existing lanes:

- `status`;
- `python_executable`;
- `runtime`;
- `scene_usd`;
- `scene_load`;
- `view_variant`;
- `visual_artifact_provenance`;
- `camera_control_api`;
- `camera_request_schema`;
- `calibration_status`;
- `lighting_profile`;
- `lighting_diagnostics`;
- `color_profile`;
- `color_management`;
- `lens`;
- `images`;
- `views`;
- `camera_control_request`.

Genesis-specific diagnostics can be added under `genesis_runtime` or
lane-local fields, but they must stay report evidence and must not change
agent-facing MCP tools or cleanup Agent View.

## Later Cleanup Path

This slice should leave a clear path to `household-cleanup
backend=genesis_subprocess`, but must not implement it yet.

Later cleanup support will need:

- a Genesis scene index that maps public object/receptacle handles to Genesis
  entities or USD prims;
- scenario generation from Genesis-loaded scene state;
- state mutation for held objects, locations, and open/close state;
- cleanup primitive methods compatible with `CleanupBackendSession`;
- honest primitive provenance, likely `genesis_semantic_pose` until real control
  exists;
- report/checker gates that reject placeholder visuals, fallback lanes, and
  unproven cleanup claims.

## Test And Acceptance

CI-safe acceptance:

- unit tests for the Genesis wrapper using fake worker JSON;
- report tests showing three-lane contact sheets and pairwise
  baseline-to-candidate metrics;
- command/recipe tests proving Genesis is opt-in and preflighted;
- import-boundary test proving normal Roboclaws imports do not import Genesis;
- failure-path tests proving missing Genesis runtime produces an explicit lane
  or preflight failure, not fallback images.

Local-dev acceptance:

```bash
just molmo::scene-camera-comparison genesis=on \
  scene_usd_path=/path/to/prepared/molmospaces/scene_semantic.usda
```

Pass criteria:

- MuJoCo baseline lane succeeds.
- Existing Isaac lane behavior is unchanged.
- Genesis lane reports real Genesis runtime metadata.
- Genesis lane loads the caller-supplied prepared USD scene.
- Genesis lane writes nonblank images for the canonical camera-control views.
- Genesis lane images are materially/texturally comparable enough for human
  review and the manifest no longer reports
  `candidate_visual_diagnostics.status=degraded_visual_fidelity`.
- Genesis lane echoes camera pose/intrinsics evidence well enough for pairwise
  geometry and visual diagnostics.
- Report and manifest label the result as render-only scene-camera evidence.

## Refactor Scope Gate

```yaml
refactor_scope: genesis-scene-camera-visual-fidelity
status: DONE
accepted_severities:
  - P0
  - P1
  - P2
last_verified: 2026-06-04
```

### Status

CONTINUE

### Target

`scripts/genesis_cleanup/genesis_backend_worker.py` and the
`scene-camera-comparison` Genesis lane diagnostics/report surface.

### Accepted Cleanup Checklist

- [x] P0: Stop treating first implementation as success. The lane is not accepted
  while the comparison manifest marks Genesis as `degraded_visual_fidelity`.
- [x] P1: Replace the current material-free `prepared_usd_visual_mesh` OBJ fallback
  with a material-preserving prepared-USD visual import path.
- [x] P1: Keep native Genesis USD/MJCF facts honest: Genesis supports both USD and
  MJCF morphs, but this MolmoSpaces prepared scene currently fails native USD
  stage import as a mixed physics graph and MJCF remains a parked spike unless
  it demonstrably beats the prepared-USD visual path.
- [x] P2: Preserve the clickable image popup/report UX and keep visual diagnostics
  explicit enough to catch future false-green render lanes.
- [x] P1: Make standalone per-view/per-lane images the primary report review
  surface, with every lane image directly clickable in the popup. Keep the
  contact sheet only as a secondary overview artifact.
- [x] P1: Put compact per-view tone metrics near each standalone image so
  MuJoCo/Isaac/Genesis color-tone differences are inspectable where the images
  are reviewed.
- [x] P1: Add a room/wall light diagnostic that separates wall or room-view
  darkness from object/material deltas and records whether a global gain is
  insufficient.
- [x] P2: Keep candidate color/luminance calibration explicit; do not hide tone
  mismatch behind generic renderer-difference language.
- [x] P1: Calibrate the Genesis renderer/color output itself so the real Genesis
  lane images are visually good enough, not merely diagnosed in the report.
- [x] P1: Rerun the real Genesis comparison after calibration and accept only if
  the report artifact shows Genesis room/object views are materially reviewable
  without the obvious dark/cold style gap called out by the human review.

### Parked Cross-Seam / Future Ideas

- A full `household-cleanup` Genesis backend with scene indexing, state
  mutation, robot control, and primitive provenance.
- A broader MJCF backend spike. Genesis has `gs.morphs.MJCF`, but its current
  loader treats MJCF as one large entity rather than a normal multi-entity
  scene; see `vendors/genesis-world/genesis/options/morphs.py`. Treat MJCF as a
  future spike only if it demonstrably beats the accepted prepared-USD visual
  package path.
- Fully generic N-way visual metrics. The current gate remains
  baseline-to-candidate against MuJoCo.

### Evidence Ladder

- L1: Genesis worker unit tests for prepared-USD visual extraction metadata.
- L2: Scene-camera comparison contract tests for visual diagnostics and report
  modal/lightbox markup.
- L4: Real local Genesis comparison run using `.venv-genesis` and the prepared
  flattened semantic USD.
- Visual QA: inspect the report/contact sheet, not just the JSON manifest.

### Stop Condition

Stop only when a real local comparison artifact exists with MuJoCo, Isaac, and
Genesis lanes succeeding, Genesis runtime metadata proving real rendering,
Genesis visual diagnostics not reporting `degraded_visual_fidelity`, clickable
standalone lane images working in the report, the contact sheet demoted to a
secondary overview, compact tone metrics visible next to the reviewed images,
room/wall light diagnostics recorded for dark wall cases, and the Genesis images
visually comparable enough for human review. If native USD/MJCF cannot meet
that, stop with this plan still `CONTINUE` and record the exact blocked visual
import mode.

### Execution Log

- 2026-06-04: Current artifact
  `output/molmo/scene-camera-comparison/genesis-local-proof-patched/0604_1146/`
  renders Genesis through `prepared_usd_visual_mesh`, but the OBJ fallback drops
  USD materials/textures and the manifest correctly reports
  `degraded_visual_fidelity`.
- 2026-06-04: Genesis support check found `gs.morphs.USD` and `gs.morphs.MJCF`.
  Native USD import of the prepared `val_1` stage fails on mixed/multi-parent
  physics graph structure; direct USD entity import fails on mixed entity
  detection. USD remains the primary path because the prepared stage has 632
  Mesh prims, 98 materials, and 153 valid material bindings available for
  visual-only import.
- 2026-06-04: Implemented the accepted fix in
  `scripts/genesis_cleanup/genesis_backend_worker.py`: failed native
  `scene.add_stage(...)` now falls back through a fresh Genesis scene, the
  prepared USD visual package preserves OBJ/MTL material bindings, diffuse
  colors, UVs, and diffuse texture maps, and Genesis applies an explicit
  lane-local luminance calibration instead of weakening the report threshold.
- 2026-06-04: Final accepted artifact:
  `output/molmo/scene-camera-comparison/genesis-materialized-proof/0604_calibrated/0604_1451/`.
  `comparison_successful=True`; MuJoCo, Isaac, and Genesis lanes all succeeded;
  Genesis runtime is real Genesis 1.0.0 from `.venv-genesis`; import mode is
  `prepared_usd_visual_asset_package`; extracted asset metadata records 153
  visible meshes, 98 materials, 53 textured materials, 50 copied textures,
  43,647 triangles, and 25,349 textured triangles. Candidate visual diagnostics
  are `computed`, degraded candidates are empty, and Genesis records mean pixel
  delta `39.76119384763466` and max pixel delta `59.989665798621466`.
- 2026-06-04: Visual QA passed by inspecting
  `output/molmo/scene-camera-comparison/genesis-materialized-proof/0604_calibrated/0604_1451/contact_sheet.png`.
  The Genesis images are not renderer-identical, but they are textured,
  nonblank, and usable for human review. Browser QA of `report.html` found 19
  image buttons; clicking a Genesis image opened the popup dialog with
  `imageSrc=genesis/camera_views/view_02_bed.png` and
  `title=genesis-prepared-usd view_02_bed`.
- 2026-06-04: Reopened the plan for the accepted review-grade follow-up:
  standalone clickable lane images must become the primary visual review
  surface, and the report must carry local tone plus room/wall light diagnostics
  close enough to the images to make MuJoCo/Isaac/Genesis style differences
  actionable.
- 2026-06-04: Completed the review-grade follow-up. New report artifact:
  `output/molmo/scene-camera-comparison/genesis-materialized-proof/0604_report_review/report.html`.
  The report now puts `Standalone Image Review` before `Contact Sheet`, keeps 19
  image buttons clickable, includes per-image `tone lum`, RGB, wall-proxy
  luminance, and baseline delta captions, and records
  `room_wall_light_diagnostics` in `comparison_manifest.json`. The copied real
  Genesis artifact classifies the Genesis room-view darkness as
  `global_tone_or_exposure_delta` rather than wall-specific shadow-only failure.
  Browser QA through Chrome DevTools clicked
  `genesis/camera_views/room_01_room_2.png` and opened the popup dialog with
  `title=genesis-prepared-usd room_01_room_2`; screenshots are
  `report_top.png` and `modal_check.png` in the same artifact directory.
  Verification passed:
  `ruff check scripts/genesis_cleanup/genesis_backend_worker.py roboclaws/household/scene_camera_comparison.py tests/unit/molmo_cleanup/test_genesis_backend.py tests/contract/molmo_cleanup/test_scene_camera_comparison.py`;
  `python -m py_compile scripts/genesis_cleanup/genesis_backend_worker.py roboclaws/household/scene_camera_comparison.py`;
  `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_genesis_backend.py tests/contract/molmo_cleanup/test_scene_camera_comparison.py`
  with 45 tests, 2 skipped.
- 2026-06-04: Reopened again after correcting the success gate. The report
  slice made the gap inspectable, but it did not solve renderer-side
  color/light parity. The active success condition is now: a fresh real Genesis
  comparison artifact where Genesis visual output itself is good enough for
  review.
- 2026-06-04: Completed the renderer-side visual-fidelity fix. Genesis prepared
  USD visual extraction now bakes USD texture `scale`/`bias` color into copied
  texture maps for the OBJ/MTL package, keeping textured material colors from
  washing out in Genesis. The Genesis lane also records explicit RGB, tone, and
  room-view tone calibration in the shared camera color-management diagnostics.
  Final accepted artifact:
  `output/molmo/scene-camera-comparison/genesis-materialized-proof/0604_baked_texture_tone_roomfix/0604_1716/`.
  Evidence: real Genesis 1.0.0 runtime from `.venv-genesis`; import mode
  `prepared_usd_visual_asset_package`; extracted asset metadata records 153
  source meshes, 98 materials, 53 textured materials, 50 textures, 28 baked
  texture materials, 43,647 triangles, and 25,349 textured triangles.
  Candidate visual diagnostics are `computed` with `degraded_candidates=[]`.
  Genesis mean pixel delta is `34.348903446930514`, max per-view mean pixel
  delta is `48.68020073804976`, and room/wall diagnostics report
  `wall_proxy_luminance_reviewable` with both Genesis room-view wall pairs
  classified `wall_proxy_luminance_matched`. Static report QA found
  `Standalone Image Review` before `Contact Sheet`, 19 clickable image buttons,
  and 6 Genesis standalone image buttons. Visual QA inspected `contact_sheet.png`
  and accepted the remaining differences as renderer style rather than the
  earlier dark/cold/washed-out failure.
- 2026-06-04: Reopened after human review called out remaining lack of
  environment light in Isaac and Genesis. Stronger Isaac/Genesis fill probes
  overcorrected or failed the visual metric gate:
  `0604_envfill/0604_1752`, `0604_envfill_tuned/0604_1756`, and
  `0604_envfill_keyonly/0604_1808`. Accepted the softer renderer-side fill
  profile from
  `output/molmo/scene-camera-comparison/genesis-materialized-proof/0604_envfill_soft/0604_1805/`:
  shared `lighting_profile.profile_id=scene_probe_mujoco_headlight_fill_v1`,
  MuJoCo headlight metadata, Isaac dome fill intensity `60.0` with no key light,
  and Genesis ambient `0.37` plus three directional fill lights. This materially
  brightens Genesis and adds explicit environment fill to Isaac while preserving
  `degraded_candidates=[]`. It does not fully eliminate the Isaac `room_01`
  wall residual; the artifact reports `room_wall_light_diagnostics.status=
  global_tone_or_exposure_delta`, and stronger Isaac lighting failed the gate.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Genesis USD import does not preserve enough MolmoSpaces scene semantics | The third lane may render but not support later cleanup indexing | Keep first gate render-only; record scene-load and mapping gaps explicitly. |
| Genesis runtime setup is platform-specific | Local setup may be slower than code changes | Isolate `.venv-genesis/`, add preflight diagnostics, and keep CI fake protocol. |
| Renderer frame convention differs | Camera pose may be mirrored/flipped or visually confusing | Require echoed eye/target/up, intrinsics, and visible pairwise diagnostics before claiming parity. |
| Three-lane report refactor grows too broad | Scope creep delays the first proof | Keep diagnostics pairwise against MuJoCo baseline and defer fully generic N-way analysis. |
| Cleanup reuse pressure broadens the slice | Render proof may be mistaken for backend proof | Keep cleanup as an explicit later section and block cleanup claims in acceptance text. |

## References

- Genesis World submodule: `vendors/genesis-world`
- Scene-camera comparison: `roboclaws/household/scene_camera_comparison.py`
- Camera-control contract: `roboclaws/household/camera_control.py`
- Isaac precedent plan:
  `docs/plans/isaac-lab-molmospaces-backend-support.md`
- MuJoCo/Isaac active visual parity notes:
  `docs/status/active/mujoco-isaac-camera-visual-parity.md`
