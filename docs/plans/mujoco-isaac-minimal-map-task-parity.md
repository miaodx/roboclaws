# MuJoCo Isaac Minimal Map Task Parity

**Status:** Planned
**Created:** 2026-06-03
**Source:** Discussion after MuJoCo/Isaac FPV head-camera alignment, chase-camera
repair, box visual-state fix, RAW_FPV check request, and the decision that
minimal map, semantic-map-build, and household-cleanup should be compared in
both backends.
**Workflow:** Pre-GSD plan. Use this file as the task-level execution source.
Use
[`mujoco-isaac-visual-parity-convergence.md`](mujoco-isaac-visual-parity-convergence.md)
and
[`mujoco-isaac-object-render-parity-audit.md`](mujoco-isaac-object-render-parity-audit.md)
as the lower-level camera/object/render gates.

## Problem

The visual parity work has mostly stabilized the camera layer, but the current
evidence is still too report-local. It tells us whether selected MuJoCo and
Isaac robot-camera captures look comparable, but it does not yet prove the
actual household task chain is apple-to-apple:

```text
minimal navigation map
  -> semantic-map-build
  -> runtime_metric_map.json
  -> household-cleanup runtime_map_prior=...
```

For future real-robot confidence, MuJoCo and Isaac need to exercise the same
public task/profile/input contracts. If Isaac cleanup is run with a prepared USD
scene while MuJoCo cleanup uses a different map, camera, generated mess set, or
input lane, any behavior difference is hard to interpret. It could be the
agent, the task state, the object renderer, the semantic-map evidence, or the
backend.

## Goal

Produce one comparable MuJoCo-vs-Isaac evidence bundle for the minimal-map
household flow:

- `semantic-map-build` from a minimal map in MuJoCo and Isaac;
- `household-cleanup` consuming the corresponding runtime map prior in MuJoCo
  and Isaac;
- both `world-labels` and RAW_FPV / `camera-raw` input lanes where backend
  support exists;
- explicit camera, object, render, map, and task-result gates before comparing
  scores or agent behavior.

The desired claim is conservative: for the audited scene/seed/lane set, MuJoCo
and Isaac run the same public task contract and any remaining differences are
classified by gate.

## Non-Goals

- Do not introduce a new public task name.
- Do not make chase camera an agent input view.
- Do not use report-side RGB gain or luminance compensation as a substitute for
  native Isaac renderer diagnostics.
- Do not hide object binding/renderability failures inside cleanup score
  differences.
- Do not claim full cross-scene parity from one scene.
- Do not require Agibot hardware for this simulator parity slice.

## Zoomed-Out Contract

The relevant architecture layers are:

- **Runnable Tasks:** `semantic-map-build` and `household-cleanup`.
- **Agent-facing map contract:** minimal `metric_map()` / Runtime Metric Map
  evidence, not rich authored room semantics by default.
- **Input lanes:** `world-labels`, `world-labels-sanitized`, `camera-labels`,
  and `camera-raw`; this plan focuses on `world-labels` and `camera-raw`
  first.
- **Backend variants:** MuJoCo through `molmospaces_subprocess`; Isaac through
  `isaaclab_subprocess` with an explicit prepared USD scene.
- **Visual gates:** FPV/head-camera, chase report view, selected object parity,
  native Isaac renderer diagnostics, and report-side comparison diagnostics.

The key reduce-entropy rule is: keep visual comparability and task comparability
separate. Visual gates explain whether the images are comparable; task gates
explain whether the public map/input/action contract is comparable.

## Current Decisions

### Camera

- FPV means the real robot-mounted head camera in both backends.
- Chase camera remains auxiliary report evidence from behind and above the
  robot.
- Every task-level run should record which images were model input and which
  were report-only evidence.

### Map

- The mainline starts from `map_mode=minimal`.
- `semantic-map-build` produces a Runtime Metric Map snapshot.
- `household-cleanup` consumes that snapshot through `runtime_map_prior=...`.
- Rich/preauthored map semantics may be used only as an explicit debug or
  calibration lane, not as the acceptance path.

### Inputs

- `world-labels` is the structured semantic upper-bound lane.
- `camera-raw` / RAW_FPV is the closest simulator lane to robot-local visual
  input.
