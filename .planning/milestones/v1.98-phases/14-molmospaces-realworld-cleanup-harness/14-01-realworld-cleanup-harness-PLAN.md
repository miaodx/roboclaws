---
phase: 14
plan: 01
slug: realworld-cleanup-harness
type: execute
wave: 1
depends_on: [13]
files_modified:
  - roboclaws/molmo_cleanup/realworld_contract.py
  - roboclaws/molmo_cleanup/report.py
  - roboclaws/molmo_cleanup/__init__.py
  - examples/molmospaces_realworld_cleanup.py
  - scripts/check_molmo_realworld_cleanup_result.py
  - just/harness.just
  - just/verify.just
  - tests/test_molmo_realworld_contract.py
  - tests/test_molmospaces_realworld_cleanup.py
  - tests/test_check_molmo_realworld_cleanup_result.py
  - tests/test_verify_just_recipes.py
  - docs/retrospectives/plans/molmospaces-realworld-cleanup-harness.md
  - .planning/STATE.md
  - .planning/milestones/v1.98-phases/14-molmospaces-realworld-cleanup-harness/14-VERIFICATION.md
  - .planning/milestones/v1.98-phases/14-molmospaces-realworld-cleanup-harness/14-01-SUMMARY.md
autonomous: true
requirements_addressed: [ADR-0003]
---

<objective>
Implement ADR-0003's real-world-style MolmoSpaces cleanup harness: the Cleanup
Agent receives only public metric-map, fixture-hint, and robot-local visible
detection inputs, while Generated Mess Set, acceptable destination sets, and
target counts remain private deterministic scorer data shown only after the run.
</objective>

<tasks>

<task type="auto">
  <name>Task 1: ADR-0003 public contract</name>
  <action>
    Add `RealWorldCleanupContract` as a wrapper over `MolmoCleanupToolContract`
    with public tools for `metric_map`, `fixture_hints`, waypoint navigation,
    local `observe`, `inspect_visible_object`, semantic pick/place actions, and
    `done`. Use stable `observed_*` handles for movable objects instead of
    global scene object ids.
  </action>
  <verify>
    <automated>Contract tests assert public responses have no Generated Mess
    Set, acceptable destination sets, target-count fields, `is_misplaced`, or
    global movable-object inventory.</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 2: Deterministic sweep harness</name>
  <action>
    Add `examples/molmospaces_realworld_cleanup.py`, which visits public
    inspection waypoints, accumulates visible detections, applies public
    category/fixture heuristics, and writes `agent_view.json`,
    `private_evaluation.json`, `trace.jsonl`, `run_result.json`, snapshots, and
    `report.html`.
  </action>
  <verify>
    <automated>Synthetic smoke tests assert success artifacts, public/private
    split, no `scene_objects` trace calls, and report separation.</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 3: Checker and recipes</name>
  <action>
    Add `scripts/check_molmo_realworld_cleanup_result.py`,
    `just harness::molmo-realworld-cleanup`, and
    `just verify::molmo-realworld-cleanup`.
  </action>
  <verify>
    <automated>Checker tests validate accepting clean artifacts and rejecting
    Agent View private leaks; recipe tests detect both new just recipes.</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 4: Evidence and hybrid artifacts</name>
  <action>
    Run focused tests, lint/format, the real MolmoSpaces three-seed harness,
    and record plan/source/verification artifacts matching the Phase 12 ADR-0004
    implementation pattern.
  </action>
  <verify>
    <automated>Verification maps ADR-0003 requirements and plan acceptance
    criteria to concrete files, commands, and output artifacts.</automated>
  </verify>
</task>

</tasks>

<success_criteria>
- `run_result.json` records `backend`, `task_prompt`, `fixture_hint_mode`,
  `generated_mess_count`, `policy`, `policy_uses_private_truth=false`,
  `mess_restoration_rate`, `sweep_coverage_rate`, `disturbance_count`, and
  primitive provenance.
- Agent View contains no Generated Mess Set, hidden target count, acceptable
  destination sets, `is_misplaced`, or global movable-object inventory.
- Deterministic sweep baseline passes the default v1 success threshold across
  the initial three-seed real MolmoSpaces gate.
- `report.html` clearly separates Agent View from Private Evaluation.
- Existing current-contract bridge/report behavior remains covered by focused
  regression tests.
</success_criteria>
