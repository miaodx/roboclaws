---
refactor_scope: fpv-visual-evidence-gate
status: PARTIAL
accepted_severities:
  - P0
  - P1
  - P2
last_verified: null
---

# Refactor Scope: FPV Visual Scan/Confirm Gate

## Status

PARTIAL

## Target

Make cleanup navigation actionable only after a real agent-facing FPV
scan/confirm step proves the candidate is visible in the source frame. This
gate applies to both `world-labels` variants, RAW-FPV manual declarations,
camera-labels, fake HTTP, and real visual-grounding producers such as
Grounding DINO.

World labels may provide semantic candidates and orientation hints, but they
must not directly authorize `navigate_to_object`. Before navigation, the robot
must orient/scan toward the candidate, observe, and bind the candidate to a
real FPV bbox from that source observation. RAW-FPV and camera-labels
candidates must resolve only from the exact source observation locality; silent
source-fixture, room, or broader category fallbacks must not authorize
navigation.

## Accepted Severities

- P1: Cleanup can continue from a structured or model-declared candidate even
  when the agent-facing FPV evidence is not reviewable.
- P1: RAW-FPV and world-labels expose different implicit actionability rules,
  which makes reports appear causally disconnected from the action chain.
- P1: `world-labels` and `world-labels-sanitized` can inherit synthetic bbox
  evidence from `_image_bbox(handle)`, so `navigate_to_object` trusts a
  report-like bbox that was not produced by a real current FPV observation.
- P1: `navigate_to_visual_candidate` can silently broaden from source waypoint
  fixtures to source-fixture or room fallback matching. In minimal-map mode the
  room branch is not a reliable same-room constraint and can resolve a bbox to
  an object in another room.
- P1: Reported `observe -> navigate` chains can show direction jumps because
  the source observation is a semantic candidate scan while the navigation uses
  backend semantic pose/yaw.
- P2: Report timeline does not make the candidate producer, source
  observation, FPV bbox/region, locality check, reviewability, and
  actionability explicit enough for human review.

## Accepted Cleanup Checklist

- [x] Define candidate states explicitly: `semantic_candidate`,
  `visual_scan_required`, `visually_confirmed`, and
  `navigation_authorized`.
- [x] Split semantic hints from visual authorization. `world-labels` and
  `world-labels-sanitized` may expose object handles/categories and orientation
  hints, but the initial detections must not carry navigation-authorizing
  synthetic bbox evidence.
- [x] Add or expose a pre-navigation visual scan/confirm flow. The robot should
  rotate/orient toward the semantic candidate, run `observe`, and bind the
  handle to a real source FPV bbox before `navigate_to_object` can succeed.
- [x] Require `navigate_to_object` / `pick` to accept only
  `navigation_authorized` candidates with real source observation provenance.
  Synthetic observation ids such as `visible_detection:*` and generated
  `_image_bbox(handle)` boxes must block with a concrete next tool such as
  `orient_to_candidate`/`adjust_camera` plus `observe`.
- [x] Remove action-authorizing resolver fallbacks from
  `navigate_to_visual_candidate`: no source-fixture fallback, no room fallback,
  and no broad category-only match when the exact source observation locality
  does not resolve.
- [x] Keep destination inference/advisory helpers separate from source-object
  grounding. Destination suggestions may be heuristic, but they must not make a
  source candidate actionable without FPV confirmation.
- [x] Preserve Grounding DINO/fake HTTP as bbox-evidence producers using the
  same visual evidence schema; they do not get a separate privileged resolver.
- [x] Update reports so each navigation card links the full evidence chain:
  semantic candidate or raw source, orientation/scan observation, source FPV
  bbox, locality check, candidate state, and navigation authorization.
- [x] Replace old fallback-positive tests with block/unresolved tests, and add
  regression coverage for default world-labels, sanitized world-labels,
  RAW-FPV, and camera-labels/Grounding-DINO-shaped candidates.
- [x] Keep held-object `done` blockers and existing sanitized/RAW-FPV readiness
  contracts green.

