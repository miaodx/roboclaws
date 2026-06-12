# Evidence Lane Naming Refactor

**Status:** Draft
**Created:** 2026-06-06
**Source:** 2026-06-06 naming discussion around RAW-FPV, camera-labels, and
visual grounding.

## Problem

The current household cleanup run surface mixes names from different abstraction
levels:

- `world-labels`
- `world-labels-sanitized`
- `camera-labels`
- `camera-raw`
- `visual_grounding=sim|grounding-dino|...`

These names work operationally, but they do not make the two conceptual axes
obvious:

1. What evidence shape the agent receives.
2. Which producer turns camera observations into structured camera candidates.

This makes `camera-labels`, pure RAW-FPV, simulator controls, and deployable
grounding sidecars harder to discuss without re-explaining the boundary.

## Decision

Introduce two public naming axes.

### Evidence Lane

`evidence_lane` describes what kind of evidence the agent receives:

```text
world-oracle-labels
world-public-labels
camera-grounded-labels
camera-raw-fpv
```

Meanings:

| Evidence lane | Meaning |
| --- | --- |
| `world-oracle-labels` | World-level simulator/state labels exposed as structured candidates; privileged cleanup upper bound. |
| `world-public-labels` | Public/sanitized world labels; perfect-detector ablation with destination/tool oracle hints removed. This is not a real semantic-map claim. |
| `camera-grounded-labels` | Structured camera candidates produced from FPV observations, with source observation id, reviewable bbox/mask, confidence, provenance, and grounding status. |
| `camera-raw-fpv` | Pure RAW-FPV path: the agent receives raw camera evidence and must declare/action candidates from image evidence itself. |

### Camera Labeler

`camera_labeler` applies only when
`evidence_lane=camera-grounded-labels`. It describes who turns the FPV
observation into structured camera candidates:

```text
sim-projected-labels
grounding-dino
yoloe
omdet-turbo
...
```

Meanings:

| Camera labeler | Meaning |
| --- | --- |
| `sim-projected-labels` | Deterministic control producer: simulator truth projected through camera visibility into reviewable camera candidates. |
| `grounding-dino` | Deployable open-vocabulary bbox proposer over FPV images. |
| `yoloe` | YOLO-family promptable/open-vocabulary proposer over FPV images. |
| `omdet-turbo` | OmDet-Turbo open-vocabulary proposer over FPV images. |

`camera_labeler` replaces the public command-surface role previously described
as `visual_grounding`. Internal service, benchmark, and report implementation
may continue to use visual-grounding terminology where the actual boundary is
the External Visual Grounding Service.

## Valid Combinations

| Evidence lane | Camera labeler |
| --- | --- |
| `world-oracle-labels` | Not applicable |
| `world-public-labels` | Not applicable |
| `camera-grounded-labels` | Required |
| `camera-raw-fpv` | Not applicable |

Examples:

```text
evidence_lane=world-oracle-labels
evidence_lane=world-public-labels
evidence_lane=camera-grounded-labels camera_labeler=sim-projected-labels
evidence_lane=camera-grounded-labels camera_labeler=grounding-dino
evidence_lane=camera-raw-fpv
```

Invalid combinations must hard fail:

```text
evidence_lane=camera-raw-fpv camera_labeler=grounding-dino
evidence_lane=world-oracle-labels camera_labeler=sim-projected-labels
evidence_lane=world-public-labels camera_labeler=grounding-dino
evidence_lane=camera-grounded-labels
```

The last example is invalid because `camera-grounded-labels` requires an
explicit labeler.

## Scope

Update the public command and artifact naming surface:

- household task launch grammar and `just` routing;
- cleanup profile/evidence-lane metadata;
- direct cleanup and MCP server CLI arguments;
- operator console route labels and default overrides;
- checker expectations;
- focused task-routing and profile tests;
- human docs that explain cleanup evidence lanes and camera labelers.

Update docs to make this clear:

```text
evidence_lane decides what the agent sees.
camera_labeler only applies to camera-grounded-labels and decides how camera
labels are produced.
```

## Non-Goals

- Do not weaken source-FPV locality, reviewable bbox/mask, or
  `navigation_authorized` requirements.
- Do not report `camera-grounded-labels` as pure RAW-FPV.
- Do not continue pure `camera-raw-fpv` prompt tuning as the production path.
- Do not introduce depth fusion, pointcloud fusion, map mutation, or occupancy
  rewrites in this naming slice.
- Do not change the External Visual Grounding Service HTTP schema just to match
  command naming; service terminology may remain visual-grounding focused.
- Do not rewrite historical output paths or old retrospective artifact names.

## Migration Shape

Because this is a semantic cleanup rather than a compatibility layer, new
commands and new artifacts should use the new names directly.

