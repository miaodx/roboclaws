# Genesis Scene-Camera Backend Lane

**Status:** Draft plan, ready for implementation
**Created:** 2026-06-04
**Source:** Genesis World submodule addition and follow-up discussion about
adding Genesis as a backend variant like the Isaac path.
**Workflow:** `intuitive-flow` discussion plus `grill-with-docs-batch`
alignment. Keep this as the pre-GSD source of truth until it is promoted into a
phase or implemented directly as a scoped comparison slice.

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
- Genesis lane echoes camera pose/intrinsics evidence well enough for pairwise
  geometry and visual diagnostics.
- Report and manifest label the result as render-only scene-camera evidence.

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
