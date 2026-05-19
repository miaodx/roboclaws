---
phase: 11
plan: 01
slug: held-object-carry-visuals
type: execute
wave: 1
depends_on: [10]
files_modified:
  - scripts/molmospaces_subprocess_worker.py
  - scripts/check_molmospaces_cleanup_result.py
  - tests/test_molmo_cleanup_subprocess_backend.py
  - docs/retrospectives/plans/molmospaces-manipulation-spike.md
  - .planning/STATE.md
  - .planning/milestones/v1.98-phases/11-molmospaces-held-object-carry-visuals/11-VERIFICATION.md
  - .planning/milestones/v1.98-phases/11-molmospaces-held-object-carry-visuals/11-01-SUMMARY.md
autonomous: true
requirements_addressed: [MOLMO-VIS-CARRY-01]
---

<objective>
Make held objects visually travel with RBY1M during MolmoSpaces semantic
cleanup navigation so `navigate_to_receptacle` rows no longer show the robot
moving while the picked object is left behind.
</objective>

<tasks>

<task type="auto">
  <name>Task 1: Held-object qpos sync</name>
  <action>
    Add a small worker helper that, when `held_object_id` is set, moves the
    held object's MuJoCo free-joint qpos to the robot-relative held pose after
    robot base/head pose changes.
  </action>
  <verify>
    <automated>Focused worker test proves the helper moves a free-joint object
    to the expected robot-relative held pose.</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 2: Navigation/opening carry semantics</name>
  <action>
    Call the held-object sync helper from `navigate_to_receptacle` and
    `open_receptacle` after the robot pose changes, and record the held-object
    qpos mutation in tool responses.
  </action>
  <verify>
    <automated>Real visual harness `run_result.json` shows held objects near
    the current robot pose during `navigate_to_receptacle` rows.</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 3: Visual gate</name>
  <action>
    Tighten `scripts/check_molmospaces_cleanup_result.py` so focused
    `navigate_to_receptacle` rows with `object_location_relation=held` require
    positive FPV object pixels in addition to receptacle pixels.
  </action>
  <verify>
    <automated>Run the checker through `just verify::molmo-robot-visual` against
    the real MolmoSpaces subprocess backend.</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 4: Verification record</name>
  <action>
    Run focused tests and the real RBY1M visual gate, then update the
    MolmoSpaces plan and GSD verification/summary artifacts with dated
    evidence.
  </action>
  <verify>
    <automated>`just verify::molmo-robot-visual` passes and the verification
    artifact records the held-object pixel evidence.</automated>
  </verify>
</task>

</tasks>

<success_criteria>
- After `pick`, the held object's real MuJoCo free-joint qpos is updated when
  RBY1M navigates to a receptacle.
- If RBY1M changes pose while opening the fridge, the held apple follows that
  access pose before `place_inside`.
- `run_result.json` focused `navigate_to_receptacle` rows record
  `object_location_relation=held`, object positions near the current robot pose,
  and positive `fpv_visibility.object_pixels`.
- The real visual checker passes against `backend=molmospaces_subprocess`,
  `robot_name=rby1m`, `planner=public_heuristic`, and
  `planner_uses_private_manifest=false`.
- Primitive provenance remains `api_semantic`; this phase does not claim
  planner-backed robot manipulation.
</success_criteria>
