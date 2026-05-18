# 0126. Bridge Camera Evidence To Cleanup Handles With Model-Declared Observations

Date: 2026-05-18

## Status

Accepted

## Context

ADR-0003 separates the Cleanup Agent's public view from private scoring truth.
ADR-0013 added `raw_fpv_only` so an agent can receive camera evidence without
structured movable-object detections. ADR-0020 added `camera_model_policy` so a
deterministic simulated camera model can register camera-derived cleanup
candidates.

Those decisions leave a gap for live image-capable agents. A model can inspect a
raw FPV image, but the public contract does not yet let it turn that visual
inference into an `observed_*` handle that the semantic cleanup tools can act
on. Keeping that conversion only inside a producer-specific MCP tool would also
make the future separate camera inference model and the main cleanup agent use
different concepts for the same boundary.

## Decision

Introduce **Model-Declared Observations** as the durable public bridge from
camera evidence to cleanup handles.

A Model-Declared Observation is an observed handle created from a camera
inference producer's interpretation of public camera evidence. The producer may
be the main cleanup agent, a separate camera inference model, a detector, a
robot perception service, or a deterministic harness producer.

The cleanup contract should:

- keep `camera-raw` and `camera-labels` as public profiles;
- let `camera-raw` agents declare visual candidates from raw FPV image
  reasoning;
- let `camera-labels` producers register structured candidates through the same
  declaration schema;
- prefer `inline_on_navigate` for live raw-FPV agents, while keeping separate
  registration as a harness-selectable variant;
- use public declaration fields such as source observation id, category, target
  fixture id, evidence note, image region, producer metadata, and confidence;
- treat declarations as append-only evidence;
- allow hidden grounding to bind declarations to executable objects only when it
  does not use or expose private scoring truth;
- expose grounding results only as public-quality metadata: resolved,
  ambiguous, or unresolved, with confidence, basis, and recovery hint;
- block `pick` for unresolved or ambiguous declarations.

Add **Active Camera Observation** as a bounded public aid: the agent may adjust
FPV yaw and pitch within small limits before observing, and each adjusted
observation becomes its own raw FPV evidence row.

## Consequences

- `raw_fpv_only` is no longer only an evidence dead end once this refactor is
  implemented; a capable image model can create public cleanup handles from
  public image evidence.
- `camera_model_policy` becomes an implementation/provenance detail of the
  camera-labels profile rather than a separate public concept.
- The MCP surface gains a narrow perception bridge, but it still does not hide
  the cleanup task behind one opaque tool.
- Reports and checkers can distinguish raw camera evidence, model-declared
  handles, grounding quality, and actual cleanup actions.
- Private generated mess sets, acceptable destinations, scorer object results,
  and internal object ids remain outside Agent View, traces, and model-facing
  grounding feedback.

