---
phase: 10
plan: 01
slug: semantic-cleanup-substeps
type: execute
wave: 1
depends_on: [09]
files_modified:
  - examples/molmospaces_cleanup_demo.py
  - roboclaws/molmo_cleanup/backend.py
  - roboclaws/molmo_cleanup/mcp_contract.py
  - roboclaws/molmo_cleanup/subprocess_backend.py
  - roboclaws/molmo_cleanup/report.py
  - scripts/molmospaces_subprocess_worker.py
  - scripts/check_molmospaces_cleanup_result.py
  - just/harness.just
  - tests/test_molmo_cleanup_demo.py
  - tests/test_molmo_cleanup_report.py
  - docs/retrospectives/plans/molmospaces-manipulation-spike.md
  - docs/retrospectives/plans/molmospaces-robot-visual-demo.md
  - docs/retrospectives/plans/molmospaces-visual-verification-report.md
  - .planning/STATE.md
  - .planning/milestones/v1.98-phases/10-molmospaces-semantic-substeps/10-VERIFICATION.md
  - .planning/milestones/v1.98-phases/10-molmospaces-semantic-substeps/10-01-SUMMARY.md
autonomous: true
requirements_addressed: [MOLMO-SEM-LOOP-01, MOLMO-SEM-FRIDGE-01, MOLMO-VIS-BOOTSTRAP-01]
---

<objective>
Replace the coarse MolmoSpaces cleanup loop with an explicit public semantic
substep loop and make the robot visual report distinguish non-focused bootstrap
views from target verification views.
</objective>

<tasks>

<task type="auto">
  <name>Task 1: Public semantic substep tools</name>
  <action>
    Add public tool-contract methods for `navigate_to_object`,
    `navigate_to_receptacle`, `open_receptacle`, `place_inside`, and
    `object_done`, preserving existing `goto` / `place` compatibility where
    useful. The real subprocess backend must dispatch these to the isolated
    Python 3.11 worker.
  </action>
  <verify>
    <automated>Focused demo tests assert the generated trace and run_result contain the semantic substep sequence.</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 2: Real scene state mutation</name>
  <action>
    Implement real MuJoCo state changes for object navigation, held-object
    pickup pose, articulated fridge opening, and fridge `place_inside`
    containment. Record containment/readback in public state and final run
    result.
  </action>
  <verify>
    <automated>`scripts/check_molmospaces_cleanup_result.py --require-semantic-substeps` asserts fridge open/place-inside/readback evidence.</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 3: Visual timeline semantics</name>
  <action>
    Record robot views for semantic substeps and hide or relabel verification
    panels for non-focused bootstrap rows so `before` / `observe` /
    `scene_objects` no longer look like broken target verification.
  </action>
  <verify>
    <automated>Report unit tests cover non-focused verification suppression and semantic evidence text.</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 4: Gates and documentation</name>
  <action>
    Update the robot visual harness checker to require the semantic substep
    loop, run focused tests, run the real `just verify::molmo-robot-visual`
    gate, and write verification/summary artifacts.
  </action>
  <verify>
    <automated>just verify::molmo-robot-visual</automated>
  </verify>
</task>

</tasks>

<success_criteria>
- Each cleanup target records `navigate_to_object -> pick ->
  navigate_to_receptacle -> place/place_inside -> object_done` in
  `run_result.json`.
- Fridge/apple records `open_receptacle` before `place_inside`.
- Final apple readback records `contained_in=<fridge id>` and
  `location_relation=inside`; the demo no longer relies on the apple being
  visible outside the refrigerator.
- Non-focused bootstrap robot timeline rows do not show a misleading
  Verification panel.
- The planner remains `public_heuristic` with
  `planner_uses_private_manifest=false`.
- `just verify::molmo-robot-visual` passes against the real MolmoSpaces
  subprocess backend.
</success_criteria>