- A MuJoCo-vs-Isaac task comparison is valid only when both backends use the
  same lane semantics and equivalent model-facing evidence.

### Objects And Rendering

- Object parity is a precondition for interpreting visual residuals.
- The box open/closed fix is category-level evidence backed by prepared-USD
  visual-physics freeze, not proof that every category is safe.
- Native Isaac exposure/tone diagnostics must be present before brightness is
  treated as solved.

## Plan

### Phase 1: Baseline Matrix Definition

Define the smallest matrix that is still useful:

- scene source: `procthor-10k-val`;
- initial scenes: current `val_0` and `val_1` slices;
- seed set: include the reviewed seed-6 path and the user-reviewed `0008` /
  seed-8 slice when reproducible;
- generated mess count: match across backends;
- location/camera settings: match render dimensions, FPV camera, and chase
  camera contract;
- prepared Isaac USD: use the combined material/light default path only when
  its prepared-scene summary passes reference, label, and visual-state gates.

Output:

- one manifest listing the intended scene/seed/lane/backend matrix;
- artifact paths for existing visual parity reports that justify the baseline.

Acceptance:

- The matrix names exactly which runs are comparable and which are blocked.
- No cleanup score is interpreted before the visual gates for that run pass.

### Phase 2: Visual Gate Preflight

For every planned task-level run, require the lower-level visual evidence:

- FPV selected camera provenance and pose/lens alignment;
- chase camera provenance and robot-relative pose contract;
- selected object binding and renderability audit;
- category-level visual-state evidence, currently at least `box`;
- native Isaac renderer diagnostics: tone mapping, exposure, ISO/f-stop, white
  point, auto-exposure, OCIO/display/view/look, color correction/grading,
  render mode, camera prim path, and render product path;
- report-side RGB/tone profiles labeled as comparison-only.

Output:

- linked `comparison_manifest.json` and `report.html` for each visual preflight;
- summary status that distinguishes `report_side_visual_parity_ready` from
  default native rendering readiness.

Acceptance:

- Each task-level run is tagged `visual_ready`, `visual_warning`, or
  `visual_blocked`.
- `visual_blocked` runs are not used for score or behavior comparison.

### Phase 3: Semantic-Map-Build Apple-To-Apple

Run `semantic-map-build` in both backends from minimal map context.

Example command shape:

```bash
just task::run semantic-map-build direct world-labels \
  seed=6 generated_mess_count=5 map_mode=minimal \
  backend=molmospaces_subprocess

just task::run semantic-map-build direct world-labels \
  seed=6 generated_mess_count=5 map_mode=minimal \
  backend=isaaclab_subprocess \
  isaac_scene_usd_path=<prepared_scene_semantic.usda>
```

For RAW_FPV, use the equivalent supported lane only after confirming the Isaac
backend exposes the same model-facing image evidence:

```bash
just task::run semantic-map-build direct camera-raw \
  seed=6 generated_mess_count=5 map_mode=minimal \
  backend=<backend>
```

Output per backend/lane:

- `runtime_metric_map.json`;
- `actionable_semantic_map_snapshot.json` when produced;
- `run_result.json`;
- `report.html`;
- robot-view image provenance.

Acceptance:

- Both backends expose minimal source-map context rather than rich authored
  fixture semantics.
- Runtime semantic anchors, observed objects, map update candidates, and sweep
  coverage are comparable by schema and provenance.
- Any missing Isaac lane support is recorded as a backend gap, not silently
  compared against a different MuJoCo input.

### Phase 4: Cleanup With Runtime Map Prior

Run `household-cleanup` in both backends using the matching runtime map prior
from Phase 3.

Example command shape:

```bash
just task::run household-cleanup direct world-labels \
  seed=6 generated_mess_count=5 map_mode=minimal \
  runtime_map_prior=<mujoco_runtime_metric_map.json> \
  backend=molmospaces_subprocess

just task::run household-cleanup direct world-labels \
  seed=6 generated_mess_count=5 map_mode=minimal \
  runtime_map_prior=<isaac_runtime_metric_map.json> \
  backend=isaaclab_subprocess \
  isaac_scene_usd_path=<prepared_scene_semantic.usda>
```