Old conceptual mapping:

| Old name | New name |
| --- | --- |
| `world-labels` | `evidence_lane=world-oracle-labels` |
| `world-labels-sanitized` | `evidence_lane=world-public-labels` |
| `camera-labels visual_grounding=sim` | `evidence_lane=camera-grounded-labels camera_labeler=sim-projected-labels` |
| `camera-labels visual_grounding=grounding-dino` | `evidence_lane=camera-grounded-labels camera_labeler=grounding-dino` |
| `camera-raw` | `evidence_lane=camera-raw-fpv` |

`smoke` remains a cheap verification preset, not an evidence lane.

## Verification

Focused deterministic checks:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup/test_molmo_cleanup_profiles.py \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_agent_server.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py
```

Lint/format checks for changed Python files:

```bash
ruff check <changed-python-files>
ruff format --check <changed-python-files>
git diff --check
```

Optional route dry runs:

```bash
ROBOCLAWS_JUST_TRACE=1 just task::run household-cleanup codex \
  evidence_lane=camera-grounded-labels camera_labeler=grounding-dino

ROBOCLAWS_JUST_TRACE=1 just task::run household-cleanup codex \
  evidence_lane=camera-raw-fpv
```

Acceptance requires:

- supported evidence lane names are exactly the new names;
- `camera-grounded-labels` requires `camera_labeler`;
- `camera_labeler` on world or raw-FPV lanes fails before launch;
- `sim-projected-labels` is documented as a camera-projected control producer,
  not a simulator execution environment;
- reports and checker messages distinguish evidence lane from camera labeler.

## Stop Condition

Stop this refactor when the public command surface, run metadata, checker
expectations, and human docs all expose the two-axis model without relying on
the old `profile` / `visual_grounding=sim` language for current runs.

## Preflight Contract

Preflight status: DRAFT

Task source: `docs/plans/refactor-evidence-lane-naming.md`.

Canonical source: `docs/plans/refactor-evidence-lane-naming.md`.

Route: durable `$intuitive-flow`.

### Goal

Rename the household cleanup evidence surface to the approved two-axis model:
`evidence_lane` plus `camera_labeler`.

### Scope

- Replace current public lane names with `world-oracle-labels`,
  `world-public-labels`, `camera-grounded-labels`, and `camera-raw-fpv`.
- Replace the public `visual_grounding` command role with `camera_labeler`.
- Use `sim-projected-labels` as the deterministic camera-label control
  producer.
- Hard fail invalid `evidence_lane` / `camera_labeler` combinations.
- Update just routing, CLI args, run metadata/checker expectations, operator
  console defaults, focused tests, and human docs.

### Non-Goals

- No depth, pointcloud, or map-fusion work.
- No weakening FPV locality, bbox/mask, or `navigation_authorized` gates.
- No HTTP visual-grounding service schema rewrite just for naming.
- No historical output path or retrospective artifact rewrite.

### Context Package

Must read:

- `docs/plans/refactor-evidence-lane-naming.md`
- `CONTEXT.md`
- `ARCHITECTURE.md`
- `docs/human/molmospaces-cleanup-mode-architecture.md`
- `docs/human/molmospaces-settings.md`

Useful evidence:

- `docs/adr/archive/superseded/0133-use-http-visual-grounding-service-for-real-camera-labels.md`
- `docs/status/active/raw-fpv-live-strategy-stabilization.md`

Do not read unless needed:

- old retrospectives and historical `output/` artifacts.

### Definition Of Done

SUCCESS only if:

- new task/just command surface uses `evidence_lane` and `camera_labeler`;
- new run metadata and checker language distinguish evidence lane from camera
  labeler;
- illegal combinations fail before launch;
- human docs explain the two axes without relying on old current-run names.

PARTIAL if:

- code routes work but reports/docs still contain old current-run terminology.

BLOCKED_NEEDS_DECISION if:

- updating artifact fields would force an irreversible schema split not covered
  by this plan.

Must not regress:

- existing FPV evidence gates, cleanup checker gates, and visual grounding
  service behavior.

### Verification

Focused deterministic checks:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup/test_molmo_cleanup_profiles.py \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_agent_server.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py
```

Lint and formatting checks for changed Python files:

```bash
ruff check <changed-python-files>
ruff format --check <changed-python-files>
git diff --check
```

### Execution Surface

- Main session: root supervisor.
- Worker: none initially.
- Worker-local goal: none.

### Main-Session Goal Prompt

```text
/goal execute docs/plans/refactor-evidence-lane-naming.md with intuitive-flow
```

### To Execute

```text
/goal execute docs/plans/refactor-evidence-lane-naming.md with intuitive-flow
```
