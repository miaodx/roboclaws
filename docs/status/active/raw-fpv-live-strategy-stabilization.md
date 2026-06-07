# RAW-FPV Live Strategy Stabilization

Owner/session: Codex active thread
Started: 2026-06-06 Asia/Shanghai
State: PARTIAL stop reached

## Scope

Stabilize the `camera-raw-fpv` live Codex cleanup lane after the strict FPV
visual-evidence authorization gate landed. Semantic-map priors may be tested as
planning context, but current-frame detector candidates remain out of scope for
this lane.

This is a strategy and skill-loop follow-up, not a relaxation of the grounding
contract. `navigate_to_object`, `pick`, and `navigate_to_visual_candidate` must
continue to require source-observation-local FPV evidence and
`navigation_authorized` candidates. Do not restore source-fixture, room, broad
category, synthetic bbox, or synthetic observation fallback authorization.

## Source Of Truth

- Gate plan: `docs/plans/refactor-fpv-visual-evidence-gate.md`
- Cleanup skill: `skills/molmo-realworld-cleanup/SKILL.md`
- RAW-FPV prompt helper: `roboclaws/household/raw_fpv_guidance.py`
- Live-agent kickoff prompt: `roboclaws/agents/prompts/household_cleanup.py`

## Current Evidence

The deterministic FPV gate is implemented and committed in
`4c857c82 fix: require source fpv navigation evidence`.

Focused contract/report/checker tests passed:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/reports/test_molmo_cleanup_report.py
```

Ruff and whitespace checks also passed for the changed Python files.

Live Codex evidence:

- `world-labels` passed at
  `output/household/household-cleanup/codex-report/0606_1128/seed-7`.
- `world-labels-sanitized` passed at
  `output/household/household-cleanup/codex-world-labels-sanitized/0606_1142/seed-7`.
- `camera-labels` with Grounding DINO passed the checker as `partial_success`
  at
  `output/household/household-cleanup/codex-camera-labels/0606_1227/seed-7`.
- `camera-raw` exposed the remaining live-agent limitation at
  `output/household/household-cleanup/codex-camera-raw/0606_1156/seed-7`:
  14/14 waypoints observed, 52 strict `navigate_to_visual_candidate` attempts,
  2 grounded cleanup chains, and 5 blocked `done` attempts.

The `camera-raw` result shows the gate is doing its job: unresolved visible
object guesses stayed non-actionable with
`source_observation_locality_unresolved` instead of being authorized by
fallback matching.

## Decision Boundary

The next target is Codex `camera-raw-fpv`. Codex should inspect the raw FPV
image blocks and drive the trace-preserving loop itself:

```text
observe
  -> choose one visible movable cleanup object
  -> navigate_to_visual_candidate with source_observation_id, category, and
     reviewable image locality
  -> pick
  -> navigate_to_receptacle
  -> open? -> place/place_inside -> close?
