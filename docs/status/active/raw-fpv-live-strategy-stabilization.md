# RAW-FPV Live Strategy Stabilization

Owner/session: Codex active thread
Started: 2026-06-06 Asia/Shanghai
State: PARTIAL stop reached

## Scope

Stabilize the pure `camera-raw` live Codex cleanup lane after the strict FPV
visual-evidence authorization gate landed.

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

The next target is pure Codex RAW-FPV. Codex should inspect the raw FPV image
blocks and drive the trace-preserving loop itself:

```text
observe
  -> choose one visible movable cleanup object
  -> navigate_to_visual_candidate with source_observation_id, category, and bbox
  -> pick
  -> navigate_to_receptacle
  -> open? -> place/place_inside -> close?
```

Keep `camera-raw` on `inline_on_navigate` for the next iteration. Do not add
normal raw-FPV pre-registration unless a later harness result shows that
prompt/loop tuning alone is insufficient.

If pure RAW-FPV still cannot pass after one focused prompt/skill iteration, the
next escalation may add a non-privileged visual producer assist, but that must
be reported as an assisted RAW-FPV lane, not as pure `camera-raw` success.

## Accepted Success Criteria

For `seed=7 generated_mess_count=5`, pure `camera-raw` is viable when:

- the run reaches full waypoint sweep coverage;
- Codex completes at least the generated mess success threshold, currently 5
  grounded cleanup chains;
- successful chains are backed by source-observation-local FPV bbox evidence and
  `candidate_state=navigation_authorized`;
- no structured world labels, private target truth, or visual-grounding service
  producer candidates leak into the pure RAW-FPV agent input;
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
- Do not call a detector or hosted visual producer while still claiming pure
  Codex RAW-FPV success.
- Do not change the public MCP surface into a whole-task cleanup tool.

## Next Action

Do not continue pure `camera-raw` prompt/loop tuning for this slice. The
2026-06-06 live gate reached the PARTIAL stop condition: prompt behavior
improved, but pure RAW-FPV still completed only two grounded cleanup chains
before low-yield post-sweep retries.

The next justified slice is an explicitly labeled assisted RAW-FPV lane. It
should preserve source-observation-local FPV evidence, reviewable bboxes, and
`navigation_authorized` requirements while adding a non-privileged visual
producer assist or pre-registration path. Do not claim that lane as pure
`camera-raw` success.

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
next justified slice should be explicitly labeled assisted RAW-FPV, using a
non-privileged visual producer assist or pre-registration path while preserving
the same source-FPV locality, bbox reviewability, and
`navigation_authorized` requirements. Do not report that assisted lane as pure
`camera-raw` success.

## Stop Condition

Stop this slice when pure `camera-raw` either passes the accepted success
criteria above, or produces artifact-backed evidence that prompt/loop tuning is
insufficient and the next justified slice is an explicitly labeled assisted
RAW-FPV lane.

## Preflight Contract

Preflight status: DRAFT

Task source: `docs/status/active/raw-fpv-live-strategy-stabilization.md` plus
the 2026-06-06 discussion.

Canonical source: `docs/status/active/raw-fpv-live-strategy-stabilization.md`.

Route: durable `$intuitive-flow`.

Goal: Stabilize the pure Codex `camera-raw` live cleanup lane by tuning only
the RAW-FPV skill/prompt loop, while preserving strict source-FPV
authorization.

### Execution Scope

- Tune `camera-raw` live-agent instructions in
  `skills/molmo-realworld-cleanup/SKILL.md`,
  `roboclaws/household/raw_fpv_guidance.py`, and/or
  `roboclaws/agents/prompts/household_cleanup.py`.
- Keep `inline_on_navigate` as the normal pure RAW-FPV strategy.
- Make Codex more reliably execute
  `observe -> visible movable object -> bbox -> navigate_to_visual_candidate -> pick/place`.
- Update focused tests for prompt/skill contract if text behavior changes.
- Run one pure `camera-raw` Codex live gate after deterministic tests pass.

### Execution Non-Goals

- No weakening source-FPV locality authorization.
- No room/source-fixture/category/synthetic bbox fallback restoration.
- No world-label or camera-label leakage into pure `camera-raw`.
- No detector/VLM producer assist in this slice.
- No new MCP tool or whole-task cleanup tool.
- No broad report redesign.

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
- `output/household/household-cleanup/codex-camera-labels/0606_1227/seed-7`

Do not read unless needed:

- Isaac/Agibot backend plans
- unrelated visual parity docs
- historical retrospectives

### Definition Of Done

SUCCESS only if:

- Focused deterministic tests pass.
- Pure `camera-raw` live Codex run reaches full sweep coverage.
- It completes at least 5 grounded cleanup chains for
  `seed=7 generated_mess_count=5`.
- Successful chains have source-observation-local FPV bbox evidence and
  `candidate_state=navigation_authorized`.
- Checker passes the RAW-FPV gates with no structured-label leakage.

PARTIAL if:

- Deterministic prompt/contract behavior improves, but live `camera-raw` still
  fails with artifact-backed classification showing prompt/loop tuning is
  insufficient.

BLOCKED_NEEDS_DECISION if:

- Passing pure RAW-FPV appears to require detector/VLM producer assist,
  pre-registration, public MCP contract changes, or fallback broadening.
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
ruff check roboclaws/agents/prompts/household_cleanup.py roboclaws/household/raw_fpv_guidance.py
ruff format --check roboclaws/agents/prompts/household_cleanup.py roboclaws/household/raw_fpv_guidance.py
git diff --check
```

Live gate:

```bash
ROBOCLAWS_CODEX_PROVIDER=codex-env \
just task::run household-cleanup codex camera-raw seed=7 generated_mess_count=5
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
