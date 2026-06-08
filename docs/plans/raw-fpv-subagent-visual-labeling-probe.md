# RAW-FPV Subagent Visual Labeling Probe

**Status:** Draft preflight
**Created:** 2026-06-08
**Source:** RAW-FPV live strategy discussion plus `intuitive-planning-loop`
review of the existing dedicated-labeler plan.
**Canonical source:** this file

## Problem

The 2026-06-08 RAW-FPV perception probe proved that the current inline
`camera-raw-fpv` prompting did not meet the live cleanup hidden-target recovery
threshold. It did not prove that a clean-context visual labeling agent cannot
produce useful semantic labels from raw robot FPV images.

The current scorer only measures generated hidden targets. In the 0608 probe,
many model-declared candidates landed on frames that had no private scorer
labels, so they were ignored as `missing_private_label` instead of being judged
as possible visible movable objects. That is the wrong contract for testing the
next hypothesis.

## Hypothesis

A dedicated RAW-FPV visual labeling skill, run in a clean-context subagent over
small frame groups, can produce more controllable and useful structured labels
for visible cleanup-relevant movable objects than the existing inline cleanup
prompt. This should be evaluated as perception-only evidence before any live
cleanup actionability change.

## Goals

- Define a dedicated RAW-FPV visual labeler contract for a clean-context
  subagent.
- Run the labeler over RAW-FPV frame groups, not only isolated single frames.
- Score two metrics separately:
  - `visible_movable_label_quality`
  - `hidden_target_recovery`
- Generate or consume scorer-only all-visible movable-object truth without
  leaking private labels, hidden targets, or executable handles into prompts.
- Keep `camera-raw-fpv` live cleanup actionability unchanged until probe
  evidence justifies a separate contract decision.

## Non-Goals

- Do not relax source-FPV actionability.
- Do not feed detector or camera-label producer candidates into
  `camera-raw-fpv` while claiming pure RAW-FPV success.
- Do not promote subagent labels into live cleanup inputs in this slice.
- Do not run new paid/provider calls before the offline probe contract and
  scorer are working on saved artifacts.
- Do not claim this probe replaces `camera-grounded-labels`; it tests a
  different perception hypothesis.

## Key Boundary

The first implementation is an offline/perception probe. The subagent consumes
public RAW-FPV frame evidence and returns structured visual labels. The cleanup
agent does not consume those labels as executable observed handles.

If a later phase feeds those labels into live cleanup, that is a separate
public-lane/product decision. It may become a `camera-grounded-labels` producer
or a new assisted RAW-FPV contract, but it must not silently change
`camera-raw-fpv`.

## Labeler Contract

Input:

- 3-6 neighboring RAW-FPV frames from the same waypoint, sweep segment, or
  source observation neighborhood.
- Public frame ids and image artifacts.
- Public waypoint/room context when already agent-facing.
- Optional public semantic-map planning hints, marked non-executable.

Prompt must not include:

- private labels;
- generated hidden target ids;
- acceptable destination truth;
- executable observed-object handles;
- detector/camera-label producer candidates.

Required output fields per label:

- `evidence_frame_id`
- `category`
- `category_family`
- `coarse_region`
- `confidence`
- `is_cleanup_relevant`

Optional output fields:

- `bbox`
- `surface_hint`
- `reason_not_actionable`

`reason_not_actionable` may describe public visual uncertainty, occlusion,
duplicate/ambiguous evidence, or insufficient locality. It must not claim
private target state or private actionability truth.

## Scorer Contract

### `visible_movable_label_quality`

Scores all visible cleanup-relevant movable objects above the chosen
pixel/visibility threshold.

Fixtures and surfaces such as tables, beds, counters, shelves, sinks, cabinets,
and floors are not object hits. They may contribute only as `surface_hint`.

Primary outputs:

- recall;
- precision;
- category match tier;
- coarse locality match;
- duplicate rate;
- schema failure rate.

### `hidden_target_recovery`

Scores only generated mess/private target ids. This remains the live cleanup
compatibility diagnostic and must not share a denominator with
`visible_movable_label_quality`.

The existing live-like top-candidate threshold remains diagnostic:

```text
unique hidden target recovery >= 5
```

No live cleanup actionability change is allowed unless this diagnostic is met
and a separate contract decision is accepted.

## Category And Locality Defaults

Category matching should report tiers:

- `exact`
- `semantic`
- `coarse_family`
- `mismatch`