```

Keep `camera-raw` on `inline_on_navigate` for the next iteration. Do not add
normal raw-FPV pre-registration unless a later harness result shows that
prompt/loop tuning alone is insufficient.

Do not create a new public lane for semantic-map hints. `camera-raw-fpv` may use
Runtime Metric Map / semantic-map priors as planning context for where to look
and which categories to prioritize, but cleanup eligibility still requires
current-frame raw-FPV confirmation from the acting model. Current-frame detector
or hosted visual producer candidates remain `camera-grounded-labels`, not
`camera-raw-fpv`.

The next escalation is probe-first: measure whether structured raw-FPV JSON
with reviewable but not detector-grade image locality can produce enough
current-frame confirmable candidates. Only if that probe passes should the live
contract accept a relaxed raw-FPV locality form such as a structured coarse
region.

## Accepted Success Criteria

For `seed=7 generated_mess_count=5`, `camera-raw-fpv` is viable when:

- the run reaches full waypoint sweep coverage;
- Codex completes at least the generated mess success threshold, currently 5
  grounded cleanup chains;
- successful chains are backed by source-observation-local raw-FPV evidence,
  reviewable image locality, and `candidate_state=navigation_authorized`;
- no structured world labels, private target truth, or visual-grounding service
  producer candidates leak into the raw-FPV agent input;
- semantic-map priors, when provided, are planning context only and do not create
  executable object handles without current-frame confirmation;
- `done` is not accepted while public recovery blockers require more grounded
  cleanup work;
- focused contract/report/checker tests remain green.

Exact hidden restoration score remains diagnostic evidence for this lane. The
first viability gate is the reliable RAW-FPV loop primitive, not perfect private
destination agreement.

## Rejected Fixes

- Do not weaken source-FPV locality authorization.
- Do not restore room, source-fixture, broad category, synthetic bbox, or
  synthetic observation fallback authorization.
- Do not feed `world-labels` or `world-labels-sanitized` structured candidates
  into `camera-raw`.
- Do not call a detector or hosted visual producer while still claiming
  `camera-raw-fpv` success.
- Do not treat older movable-object semantic-map priors as executable cleanup
  handles without current-frame raw-FPV confirmation.
- Do not relax JSON structure for raw-FPV declarations; the open question is
  locality precision, not whether outputs remain structured.
- Do not change the public MCP surface into a whole-task cleanup tool.

## Next Action

Do not continue broad `camera-raw` prompt/loop tuning for this slice. The
2026-06-06 live gate reached the PARTIAL stop condition: prompt behavior
improved, but raw-FPV still completed only two grounded cleanup chains before
low-yield post-sweep retries.

The next justified slice is a perception-only raw-FPV probe over fixed frames.
It should compare no-prior and semantic-map-context variants while preserving
source-observation-local evidence and structured JSON output. Bbox precision is
diagnostic rather than assumed: the probe should separately report strict bbox
success and structured coarse-locality success. Do not change live cleanup
actionability until the probe shows that relaxed locality can meet the cleanup
threshold.

Reference live artifact:

```bash
output/household/household-cleanup/codex-camera-raw/0606_1537/seed-7
```

No `run_result.json`, `checker.log`, or `report.html` exists for that row
because it was manually stopped after ~26 minutes to avoid provider burn.

## 2026-06-06 Prompt-Loop Iteration Result

State: PARTIAL

Changed only the pure RAW-FPV skill/prompt loop:

- `roboclaws/household/raw_fpv_guidance.py`
- `roboclaws/agents/prompts/household_cleanup.py`
- `skills/molmo-realworld-cleanup/SKILL.md`
- `tests/contract/dev_tools/test_task_agent_just_recipes.py`

Prompt behavior now tells Codex to choose at most one fresh high-confidence
cleanup object per source observation, prefer reviewable bboxes, avoid
source-fixture guesses in minimal map mode, avoid stale/handled regions, and
move to a fresh observation instead of looping on the same
`source_observation_id/category/region`.

Deterministic verification passed:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py
ruff check roboclaws/agents/prompts/household_cleanup.py roboclaws/household/raw_fpv_guidance.py
ruff format --check roboclaws/agents/prompts/household_cleanup.py roboclaws/household/raw_fpv_guidance.py
git diff --check
```

Live Codex gate:

```bash
ROBOCLAWS_CODEX_PROVIDER=codex-env \
just task::run household-cleanup codex camera-raw seed=7 generated_mess_count=5
```

Run artifact:

`output/household/household-cleanup/codex-camera-raw/0606_1537/seed-7`

Observed outcome:

- Full public waypoint sweep completed: 14/14 waypoints observed.
- Two grounded cleanup chains completed:
  - `observed_006`: `candidate_state=navigation_authorized`,
    source FPV bbox from `raw_fpv_012`, placed on `anchor_fixture_006`.
  - `observed_007`: `candidate_state=navigation_authorized`,
    source FPV bbox from `raw_fpv_014`, placed inside `anchor_fixture_004`.
- Eleven `navigate_to_visual_candidate` attempts were made; nine ended as
  `visual_candidate_not_resolved` with reviewable bboxes but
  `source_observation_locality_unresolved`.
- No structured world labels, camera-label producer candidates, private target
  truth, detector service, or fallback authorization was introduced.