## Parked Cross-Seam / Future Ideas

- Real Grounding DINO threshold tuning and GPU benchmark runs remain local
  provider/GPU gates.
- Pure RAW-FPV live-agent strategy stabilization is tracked separately in
  `docs/status/active/raw-fpv-live-strategy-stabilization.md`. That follow-up
  must not weaken source-FPV locality authorization or reintroduce room,
  source-fixture, broad-category, synthetic bbox, or synthetic observation
  fallback authorization.
- Broader report visual redesign is out of scope unless needed for the
  actionability evidence.
- Planner-backed manipulation proof is a separate primitive gate.
- Fallbacks outside this grounding/navigation seam, such as planner proof
  fallback request generation or renderer/material fallback diagnostics, are
  not part of this cleanup.

## Preflight Contract

Preflight status: DRAFT

Task source: approved discussion plus this reopened plan gate.

Canonical source: `docs/plans/refactor-fpv-visual-evidence-gate.md`.

Route: `$intuitive-refactor`.

Goal: Implement the reopened FPV visual scan/confirm gate so cleanup navigation
is authorized only by real source-frame visual evidence, with
action-authorizing fallbacks removed.

### Scope

- Add explicit candidate states: `semantic_candidate`,
  `visual_scan_required`, `visually_confirmed`, and
  `navigation_authorized`.
- Apply the gate to `world-labels` and `world-labels-sanitized`.
- Prevent synthetic bbox and synthetic observation ids from authorizing
  `navigate_to_object` or `pick`.
- Remove action-authorizing source-fixture, room, and category-only fallback
  resolution from `navigate_to_visual_candidate`.
- Keep Grounding DINO and fake HTTP as normal bbox producers through the same
  evidence schema.
- Update reports to show source observation, bbox, locality check, candidate
  state, and navigation authorization chain.
- Update tests that currently expect fallback success.

### Non-Goals

- No real Grounding DINO threshold tuning.
- No broad report redesign beyond evidence-chain clarity.
- No planner/manipulation proof refactor.
- No unrelated fallback cleanup outside grounding/navigation.

### Context Package

Must read:

- `docs/plans/refactor-fpv-visual-evidence-gate.md`
- `roboclaws/household/realworld_contract.py`
- `roboclaws/household/semantic_timeline.py`
- `roboclaws/household/report.py`
- `tests/contract/molmo_cleanup/test_molmo_realworld_contract.py`
- `tests/contract/reports/test_molmo_cleanup_report.py`

Useful evidence:

- `output/household/verify-latest-world-labels-codex-env/0605_1826/seed-7/report.html`
- `output/household/verify-latest-raw-fpv-codex-env/0605_1833/seed-7/report.html`

Do not read unless needed:

- Historical retrospectives.
- Isaac/renderer fallback plans unrelated to cleanup candidate grounding.

### Definition Of Done / Acceptance Criteria

SUCCESS only if:

- World-label and sanitized candidates cannot navigate from synthetic bbox
  evidence alone.
- Navigation requires a real source FPV observation and bbox/locality
  confirmation.
- RAW-FPV/camera-label candidates do not resolve through source-fixture, room,
  or category-only fallback.
- The report shows the authorization chain clearly.
- Focused contract/report/checker tests pass.

PARTIAL if:

- Deterministic contract behavior is fixed, but one or more required Codex
  cleanup demo lanes still fail and the failure has a concrete artifact-backed
  diagnosis plus a proposed fix.

BLOCKED_NEEDS_DECISION if:

- Implementation requires adding a new public MCP tool instead of using the
  existing `adjust_camera`/observe flow.
- A required Codex cleanup demo cannot be run because local credentials,
  Docker/runtime, simulator, GPU, or Grounding DINO service access is
  unavailable.

Must not regress:

- Held-object `done` blockers.
- Existing RAW-FPV readiness gates.
- Sanitized world-label payload privacy.
- Grounding DINO/fake HTTP producer compatibility.

