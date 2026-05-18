# MolmoSpaces Model-Declared Observations For Raw FPV Cleanup

**Status:** Planned
**Created:** 2026-05-18
**Source:** `CONTEXT.md`, ADR-0003, ADR-0013, ADR-0020, failed Codex camera-raw run `output/molmo/codex-camera-raw/0518_0956/seed-7`
**Workflow:** docs-first refactor plan; implementation should use the harness/refactor loop

## Problem

The `camera-raw` profile currently proves that raw FPV observations can be
withheld from structured object labels, but it does not yet give a capable
image model a public way to convert its visual inference into cleanup handles.

The failure mode is concrete:

```text
Sweep: 14/14 raw FPV observations
Structured observed objects exposed: 0
Cleanup result: failed, 0/10 restored
```

That result is honest for the old `raw_fpv_only` contract, but it is not the
desired live-agent behavior. A strong image-capable coding agent such as
official Codex with `gpt-5.5` should be able to inspect the FPV image evidence,
declare plausible cleanup candidates, and then use the same public
`navigate -> pick -> navigate -> open? -> place` cleanup loop as world-label and
camera-label runs.

The current implementation also risks splitting the concept across two names:
`raw_fpv_only` has no handle-registration path, while `camera_model_policy`
registers deterministic simulated candidates through `infer_camera_model_candidates`.
The next refactor should unify both under one producer-agnostic mechanism.

## Decision

Implement a **Model-Declared Observation** path for the Molmo cleanup contract.

A Model-Declared Observation is a public `observed_*` handle created from a
camera inference producer's interpretation of public camera evidence. The
producer may be:

- the main cleanup agent reasoning over raw FPV image blocks;
- a separate camera inference model;
- a detector or perception service;
- a deterministic simulated producer used only by smoke/harness tests.

Keep public profiles stable:

- `camera-raw` means the main cleanup agent receives raw FPV evidence and may
  declare observations from image reasoning.
- `camera-labels` means structured candidates are produced from camera evidence
  by a camera inference producer.

Internally, both profiles should produce the same declaration shape and the same
observed-handle lifecycle.

## Public Tool Shape

Expose two declaration strategies as harness-selectable variants:

| Variant | Tool shape | Use |
| --- | --- | --- |
| `separate_registration` | `declare_visual_candidates(observation_id, candidates, producer_type, producer_id)` | Best for separate camera inference producers and explicit batch registration. |
| `inline_on_navigate` | `navigate_to_visual_candidate(source_observation_id, category, target_fixture_id, evidence_note, image_region, ...)` | Best for raw-FPV live agents; the agent declares only when it attempts to act. |

Both variants should call the same internal registration path. The default live
strategy should be `inline_on_navigate` unless harness evidence shows that
separate registration is more reliable.

Replace the producer-specific `infer_camera_model_candidates` path with the
producer-agnostic `declare_visual_candidates`. No compatibility layer is needed
for obsolete active surfaces.

## Declaration Schema

Every declared candidate should include:

- `source_observation_id`
- `category`
- `target_fixture_id`
- `evidence_note`
- `image_region`

Optional fields:

- `source_fixture_id`
- `confidence`
- `producer_type`
- `producer_id`
- `supersedes_observation_id`

`image_region` should accept:

- `{"type": "bbox", "value": [x, y, width, height]}`
- `{"type": "point", "value": [x, y]}`
- `{"type": "verbal_region", "value": "left side of sink counter"}`

Prefer bbox or point when the model can supply one. Verbal regions are allowed
for degraded image-localization cases but should produce lower grounding
confidence.

Declarations are append-only. A correction creates a new handle or a new
declaration that supersedes an earlier one; it should not mutate the prior
declaration in place.

## Grounding Boundary

The hidden grounding resolver may use execution-world geometry, segmentation,
camera calibration, and current public waypoint context to bind a declaration to
an executable object.

It must not use or expose:

- generated mess set;
- target count;
- acceptable destination sets;
- private scorer object results;
- hidden "what improves score" signals;
- internal object ids in agent-facing payloads.

The agent-facing grounding result should only expose:

- `grounding_status`: `resolved`, `ambiguous`, or `unresolved`;
- `grounding_confidence`;
- `grounding_basis`;
- `recovery_hint`;
- public handle id;
- public candidate fixture metadata.

If grounding is `ambiguous` or `unresolved`, the system may still record the
public handle for auditability, but `pick` must be blocked until the declaration
is resolved. Recovery hints should ask for a tighter bbox/point, a clearer
source fixture, or another observation.

## Active Camera Observation

Add bounded camera orientation control as a public perception aid:

- tool: `adjust_camera(yaw_delta_deg, pitch_delta_deg)`;
- yaw bound: `[-45, +45]` degrees;
- pitch bound: `[-20, +20]` degrees;
- each subsequent `observe` records a new `raw_fpv_###` row with the active
  camera offset;
- camera adjustment persists only at the current waypoint;
- navigation resets the adjustment.

This should be available across profiles but mainly graded under `camera-raw`.
The first live gate should track usage, not require it.

## MCP Image Delivery