- The run did not call `done`; after full sweep and two chains it continued
  post-sweep fresh-observation retries below the RAW-FPV success threshold. The
  run was stopped manually with Ctrl-C after ~26 minutes to avoid provider burn,
  so no `run_result.json`, `checker.log`, or `report.html` was produced for this
  row.

Classification:

- Not visual declaration schema: tool calls used accepted bbox regions and
  omitted minimal-map target/source fixture guesses.
- Not placement policy: both authorized candidates completed pick and placement
  chains.
- Not environment/provider route: Codex, Docker, MCP, MuJoCo/MolmoSpaces, robot
  views, and waypoint navigation were available.
- Remaining failure is pure RAW-FPV visual grounding/image-understanding
  reliability: Codex can now produce some source-observation-local authorized
  chains, but prompt/loop tuning alone did not reliably find enough candidates
  from raw FPV image blocks to satisfy the generated mess threshold.
- Secondary loop issue: when below threshold after a full sweep, the pure
  prompt keeps making low-yield fresh-observation retries instead of producing a
  blocked closeout artifact.

Decision:

This satisfies the PARTIAL stop condition for the pure prompt/skill slice. The
next justified slice is a perception-only raw-FPV probe that keeps structured
JSON output and current-frame source locality, allows semantic-map priors only
as planning context, and measures whether coarse but reviewable image locality
can meet the cleanup threshold before live actionability changes.

## Stop Condition

Stop this slice when `camera-raw-fpv` either passes the accepted success
criteria above, or produces artifact-backed evidence that raw-FPV model
perception remains below threshold even with structured JSON, semantic-map
context, and relaxed coarse-locality probe scoring.

## Preflight Contract

Preflight status: DRAFT

Task source: `docs/status/active/raw-fpv-live-strategy-stabilization.md` plus
the 2026-06-06 and 2026-06-07 discussion.

Canonical source: `docs/status/active/raw-fpv-live-strategy-stabilization.md`.

Route: durable `$intuitive-flow`.

Goal: Build a perception-only `camera-raw-fpv` probe that measures whether
structured JSON output with strict bbox and relaxed coarse-locality scoring can
produce enough current-frame confirmable cleanup candidates before changing live
cleanup actionability.

### Execution Scope

- Add a probe script under `scripts/molmo_cleanup/` that reads fixed raw-FPV
  observation frames and public context from existing run artifacts.
- Include both failed raw-FPV frames and successful or partial-success contrast
  frames so scorer behavior is calibrated.
- Ask the model for JSON only: each observation may yield at most 1-3 cleanup
  candidates with `source_observation_id`, `category`, `evidence_note`,
  confidence, and either strict bbox locality or structured coarse locality.
- Represent coarse locality as structured fields, not free text: a fixed screen
  grid region such as `upper_left`, `upper_center`, `upper_right`,
  `middle_left`, `center`, `middle_right`, `lower_left`, `lower_center`, or
  `lower_right`, plus an optional surface hint such as `floor`, `table`,
  `shelf`, `counter`, `bed`, `sofa`, or `unknown`.
- Compare a minimal first matrix: `CodexENV gpt-5.5` with baseline JSON prompt
  vs skill JSON plus semantic-map context.
- Provide semantic-map context only as compressed planning context:
  waypoint/area, likely categories, historical observation direction, and
  `needs_confirm`; do not expose executable observed-object handles.
- Score strict-bbox success separately from coarse-locality success against an
  offline private-label scorer that is never included in the model prompt.
- Score coarse locality by region/object overlap plus independent category
  matching; do not require a precise center-point hit for coarse locality.
- Simulate live cleanup constraints in the primary metric: at most one acted
  candidate per observation, duplicate/already-handled candidates do not count
  toward threshold, and 1-3 candidate lists are used only for recall diagnostics
  beyond the live-like top candidate.
- Report failure classes at least as `schema_failure`,
  `locality_too_coarse_or_invalid`, and `semantic_mismatch/unresolved`.

### Execution Non-Goals

- No weakening source-FPV locality authorization.
- No room/source-fixture/category/synthetic bbox fallback restoration.
- No world-label or camera-label leakage into pure `camera-raw`.
- No detector/VLM producer assist in this slice.
- No live cleanup actionability change until the probe shows relaxed locality can
  meet the cleanup threshold.