### Verification

- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_contract.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/reports/test_molmo_cleanup_report.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py`

Required local Codex cleanup demos after deterministic pass:

- `just task::run household-cleanup codex world-labels seed=7 generated_mess_count=5`
- `just task::run household-cleanup codex world-labels-sanitized seed=7 generated_mess_count=5`
- `just task::run household-cleanup codex camera-raw seed=7 generated_mess_count=5`
- `just task::run household-cleanup codex camera-labels seed=7 generated_mess_count=5 visual_grounding=grounding-dino`

If any required demo fails or produces a suspicious report, inspect its
`trace.jsonl`, `run_result.json`, `agent_view.json`, `checker.log`, and
`report.html`; classify whether the issue is behavior, contract, report, model
prompting, or environment; then fix or produce a concrete follow-up patch plan.
Do not close this gate solely by recording a failed demo.

### Execution Surface

- Main session: root supervisor and final verifier.
- Worker: none initially.
- Worker-local goal: none.

### Main-Session Goal Prompt

```text
/goal
Execute the approved contract for FPV visual scan/confirm and fallback removal.
Keep this main session as the root supervisor.
Use $intuitive-flow for route control and skill-runner only for bounded workers.
Do not mark complete unless the acceptance criteria pass.
```

### Approval Gate

Reply `LGTM`, `approve`, or `go ahead` to execute; otherwise request edits.

## Evidence Ladder

- L1/L2 contract:
  - `./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_contract.py`
  - `./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`
- L2 report/checker:
  - `./scripts/dev/run_pytest_standalone.sh -q tests/contract/reports/test_molmo_cleanup_report.py`
  - `./scripts/dev/run_pytest_standalone.sh -q tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py`
- L2 profile/routing:
  - focused profile/routing tests for `world-labels`,
    `world-labels-sanitized`, `camera-raw`, and `camera-labels` if touched.
- L4/L6 required local coding-agent demos after deterministic gates:
  - `just task::run household-cleanup codex world-labels seed=7 generated_mess_count=5`
  - `just task::run household-cleanup codex world-labels-sanitized seed=7 generated_mess_count=5`
  - `just task::run household-cleanup codex camera-raw seed=7 generated_mess_count=5`
  - `just task::run household-cleanup codex camera-labels seed=7 generated_mess_count=5 visual_grounding=grounding-dino`

## Stop Condition

Stop when cleanup navigation can start only from a candidate whose state is
`navigation_authorized`, backed by a real source FPV observation and bbox from
the same locality; world-label semantic candidates require a visible
scan/confirm before navigation; RAW-FPV/camera-label candidates cannot resolve
through source-fixture, room, or category-only fallbacks; reports make the
authorization chain reviewable; focused deterministic tests pass; and all
required local Codex cleanup demos, including the Grounding DINO
camera-labels lane, have run and either pass or have an artifact-backed fix
landed. Missing local credentials, simulator/GPU, Docker, or Grounding DINO
service access is a blocker, not a successful completion condition.

## Execution Log

- 2026-06-05: Created after manual review of Codex world-labels and RAW-FPV
  reports showed action chains that were not reviewable from the preceding FPV
  timeline frame. The accepted seam is a unified FPV visual-evidence gate across
  candidate producers.
- 2026-06-05: Implemented `visual_grounding_evidence_v1`, gated
  `navigate_to_visual_candidate`, `navigate_to_object`, and `pick` on
  reviewable agent-facing FPV bbox evidence, updated RAW-FPV guidance to
  bbox-first, and surfaced reviewability/actionability in Agent View/runtime map
  and report tables. Verified with:
  `ruff check roboclaws/household/realworld_contract.py roboclaws/household/realworld_mcp_server.py roboclaws/household/report.py roboclaws/household/raw_fpv_guidance.py tests/contract/molmo_cleanup/test_molmo_realworld_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmo_realworld_contract.py -q`;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py -q`.