Use canonical `category` plus `category_family`. Initial families may reuse the
existing cleanup prompt/scorer families:

- `food`
- `dish`
- `book`
- `linen`
- `toy`
- `electronics`

Examples:

- `potato` -> `food`
- `plate`, `bowl`, `cup`, `mug` -> `dish`
- `pillow` -> `linen`
- `remote control` -> `electronics`

Locality does not need detector-grade precision. A normalized bbox is useful
when available, but a structured 3x3 coarse screen region is acceptable for the
first probe when it is reviewable against the source frame.

## First Implementation Slice

1. Add a dedicated `raw-fpv-visual-labeler` skill or skill-owned prompt
   contract for the subagent.
2. Extend or wrap `scripts/molmo_cleanup/run_raw_fpv_perception_probe.py` so it
   can build frame-group inputs and ingest richer labeler output.
3. Add scorer support for split metrics:
   `visible_movable_label_quality` and `hidden_target_recovery`.
4. Generate or load scorer-only all-visible movable truth for the existing 0608
   RAW-FPV corpus.
5. Re-score saved outputs offline first. Only after the contract works, run a
   real provider/subagent matrix as a follow-up.
6. Update docs so current `prefer_camera_grounded_labels` wording is limited to
   the current live cleanup path and hidden-target recovery gate.

## Acceptance Criteria

SUCCESS only if:

- the probe can run offline on the existing 0608 RAW-FPV corpus;
- prompt inputs pass privacy checks:
  - `private_labels_in_prompt_inputs=false`;
  - no executable prior handles in agent-facing input;
- labeler outputs have zero schema failures on fixture tests or saved
  predictions;
- the report separates `visible_movable_label_quality` from
  `hidden_target_recovery`;
- fixtures/surfaces are scored only as hints, not object hits;
- focused unit tests cover taxonomy matching, frame grouping, schema parsing,
  privacy checks, and split metric reporting.

PARTIAL if:

- the offline contract and scorer work, but all-visible movable truth is too
  sparse for a meaningful quality claim on the current saved corpus. In that
  case, the next step is corpus/truth generation, not live actionability.

BLOCKED_NEEDS_DECISION if:

- the implementation requires changing public evidence-lane semantics;
- subagent labels are proposed as live executable cleanup handles;
- scorer truth scope needs to include fixtures or non-cleanup objects;
- a real provider run is needed before the offline contract is testable.

Must not regress:

- existing RAW-FPV source locality authorization;
- `camera-grounded-labels` producer boundaries;
- private-label prompt exclusion;
- focused RAW-FPV perception probe tests.

## Verification

Expected deterministic gates:

```bash
ruff check scripts/molmo_cleanup tests/unit/molmo_cleanup
ruff format --check scripts/molmo_cleanup tests/unit/molmo_cleanup
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py
```

