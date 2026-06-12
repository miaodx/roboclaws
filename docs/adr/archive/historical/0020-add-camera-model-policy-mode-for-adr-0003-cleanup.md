# 0020. Add Camera Model Policy Mode For ADR-0003 Cleanup

Date: 2026-05-09

## Status

Accepted

## Context

ADR-0003 separates the Cleanup Agent's public view from private scoring truth.
ADR-0013 added `raw_fpv_only` as an evidence mode: the agent receives camera
observations and artifacts without structured movable-object detections,
categories, support estimates, target labels, or generated-mess truth.

That raw mode intentionally does not clean successfully. The broader context
still needs a camera-only model-policy path where cleanup candidates are derived
from the public camera-observation stream, then run through the same semantic
cleanup loop and shared report underlay as the visible-detection path.

The project must avoid a new false shortcut here. A deterministic CI policy may
stand in for a future VLM, but it must be labelled as simulated camera-model
evidence and must not be confused with private scorer truth or real pixel-model
inference.

## Decision

Add an explicit ADR-0003 perception mode, `camera_model_policy`.

The mode should:

- keep `observe` camera-first by recording a raw FPV observation and returning
  no built-in `visible_object_detections`;
- expose a separate camera-model policy primitive that derives observed object
  handles from the current public camera observation;
- label every derived candidate with model provenance, perception source, and
  its source raw FPV observation;
- register derived candidates as ordinary observed handles so the existing
  semantic cleanup tools can be reused;
- keep generated mess, target count, acceptable destinations, `is_misplaced`,
  and target receptacles out of Agent View and traces;
- render a `Camera Model Policy` section in the shared cleanup report;
- add checker support that can require camera-model policy evidence and reject
  unlabeled/private-truth detections.

## Consequences

- The ADR-0003 cleanup path gains a camera-only model-policy proof without
  cloning report code or bypassing the semantic loop.
- CI can prove the contract with a deterministic simulated camera model, while
  reports clearly distinguish that from real VLM inference.
- `raw_fpv_only` remains a stricter no-structured-detections evidence mode and
  does not imply cleanup success.
- Cleanup primitive provenance remains `api_semantic` until the separate
  RBY1M/CuRobo planner-backed primitive gate passes.
