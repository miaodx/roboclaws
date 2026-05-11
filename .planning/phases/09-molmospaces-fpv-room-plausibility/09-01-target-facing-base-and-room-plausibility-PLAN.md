---
phase: 09
plan: 01
slug: target-facing-base-and-room-plausibility
type: execute
wave: 1
depends_on: [08]
files_modified:
  - scripts/molmospaces_subprocess_worker.py
  - roboclaws/molmo_cleanup/report.py
  - scripts/check_molmospaces_cleanup_result.py
  - tests/test_molmo_cleanup_report.py
  - .planning/phases/09-molmospaces-fpv-room-plausibility/09-VERIFICATION.md
  - .planning/phases/09-molmospaces-fpv-room-plausibility/09-01-SUMMARY.md
autonomous: true
requirements_addressed: [MOLMO-VIS-ORIENT-01, MOLMO-VIS-ROOM-01, MOLMO-VIS-VERIFY-01]
---

<objective>
Make the MolmoSpaces RBY1M visual cleanup report more physically plausible by
orienting the robot base toward the active target, selecting same-room target
stand-off poses when possible, and making refrigerator/apple verification
visually inspectable.
</objective>

<tasks>

<task type="auto">
  <name>Task 1: Target-facing base yaw</name>
  <action>
    Change semantic `goto` pose generation so `robot_0/base_theta` faces the
    target receptacle from the chosen base position. Record `theta_source` in
    the robot pose. Keep base yaw as the horizontal orientation source, then set
    the RBY1M head pitch only to frame close low targets in the real
    `robot_0/head_camera` FPV render; record `head_pitch_source` separately so
    the report does not conflate base navigation direction with camera framing.
  </action>
  <verify>
    <automated>scripts/check_molmospaces_cleanup_result.py --require-robot-views must assert target-facing base metadata and target-framing head pitch metadata on focused steps.</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 2: Same-room stand-off selection</name>
  <action>
    Use the room outlines already derived from MuJoCo room geoms to choose a
    stand-off candidate inside the target receptacle's room when possible.
    Record `robot_room_id`, `target_room_id`, and `same_room_as_target`.
  </action>
  <verify>
    <automated>Focused `goto` / `place` robot-view steps must record `same_room_as_target=true`.</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 3: Verification and FPV target boxes</name>
  <action>
    Render segmentation passes for the verification camera and the RBY1M head
    camera. Draw object/receptacle boxes in the verification view when their
    MuJoCo geoms are visible, record FPV visibility pixels, and use a close
    object-focused verification camera for post-place frames so the apple on
    the refrigerator is inspectable.
  </action>
  <verify>
    <automated>Focused steps must report positive FPV target pixels; focused `place` robot-view steps must report visible object pixels in verification metadata for the called-out apple/book/bowl/pillow cases.</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 4: Report and real gate</name>
  <action>
    Surface room plausibility and visibility evidence in `report.html`, update
    focused tests, and rerun the real `just verify::molmo-robot-visual` gate.
  </action>
  <verify>
    <automated>just verify::molmo-robot-visual</automated>
  </verify>
</task>

</tasks>

<success_criteria>
- FPV is generated from the real RBY1M head camera after the robot base pose
  records `theta_source=target_facing_base_yaw` for focused manipulation steps.
- The report records `head_pitch_source=target_framing_head_pitch` separately
  from base yaw and the checker requires positive FPV target pixels.
- Focused manipulation steps record `same_room_as_target=true`.
- Verification views include segmentation-derived target boxes when visible.
- Place steps record positive object visibility pixels.
- Refrigerator/apple verification is visually inspectable in the regenerated
  report artifact.
- `just verify::molmo-robot-visual` passes against the real MolmoSpaces
  subprocess backend.
</success_criteria>