If contract or report code outside the probe changes, also run:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py
```

Offline artifact gate should reuse the existing 0608 corpus and saved probe
artifacts before any new provider calls.

## Open Decisions For Review

- Confirm that first-slice truth scope is only cleanup-relevant movable
  objects.
- Confirm that fixtures/surfaces are hints only.
- Confirm that first implementation stays offline/perception-only and does not
  feed labels into live cleanup.

Recommended answer for all three: yes.

## Preflight Contract

Preflight status: DRAFT

Task source: `docs/plans/raw-fpv-subagent-visual-labeling-probe.md` plus the
2026-06-08 `intuitive-planning-loop` review.

Canonical source: `docs/plans/raw-fpv-subagent-visual-labeling-probe.md`.

Route: durable `$intuitive-flow`, with a bounded implementation slice. If the
executor keeps the change entirely inside the perception probe, route the code
work through `$intuitive-refactor` as the implementation sub-slice.

Goal:
Build a perception-only RAW-FPV subagent visual labeling probe that measures
visible cleanup-relevant movable-object label quality separately from hidden
generated-target recovery.

### Scope

- Add or define the `raw-fpv-visual-labeler` skill/prompt contract.
- Build frame-group public inputs from existing RAW-FPV observation artifacts.
- Parse richer visual-labeler outputs with category, family, coarse locality,
  confidence, cleanup relevance, optional bbox, optional surface hint, and
  optional public uncertainty reason.
- Add split scorer/report metrics:
  - `visible_movable_label_quality`
  - `hidden_target_recovery`
- Generate or consume scorer-only all-visible movable-object truth for the
  existing 0608 RAW-FPV corpus.
- Keep all private labels, hidden target ids, acceptable destination truth, and
  executable handles out of prompts.
- Update focused docs where the current `prefer_camera_grounded_labels`
  conclusion could be read as a general RAW-FPV semantic-labeling failure.

### Non-Goals

- No live cleanup actionability change.
- No promotion of subagent labels into executable observed handles.
- No new public evidence lane or MCP tool.
- No detector/camera-label producer candidates inside `camera-raw-fpv`.
- No new paid/provider/model calls before the offline contract is green.
- No broad multi-scene benchmark in this first slice.

### Context Package

Must read:

- `docs/plans/raw-fpv-subagent-visual-labeling-probe.md`
- `CONTEXT.md`
- `docs/status/active/raw-fpv-live-strategy-stabilization.md`
- `docs/human/molmospaces-visual-grounding-results.md`
- `docs/human/molmospaces-settings.md`
- `scripts/molmo_cleanup/run_raw_fpv_perception_probe.py`
- `scripts/molmo_cleanup/generate_raw_fpv_sweep_corpus.py`
- `tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py`

Useful evidence:

- `output/molmo/raw-fpv-perception-probe/0608_codexenv_public_sweep_plus_saved_trace_raw_only_max18/report.json`
- `output/molmo/raw-fpv-perception-probe/0608_codexenv_public_sweep_plus_saved_trace_raw_only_max18/private_score.json`
- `output/molmo/raw-fpv-sweep-corpus/0608_public_sweep_default_offsets/report.json`

Do not read unless needed:

- Historical retrospectives.
- Isaac/renderer parity plans.
- Real visual-grounding sidecar benchmark details.
- Full cleanup live traces outside the existing 0608 RAW-FPV probe artifacts.

### Definition Of Done / Acceptance Criteria

SUCCESS only if:

- offline probe inputs can be built from the existing 0608 RAW-FPV corpus;
- visual-labeler outputs are accepted through a strict schema;
- prompt privacy checks prove no private labels, hidden target ids, acceptable
  destinations, or executable handles are in agent-facing inputs;
- the report separately shows `visible_movable_label_quality` and
  `hidden_target_recovery`;
- fixture/surface labels are scored only as `surface_hint`, not object hits;
- category matching reports exact, semantic, coarse-family, and mismatch tiers;
- deterministic focused tests pass.

PARTIAL if:

- the offline probe contract and split scorer are implemented, but the existing
  0608 corpus lacks enough all-visible movable truth for a meaningful quality
  claim. In that case, produce a precise corpus/truth-generation follow-up and
  do not change live actionability.

BLOCKED_NEEDS_DECISION if:

- implementing the probe requires changing public lane semantics;
- subagent labels need to become live executable handles;
- the scorer needs fixture/non-cleanup objects as object hits;
- a real provider call is needed before the offline contract can be tested.

Must not regress:

- source-FPV locality authorization;
- `camera-grounded-labels` producer boundaries;
- private scorer truth exclusion from prompts;
- existing RAW-FPV perception probe tests and artifacts.

### Verification

Required deterministic gates:

```bash
ruff check scripts/molmo_cleanup tests/unit/molmo_cleanup
ruff format --check scripts/molmo_cleanup tests/unit/molmo_cleanup
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py
```

Run these if shared contract/report/checker code changes:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py
```

Expected artifact proof:

- an offline report under `output/molmo/raw-fpv-perception-probe/<run-id>/`
  showing split metrics and privacy checks;
- a private score artifact proving scorer-only all-visible movable truth did
  not enter prompt inputs.

### Execution Surface

- Main session: root supervisor, route control, and final verifier.
- Worker: optional bounded `skill-runner` worker for implementation if the
  executor expects the probe/scorer work to span multiple files.
- Worker-local goal: implement the offline RAW-FPV visual-labeler probe slice
  from this plan; stop before paid/provider calls or live actionability changes.

### Main-Session `/goal` Prompt

```text
/goal execute docs/plans/raw-fpv-subagent-visual-labeling-probe.md with intuitive-flow
```

### To Execute

```text
/goal execute docs/plans/raw-fpv-subagent-visual-labeling-probe.md with intuitive-flow
```

Approval gate:
Reply `LGTM`, `approve`, or `go ahead` to approve this preflight. If approval
changes scope, update this contract before implementation.