- 2026-06-06: Reopened after manual review of local Codex world-labels and
  RAW-FPV reports showed the previous gate was still a false green. World-label
  candidates were authorized by synthetic bbox evidence, and RAW-FPV candidate
  resolution could broaden through source-fixture/room fallback. The reopened
  scope adds an explicit visual scan/confirm state transition and removes
  action-authorizing fallback resolution.
- 2026-06-06: Added the `$intuitive-preflight` execution contract to this gate
  so implementation can start from one canonical plan file after approval.
- 2026-06-06: Tightened the preflight verification contract: Codex cleanup
  demos are required evidence, not optional smoke. Added the Grounding DINO
  camera-labels Codex lane and required artifact-backed diagnosis plus fixes
  for any suspicious or failing demo output.
- 2026-06-06: Implemented the deterministic FPV scan/confirm gate: world-label
  observations now start as `visual_scan_required` semantic candidates without
  synthetic bbox authorization, `adjust_camera -> observe` promotes same-source
  candidates to `navigation_authorized`, RAW-FPV/camera-label resolution no
  longer falls back through source-fixture/room/category broadening, and reports
  show locality, candidate state, and authorization. Focused contract, MCP,
  report, and checker suites pass together:
  `./scripts/dev/run_pytest_standalone.sh -q tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py tests/contract/molmo_cleanup/test_molmo_realworld_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/contract/reports/test_molmo_cleanup_report.py`;
  `ruff check ...`;
  `ruff format --check ...`.
- 2026-06-06: Required local Codex evidence with `ROBOCLAWS_CODEX_PROVIDER=codex-env`:
  `world-labels` passed at
  `output/household/household-cleanup/codex-report/0606_1128/seed-7`
  (`completion_status=success`, `mess_restoration_rate=0.8`,
  `sweep_coverage_rate=1.0`, `disturbance_count=0`), with 5/5
  `navigate_to_object` actions backed by `navigation_authorized`,
  `reviewable`, `same_waypoint_source_observation` source-FPV bbox evidence.
  `world-labels-sanitized` passed at
  `output/household/household-cleanup/codex-world-labels-sanitized/0606_1142/seed-7`
  (`completion_status=success`, `mess_restoration_rate=0.8`,
  `sweep_coverage_rate=1.0`, `disturbance_count=0`), with 5/5 navigation
  actions backed by the same source-FPV authorization chain.
- 2026-06-06: `camera-labels` with Grounding DINO passed the checker at
  `output/household/household-cleanup/codex-camera-labels/0606_1227/seed-7`
  with `completion_status=partial_success`, `mess_restoration_rate=0.2`,
  `sweep_coverage_rate=1.0`, and `disturbance_count=0`. Grounding DINO produced
  one navigation-authorized candidate; the single `navigate_to_object` action
  carried `source_observation_id=raw_fpv_013`,
  `candidate_state=navigation_authorized`, `reviewability_status=reviewable`,
  `locality_status=same_waypoint_source_observation`,
  `producer_id=grounding-dino`, and normalized source-FPV bbox evidence.
- 2026-06-06: `camera-raw` exposed the remaining live-agent limitation at
  `output/household/household-cleanup/codex-camera-raw/0606_1156/seed-7`.
  The run was stopped after 29 minutes with 14/14 waypoints observed, 52 strict
  `navigate_to_visual_candidate` attempts, 2 grounded cleanup chains, and 5
  blocked `done` attempts. Successful chains were authorized by
  source-observation-local FPV evidence; unresolved visible-object guesses
  stayed `semantic_candidate` with `source_observation_locality_unresolved`
  instead of resolving through room/source-fixture/category fallback. Diagnosis:
  stricter RAW-FPV grounding is working, but the current live agent cannot find
  enough same-source reviewable candidates without a stronger camera-producer or
  raw-FPV strategy. Proposed follow-up: tune the RAW-FPV live skill/prompt or
  add a non-privileged visual producer assist, then rerun the same
  `camera-raw` gate without weakening source-locality authorization.