For `camera-raw` live-agent runs, raw FPV observations must be delivered as
actual MCP image content, not only as file paths in JSON.

The Molmo cleanup MCP server should mirror the AI2-THOR MCP pattern:

```text
[json_state_text, MCPImage(data=<fpv_png_bytes>, format="png")]
```

The JSON state should still include artifact paths for trace/report reuse, but
the model-facing observation must contain the image block when the launcher
selects an image-capable model.

## Reports And Checkers

Reports should add or extend a **Model-Declared Observations** section showing:

- source observation id;
- producer type/id;
- category;
- target fixture;
- image region;
- evidence note;
- grounding status/confidence/basis;
- recovery hint;
- target plausibility;
- whether the handle was acted on.

Checker requirements for `camera-raw` should be split:

- contract gate: raw FPV observations exist, image blocks/artifacts were
  delivered, and structured labels did not leak before declaration;
- live-agent gate: model-declared observations exist and drive cleanup actions;
- success gate: restoration, coverage, disturbance, and semantic-loop checks.

For the first official Codex `gpt-5.5` gate, use:

| Metric | Required |
| --- | --- |
| `sweep_coverage_rate` | `1.0` |
| `raw_fpv_observations` | `>= 10` |
| `model_declared_observations` | `>= 7` |
| cleanup actions attempted from declarations | `>= 7` |
| restored objects | `>= 7/10` |
| structured label leakage before declaration | `0` |

`done()` should return a public insufficiency error when the agent attempts to
finish with too few declarations for a raw-FPV cleanup run. That error may name
public counts and recovery hints, but it must not reveal target ids, hidden
target count beyond the requested generated mess count already known to the
operator, acceptable destinations, or private scorer detail.

## Implementation Scope

1. Refactor `RealWorldCleanupContract`:
   - replace `infer_camera_model_candidates` with `declare_visual_candidates`;
   - add `navigate_to_visual_candidate`;
   - add `adjust_camera`;
   - unify `camera-raw` and `camera-labels` around Model-Declared Observation
     evidence;
   - keep unresolved handles unpickable.
2. Refactor `realworld_mcp_server`:
   - register the new tools;
   - return MCP image blocks for raw FPV observe responses;
   - include model-declared evidence in `run_result.json`.
3. Update deterministic direct and MCP-smoke flows:
   - use `declare_visual_candidates` with `producer_type=simulated_camera_model`
     for `camera-labels`;
   - keep `world-labels` unchanged.
4. Update agent skill and kickoff prompts:
   - `camera-raw` should instruct the agent to inspect FPV image blocks and use
     `navigate_to_visual_candidate` only when acting on a visual candidate;
   - `camera-labels` should instruct a producer-style declaration step.
5. Update reports and checkers:
   - add Model-Declared Observations reporting;
   - reject raw-FPV structured leakage before declaration;
   - require declaration evidence for raw-FPV cleanup-success claims.
6. Add focused tests:
   - contract registration and grounding;
   - unresolved handle pick blocking;
   - MCP image content delivery;
   - report rendering;
   - checker gates;
   - no private-truth leakage in Agent View or trace.
7. Run the harness comparison:
   - `separate_registration`;
   - `inline_on_navigate`;
   - default chosen by restoration rate, declaration count, semantic-order
     errors, and private-boundary checks.

## Non-Goals

- Do not create an opaque `cleanup_room()` MCP tool.
- Do not leak private generated mess, acceptable destinations, or scoring truth
  into declaration, grounding, reports, or traces.
- Do not require planner-backed manipulation proof for this perception refactor.
- Do not claim physical manipulation readiness; cleanup primitives remain
  labelled by their existing provenance.
- Do not preserve obsolete active tool names unless a historical artifact reader
  needs them.

## Verification Plan

Focused non-live verification:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py \
  tests/contract/reports/test_molmo_cleanup_report.py

ruff check roboclaws/molmo_cleanup scripts/molmo_cleanup examples/molmo_cleanup
```

Harness/live verification:

```bash
ROBOCLAWS_CODEX_PROVIDER=system \
ROBOCLAWS_CODEX_MODEL=gpt-5.5 \
just task::run molmo-cleanup codex camera-raw
```

Monitor with:

```bash
just molmo::status <run-dir>
```

If the local work-network guard, missing VLM key, missing image-capable Codex
route, or MolmoSpaces runtime blocks the live run, record that as a local
validation blocker rather than claiming the gate passed.

## Acceptance Criteria

- `camera-raw` gives image-capable agents a public path from FPV image evidence
  to observed handles.
- `camera-labels` uses the same declaration/evidence schema with a separate
  producer.
- `world-labels` remains a structured-label profile and is not described as
  image reasoning.
- Raw-FPV observations expose no structured labels before declaration.
- Model-declared handles carry source observation, producer, evidence note, image
  region, grounding status, and target plausibility.
- Unresolved declarations are visible in reports but blocked from `pick`.
- Official Codex `gpt-5.5` can run the `camera-raw` harness with the first-pass
  gate above or produces an artifact that pinpoints the remaining failure.