Repeat for `camera-raw` only after Phase 3 proves lane parity.

Output per backend/lane:

- cleanup `run_result.json`;
- `trace.jsonl`;
- `report.html`;
- robot-view and selected-object evidence;
- final cleanup score and evaluator details kept separate from agent-facing
  evidence.

Acceptance:

- Cleanup action opportunities are compared only when the map prior, generated
  mess set, selected objects, and visual gates match.
- Differences are classified as map evidence, perception lane, object/render
  parity, backend capability, or policy behavior.
- The report makes clear whether the agent saw `world-labels` or RAW_FPV.

### Phase 5: Summary Report

Generate one summary report for human review.

The summary should group by:

- scene/seed/mess-count;
- task: `semantic-map-build` or `household-cleanup`;
- lane: `world-labels` or `camera-raw`;
- backend: MuJoCo or Isaac;
- visual gate status;
- map/task gate status;
- cleanup score and behavior notes only after gates pass.

Acceptance:

- The HTML embeds image pairs, not just links.
- The JSON summary can answer whether a difference came from camera, object,
  render, map, input lane, backend, or agent behavior.
- The summary does not mark default Isaac rendering ready if native diagnostics
  are missing.

## Engineering Review Gates

Fast CI-safe gates for code changes in this area:

```bash
ruff check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py \
  scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py \
  roboclaws/household/scene_camera_comparison.py \
  scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py \
  tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py \
  tests/unit/molmo_cleanup/test_robot_camera_visual_parity_summary.py \
  tests/unit/molmo_cleanup/test_isaac_lab_backend.py \
  tests/contract/molmo_cleanup/test_scene_camera_comparison.py

ruff format --check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py \
  scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py \
  roboclaws/household/scene_camera_comparison.py \
  scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py \
  tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py \
  tests/unit/molmo_cleanup/test_robot_camera_visual_parity_summary.py \
  tests/unit/molmo_cleanup/test_isaac_lab_backend.py \
  tests/contract/molmo_cleanup/test_scene_camera_comparison.py

./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py \
  tests/unit/molmo_cleanup/test_robot_camera_visual_parity_summary.py \
  tests/unit/molmo_cleanup/test_isaac_lab_backend.py \
  tests/contract/molmo_cleanup/test_scene_camera_comparison.py
```

Task-level gates:

```bash
ROBOCLAWS_JUST_TRACE=1 just task::run semantic-map-build direct world-labels \
  seed=6 generated_mess_count=5 map_mode=minimal

ROBOCLAWS_JUST_TRACE=1 just task::run household-cleanup direct world-labels \
  seed=6 generated_mess_count=5 map_mode=minimal

ROBOCLAWS_JUST_TRACE=1 just task::run household-cleanup direct camera-raw \
  seed=6 generated_mess_count=5 map_mode=minimal
```

Local GPU gates:

- verify `.venv/` has MolmoSpaces and MuJoCo;
- verify `.venv-isaaclab/` has Isaac Sim/Lab and can load the prepared USD;
- regenerate or refresh native Isaac diagnostics;
- inspect generated `report.html` image pairs before promoting defaults.

## Open Questions

- Should the first task-level parity matrix use only one seed for fast
  iteration, or require seed-6 plus seed-8 before any summary is considered
  useful?
- Does `semantic-map-build direct camera-raw` have full backend support in
  Isaac today, or should the first RAW_FPV gate be cleanup-only?
- Should chase be a warning-only visual gate for task-level parity, or a hard
  gate when the report claims visual apple-to-apple?
- How many held-out scenes are needed before changing Isaac native exposure or
  material/light defaults? Initial minimum: current two scenes plus one
  held-out scene.

## Stop Condition

This plan is ready to move into a GSD phase when:

- the visual parity summary has native Isaac diagnostics for the selected
  matrix;
- the task matrix is fixed and reproducible;
- MuJoCo and Isaac runs can be generated from the repo root without worktree
  dependency confusion;
- at least one `world-labels` semantic-map-build plus cleanup pair exists for
  both backends;
- RAW_FPV support status is explicit.
