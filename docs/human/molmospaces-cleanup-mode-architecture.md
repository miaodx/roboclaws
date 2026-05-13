# MolmoSpaces Cleanup Profile Architecture

Status: draft for refactor planning

This note defines a reduced naming model for MolmoSpaces cleanup commands. It is
intended to guide a later CLI/docs/test refactor without changing behavior by
itself.

## Problem

The current command surface mixes several separate questions:

- What does the agent actually receive as input?
- Are visual artifacts model input or report evidence?
- Which backend is running?
- Which verifier gates decide pass/fail?

The most confusing case is `visual`. In current Molmo cleanup commands,
`visual` means "produce RBY1M robot-view report artifacts." It does not mean the
agent reasons over images. The default visual cleanup run still uses structured
object detections.

The current raw/image-related names are also too implementation-shaped:

- `visible_object_detections`
- `raw_fpv_only`
- `camera_model_policy`

They make it too easy to forget which runs are structured-label runs, which runs
exercise raw image input, and which runs use simulated camera-derived labels.

## Design Direction

Expose one public concept: `profile`.

Keep `driver` as the second public concept because it is already clear enough:
`direct`, `mcp-smoke`, `codex`, `claude`, `openclaw`.

Do not expose `agent_input`, `report`, `world_backend`, `perception_provenance`,
or `verifier` as first-class public knobs by default. Those remain profile
metadata and report metadata.

Preferred command shape:

```bash
just task::run molmo-cleanup <driver> <profile>
```

Examples:

```bash
just task::run molmo-cleanup claude world-labels
just task::run molmo-cleanup claude camera-raw
just task::run molmo-cleanup direct camera-labels
```

No backward compatibility is required for this refactor. The new names can
replace the old public names instead of preserving aliases.

## Profile Naming Principles

Profile names should answer one question: what kind of evidence does the agent
use?

Use short names that expose the agent input source:

- `world-*` means labels come from a world model, semantic map, simulator state,
  or object memory.
- `camera-*` means the camera observation is the source.
- `*-labels` means the agent receives structured object candidates or handles.
- `*-raw` means the agent receives raw camera artifacts and must infer from
  pixels or image-derived text.

Avoid names that describe only report output:

- Avoid `visual`.
- Avoid `robot-view` as a profile name.
- Use robot-view wording only inside report metadata.

Avoid simulator-specific names in the public profile:

- Avoid `sim-*`.
- Avoid `oracle`.

Simulator-vs-real provenance belongs in metadata, not in the profile name.

## Recommended Profiles

| Profile | Agent input | Default backend | Default report | What it proves |
| --- | --- | --- | --- | --- |
| `smoke` | world labels | synthetic contract | semantic report | Cheap command and contract sanity. |
| `world-labels` | world labels | MolmoSpaces sim | robot-view report | Current structured cleanup path with visual artifacts. No image reasoning. |
| `camera-raw` | raw camera artifacts | MolmoSpaces sim | robot-view report | Image-input contract: structured labels are withheld. |
| `camera-labels` | camera-derived labels | MolmoSpaces sim | robot-view report | Camera-perception-label contract. Today simulated; later real detector/VLM. |

This gives humans four memorable buckets:

```text
smoke
world-labels
camera-raw
camera-labels
```

The names are intentionally not perfectly symmetrical with the current
implementation. They describe the durable contract.

## Profile Details

### `smoke`

Cheap deterministic confidence gate.

Expanded meaning:

```text
agent_input=world_labels
input_provenance=synthetic_contract
world_backend=synthetic_contract
report=semantic_report
verifier=contract_only
```

Use this for fast agent iteration and CI-style checks. It is not a visual
cleanup claim and does not exercise image input.

### `world-labels`

Structured-label cleanup with robot-view report artifacts.

Expanded meaning:

```text
agent_input=world_labels
input_provenance=simulator_state
world_backend=molmospaces_sim
report=robot_view_report
verifier=cleanup_success + robot_view_honesty + real_robot_alignment
```

This is the current "MolmoSpaces cleanup with visual result" behavior. The
agent receives handles such as `observed_001`, object categories, support
estimates, and public candidate fixture hints. The FPV/chase/map/verification
images are report artifacts, not model input.

Future real hardware can still use this profile if the labels come from a robot
semantic map or object memory. The public profile should not change just because
the provenance changes.

### `camera-raw`

Raw camera-input cleanup.

Expanded meaning:

```text
agent_input=raw_camera
input_provenance=camera_artifact
world_backend=molmospaces_sim
report=robot_view_report
verifier=image_input_contract + robot_view_honesty
```

This is the profile to use when the test is meant to prove that the model path
does not depend on prebuilt object labels. The contract should provide camera
artifacts and withhold object handles, categories, support estimates, and
candidate fixtures.

This profile is the one that can exercise real image reasoning when paired with
a model that supports image input and a launcher that passes images correctly.