- No new public lane, MCP tool, or whole-task cleanup tool.
- No broad report redesign beyond the probe output.

### Context Package

Must read:

- `docs/status/active/raw-fpv-live-strategy-stabilization.md`
- `docs/plans/refactor-fpv-visual-evidence-gate.md`
- `skills/molmo-realworld-cleanup/SKILL.md`
- `roboclaws/household/raw_fpv_guidance.py`
- `roboclaws/agents/prompts/household_cleanup.py`
- `tests/contract/dev_tools/test_task_agent_just_recipes.py`
- `tests/contract/molmo_cleanup/test_molmo_realworld_contract.py`
- `tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`

Useful evidence:

- `output/household/household-cleanup/codex-camera-raw/0606_1156/seed-7`
- `output/household/household-cleanup/codex-camera-raw/0606_1537/seed-7`
- `output/household/household-cleanup/codex-camera-labels/0606_1227/seed-7`
- `output/molmo/codex-harness8/0607_1005-codexenv-detached`
- `output/molmo/codex-harness8/0607_0943-codexenv-cleanwt/_semantic-map-prior-dino/0607_0943/seed-7/runtime_metric_map.json`

Do not read unless needed:

- Isaac/Agibot backend plans
- unrelated visual parity docs
- historical retrospectives

### Definition Of Done

SUCCESS only if:

- Focused deterministic tests pass.
- The probe ingests fixed raw-FPV frames and writes a reproducible report under
  `output/molmo/raw-fpv-perception-probe/`.
- The report separates strict-bbox and coarse-locality scoring.
- The report includes `unique_confirmable_count`, `duplicate_count`, and a
  live-like top-candidate score that prevents repeated sightings of the same
  object from satisfying the threshold.
- The report shows whether the first CodexENV matrix reaches the cleanup
  threshold: `>=5` unique current-frame confirmable candidates for
  `generated_mess_count=5`, or `>=7` for `generated_mess_count=10`.
- The report emits one route recommendation:
  `keep_raw_fpv_baseline_only`, `try_live_coarse_locality_contract`, or
  `prefer_camera_grounded_labels`.
- Private labels are used only by the offline scorer and are not present in
  prompts or agent-facing input dumps.
- Semantic-map context appears only as compressed planning context and does not
  expose executable prior handles.

PARTIAL if:

- The probe infrastructure runs and reports schema/locality/semantic failure
  classes, but real-provider execution is skipped or inconclusive.

BLOCKED_NEEDS_DECISION if:

- Probe evidence shows live cleanup would require accepting coarse locality,
  adding a detector/VLM producer assist, pre-registration, public MCP contract
  changes, or fallback broadening.
- Required local Codex/Docker/simulator/provider route is unavailable.

Must not regress:

- FPV evidence gate.
- RAW-FPV done blockers.
- Structured-label leakage checks.
- `world-labels`, `world-labels-sanitized`, and `camera-labels` prompt
  contracts.

### Verification

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/dev_tools/test_task_agent_just_recipes.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py
```

```bash
ruff check scripts/molmo_cleanup roboclaws/agents/prompts/household_cleanup.py roboclaws/household/raw_fpv_guidance.py
ruff format --check scripts/molmo_cleanup roboclaws/agents/prompts/household_cleanup.py roboclaws/household/raw_fpv_guidance.py
git diff --check
```

Optional model probe after deterministic verification:

```bash
ROBOCLAWS_CODEX_PROVIDER=codex-env \
python scripts/molmo_cleanup/run_raw_fpv_perception_probe.py --provider codex-env --model gpt-5.5
```

### Execution Surface

- Main session: root supervisor, edits, verification, final pass/fail
  classification.
- Worker: none initially.
- Worker-local goal: none.

### Main-Session Goal Prompt

```text
/goal execute docs/status/active/raw-fpv-live-strategy-stabilization.md with intuitive-flow
```

### To Execute

```text
/goal execute docs/status/active/raw-fpv-live-strategy-stabilization.md with intuitive-flow
```

### Approval Gate

Reply `LGTM`, `approve`, or `go ahead` to approve this contract.
