# Isaac Lab MolmoSpaces Backend Support

**Status:** Proposed
**Created:** 2026-05-27
**Source:** MolmoSpaces renderer/backend research and Isaac Lab support
discussion.
**Workflow:** Pre-GSD plan; use this file as the shaping source before any
implementation phase is opened.

## Problem

Roboclaws currently proves household cleanup through a MolmoSpaces/MuJoCo
backend. That path is good for stable scene state, current upstream benchmark
compatibility, and visible cleanup reports, but the visual result is limited by
MuJoCo's renderer choices. MuJoCo Filament can improve some images, but local
comparison did not show a clear enough win to make it the default.

MolmoSpaces also publishes assets for Isaac Sim / Isaac Lab through USD, and
Isaac can provide a more realistic renderer and richer sensor outputs. However,
this is not a renderer-only swap. The current Roboclaws backend directly uses
MuJoCo `MjModel`, `MjData`, `qpos`, MuJoCo fixed cameras, body names, joints,
and free-joint state mutation. Isaac Lab would need its own runtime adapter
over USD prims, articulations, sensors, and renderer outputs while preserving
the same public cleanup/MCP contract.

## Goal

Add an Isaac Lab backend variant that can run the current household-cleanup
style flow with MolmoSpaces scenes:

- load a MolmoSpaces USD scene into Isaac Sim / Isaac Lab;
- expose the same public Roboclaws cleanup tools and report shape used by the
  current MolmoSpaces backend;
- capture FPV, chase, verification, and optional segmentation evidence from
  Isaac cameras;
- execute a bounded semantic cleanup loop over one small scene;
- keep all Isaac-specific dependencies and runtime state outside the core
  Roboclaws `.venv/`;
- label early results honestly as `isaac_semantic_pose` or equivalent, not as
  planner-backed manipulation.

The target first proof is backend parity for a cleanup report, not a full
Isaac Lab RL benchmark and not real manipulation control.

## Non-Goals

- Do not replace the current MuJoCo backend as the default truth path.
- Do not treat Isaac Sim as a drop-in renderer behind the MuJoCo state model.
- Do not add Isaac Lab dependencies to the core Roboclaws `.venv/`.
- Do not claim RBY1M or humanoid planner-backed manipulation from pose edits.
- Do not raise RAW_FPV or cleanup default render resolution globally.
- Do not build a full Isaac Lab training task, reward stack, or leaderboard
  integration in the first phase.
- Do not block existing MolmoSpaces cleanup, visual-grounding, or Agibot work
  on Isaac support.

## Architecture

Keep the current Roboclaws ladder intact:

```text
Runnable task
  -> cleanup skill / MCP tools
  -> realworld cleanup contract
  -> backend variant
  -> artifacts and report
```

The new work belongs at the backend layer:

```text
household-cleanup
  -> realworld_cleanup_v1
  -> IsaacLabSubprocessBackend
  -> scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py
  -> report.html / run_result.json / trace.jsonl
```

The public tool surface should remain compatible with the current backend:

- `observe`
- `navigate_to_object`
- `pick`
- `navigate_to_receptacle`
- `open_receptacle`
- `place`
- `place_inside`
- `close_receptacle`
- `done`
- report helpers such as `write_snapshot` and `write_robot_views`

The first backend should be subprocess-based, mirroring
`MolmoSpacesSubprocessBackend`. Isaac Lab has a heavy runtime lifecycle, so the
main Roboclaws process should communicate through JSON commands and artifacts
rather than importing Isaac directly.

## Runtime Boundary

Create an isolated Isaac runtime, for example:

```text
.venv-isaaclab/
```

or a dedicated Docker image if local Isaac pip setup is too brittle. This is a
deliberate exception to the repo's normal one-`.venv/` rule because Isaac Sim,
CUDA Torch, RTX rendering, and Omniverse dependencies should not contaminate the
core cleanup runtime.

The worker should record diagnostics in every run:

- Isaac Sim version;
- Isaac Lab version;
- Python version;
- CUDA availability;
- GPU name and VRAM when available;
- renderer mode;
- camera resolution;
- selected scene USD path;
- object/receptacle index count;
- segmentation availability.

## Scene And State Mapping

The hardest part is not launching Isaac; it is preserving Roboclaws' cleanup
semantics over a different simulator state model.

Build an `IsaacSceneIndex` that maps:

- MolmoSpaces object ids to USD prim paths;
- receptacle ids to fixture prims and support poses;
- openable receptacles to Isaac articulation/joint handles;
- object categories to public visible-detection labels;
- semantic/instance ids to report-visible object handles;
- room and fixture metadata to the existing Runtime Metric Map / fixture hints
  shape.

The MuJoCo backend stores mutable truth in `qpos`, object body positions, and
joint positions. The Isaac backend must store equivalent public/private state in
terms of USD prim transforms, articulation states, and backend-side JSON state.

## Control Strategy

Start with semantic control, then graduate to real controllers only after the
report path is stable.

### Phase 1 Control: Semantic Pose Backend

Use explicit simulator state edits:

- `navigate_to_object`: set robot root/base pose near the object's current
  fixture.
- `pick`: attach the object to a held-object state and move its prim near the
  robot/gripper frame.
- `navigate_to_receptacle`: set robot root/base pose near the target fixture
  and carry the held object.
- `open_receptacle`: set a target articulation joint/open value where available.
- `place` / `place_inside`: set object prim transform to a fixture support or
  inside pose.
- `close_receptacle`: set the articulation joint back to the closed value.

Every response must report provenance such as:

```text
primitive_provenance=isaac_semantic_pose
physical_robot=false
planner_backed=false
```

### Later Control: Planner-Backed Isaac

Only after semantic backend parity is stable, add real controllers:

- base navigation controller or waypoint follower;
- arm IK or motion planner;
- grasp candidate selection;
- collision-aware place;
- articulation interaction policy.

This later layer can use Isaac Lab controllers or external planners, but it
should attach proof artifacts to cleanup substeps the same way current
planner-backed MolmoSpaces proof bundles do.

## Camera And Perception

First version should support:

- FPV camera;
- chase camera;
- verification/focus camera;
- optional map/snapshot view;
- RGB output at the same default cleanup resolution as MuJoCo today;
- optional semantic or instance segmentation when available.

Do not change the global cleanup default resolution. Use a renderer comparison
or Isaac-specific probe to test `1280x720` / 1280p images before changing
RAW_FPV or visual-grounding defaults.

Isaac camera outputs should feed the same report and visual-grounding paths:

- `raw_fpv_observation`;
- `camera-labels` producer inputs;
- bbox overlays;
- robot view timeline;
- renderer/runtime diagnostics.

## Implementation Phases

### Phase A: Isaac Runtime Smoke

Deliver a standalone local script that:

- starts Isaac Sim / Isaac Lab headlessly or with a minimal viewer;
- loads one tiny USD scene or a MolmoSpaces USD scene if already available;
- captures one RGB image;
- writes runtime diagnostics and a small HTML or JSON artifact.

Acceptance:

- one command produces a nonblank image;
- diagnostics show Isaac and GPU/runtime information;
- no Isaac package is imported by normal Roboclaws startup.

### Phase B: MolmoSpaces USD Scene Parity

Load one MolmoSpaces scene through the Isaac asset path.

Acceptance:

- scene loads without manual editor steps;
- object and receptacle counts are recorded;
- at least one FPV, one chase, and one verification image are saved;
- report diagnostics list unresolved mapping gaps.

### Phase C: Public Object/Receptacle Index

Build the `IsaacSceneIndex`.

Acceptance:

- public scenario can be generated from Isaac scene state;
- selected cleanup objects and target receptacles are deterministic;
- private manifest remains separate from agent view;
- object/receptacle ids map to stable USD prim paths or recorded blockers.

### Phase D: Semantic Cleanup Backend

Implement `IsaacLabSubprocessBackend` behind the existing cleanup contract.

Acceptance:

- a one-object cleanup run completes `nav -> pick -> nav -> place`;
- `run_result.json`, `trace.jsonl`, and `report.html` are generated;
- report includes robot view timeline images from Isaac;
- primitive provenance is visibly `isaac_semantic_pose`;
- existing MuJoCo backend behavior is unchanged.

### Phase E: Camera/Segmentation Parity

Add segmentation or instance-id evidence if the selected Isaac renderer path
supports it reliably.

Acceptance:

- FPV RGB remains available;
- segmentation availability is recorded as explicit success or blocker;
- bbox/candidate overlays can be generated from Isaac camera evidence;
- no fallback silently substitutes MuJoCo or simulator labels.

### Phase F: Planner-Backed Follow-Up

Only after Phases A-E are stable, scope planner-backed manipulation.

Acceptance:

- each planner-backed substep has proof evidence;
- semantic pose fallback remains clearly labeled;
- failed planner attempts produce visible blockers, not fabricated success.

## Recommended First Command Surface

Do not add a new public task name. Add a backend selector to the existing
household cleanup run shape, for local-dev only at first:

```bash
just task::run household-cleanup direct world-labels \
  backend=isaaclab_subprocess \
  seed=7 \
  generated_mess_count=1
```

Renderer comparison can use an explicit maintainer or harness command instead:

```bash
just agent::harness molmo-isaac-renderer-comparison \
  scene=procthor-val-0 \
  resolution=1280x720
```

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Isaac install/runtime is heavy or host-specific | Local setup takes longer than backend code | Keep isolated runtime and write diagnostics first |
| MolmoSpaces USD metadata does not preserve every cleanup handle | Object/receptacle mapping gaps | Build `IsaacSceneIndex` with explicit unresolved rows |
| RTX rendering memory pressure | 1280p or segmentation may fail | Keep 540x360 default and make 1280p comparison-only |
| Articulation or collision behavior differs from MuJoCo | Open/place semantics drift | Label phase-D as semantic pose and defer planner proof |
| Report becomes backend-specific | Cleanup evidence gets harder to compare | Reuse existing report schema and add backend diagnostics only |

## Research Sources

- MolmoSpaces README: assets are usable in MuJoCo, Isaac, and ManiSkill, while
  data generation and benchmarking are only supported for MuJoCo:
  <https://github.com/allenai/molmospaces>
- MolmoSpaces Isaac package: USD asset/scene conversion and loading path:
  <https://github.com/allenai/molmospaces/tree/main/molmo_spaces_isaac>
- Isaac Lab installation:
  <https://isaac-sim.github.io/IsaacLab/develop/source/setup/installation/pip_installation.html>
- Isaac Sim system requirements:
  <https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html>
- Isaac Lab cameras and renderer outputs:
  <https://isaac-sim.github.io/IsaacLab/v3.0.0-beta/source/overview/core-concepts/sensors/camera.html>
- Isaac Lab AppLauncher:
  <https://isaac-sim.github.io/IsaacLab/main/source/tutorials/00_sim/launch_app.html>

## Open Questions

- Which MolmoSpaces USD scene should be the first pinned test scene?
- Is local Isaac installation acceptable, or should the first runtime be Docker?
- Do we target RBY1M shape immediately, or start with a simpler Isaac robot for
  camera/report parity?
- Which segmentation output should be canonical for Roboclaws reports:
  semantic label, instance id, or both?
- Should the first Isaac backend reuse the existing MolmoSpaces map bundle or
  generate a fresh map projection from USD geometry?