### `camera-labels`

Camera-derived structured labels.

Expanded meaning:

```text
agent_input=camera_labels
input_provenance=simulated_camera_model
world_backend=molmospaces_sim
report=robot_view_report
verifier=image_input_contract + cleanup_success + robot_view_honesty
```

The agent receives structured object candidates, but those candidates are
registered from a camera-observation step rather than directly from the world
model.

Current implementation note: the existing `camera_model_policy` path uses
deterministic simulated camera-model evidence. It does not call a real VLM or
detector. A future implementation can keep the same profile and change
`input_provenance` to `vlm_detector` or `object_detector`.

## Metadata Kept Behind Profiles

Profiles expand into implementation metadata. This metadata should appear in
reports and checker output, but most users should not type it.

### Agent Input

| Metadata value | Meaning |
| --- | --- |
| `world_labels` | Structured object handles and labels from a world model. |
| `raw_camera` | Raw camera/FPV artifacts with no structured labels. |
| `camera_labels` | Structured object candidates derived from camera perception. |

### Input Provenance

| Metadata value | Meaning |
| --- | --- |
| `synthetic_contract` | Cheap contract-shaped test data. |
| `simulator_state` | Labels derived from simulator object locations/state. |
| `robot_semantic_map` | Labels from a real robot semantic map or object memory. |
| `camera_artifact` | Raw camera artifact supplied without labels. |
| `simulated_camera_model` | Camera-label candidates generated from public simulator state. |
| `vlm_detector` | Camera-label candidates generated by a real multimodal model. |
| `object_detector` | Camera-label candidates generated by a conventional detector. |
| `human_annotation` | Labels supplied by a human or offline annotation process. |

### Report

| Metadata value | Meaning |
| --- | --- |
| `semantic_report` | Shared cleanup report without robot-view timeline. |
| `robot_view_report` | Adds RBY1M FPV/chase/map/verification timeline. |

### Verifier

| Metadata value | Meaning |
| --- | --- |
| `contract_only` | Contract shape exists and artifacts are present. |
| `cleanup_success` | Restoration, coverage, disturbance, and cleanup status gates. |
| `robot_view_honesty` | Robot-view timeline and waypoint/post-place roles are honest. |
| `image_input_contract` | Raw camera or camera-label path is actually used as expected. |
| `real_robot_alignment` | Reports keep semantic simulation separate from real robot readiness. |

## Legacy Name Replacement

No compatibility layer is required. Replace old public names directly.

| Old public/internal name | New public profile or metadata |
| --- | --- |
| `visual` | `profile=world-labels` when used as the default visual cleanup result. |
| `semantic` | `profile=smoke` for cheap contract checks, or `report=semantic_report` in metadata. |
| `raw-fpv` | `profile=camera-raw`. |
| `visible_object_detections` | `agent_input=world_labels` metadata. |
| `raw_fpv_only` | `agent_input=raw_camera` metadata. |
| `camera_model_policy` | `profile=camera-labels`, with `input_provenance=simulated_camera_model` today. |
| `synthetic` | `world_backend=synthetic_contract` metadata. |
| `molmospaces` | `world_backend=molmospaces_sim` metadata. |

## Missing Default Tests

The refactor should make these gaps visible and testable:

| Test target | Purpose |
| --- | --- |
| `profile=smoke` | Cheap contract sanity still works. |
| `profile=world-labels` | Current structured cleanup path still produces robot-view artifacts and does not imply image input. |
| `profile=camera-raw` | Raw camera artifacts are actually used and structured labels are withheld. |
| `profile=camera-labels` | Camera-derived label path is separate from world-label path and records provenance. |

The most important regression test is:

```text
profile=world-labels must not be described as image reasoning.
```

The second most important regression test is:

```text
profile=camera-raw must fail if structured object labels leak into agent input.
```

## Implementation Plan

1. Change public `just task::run molmo-cleanup <driver> <report>` routing to
   treat the third positional argument as `<profile>`.
2. Implement the four profiles: `smoke`, `world-labels`, `camera-raw`,
   `camera-labels`.
3. Remove old public values instead of preserving aliases.
4. Keep internal constants if that reduces churn, but translate them into the
   new profile metadata at command/report boundaries.
5. Update command help, `docs/human/molmospaces-settings.md`, and
   `just/README.md`.
6. Add contract tests for profile expansion and report metadata.
7. Add focused default tests for `camera-raw` and `camera-labels`.

## Open Decisions

- Whether `direct` should be renamed to `scripted-baseline` now or left alone.
- Whether `camera-labels` should be exposed for live Codex/Claude/OpenClaw
  immediately; the current live server supports the structured-label and
  raw-camera shapes, while camera-label support is strongest in the direct
  contract path.
- Whether `profile=world-labels` should default to one seed or keep the current
  direct-driver multi-seed review behavior.
