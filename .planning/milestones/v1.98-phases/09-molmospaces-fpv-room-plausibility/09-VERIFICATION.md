# Phase 09 Verification - MolmoSpaces FPV Room Plausibility

## Gate Result

Command:

```bash
just verify::molmo-robot-visual
```

Result: PASS on 2026-05-08.

The gate ran the focused unit suite and the real MolmoSpaces RBY1M visual
harness. The harness produced:

- `output/molmo-robot-visual-harness/before.png`
- `output/molmo-robot-visual-harness/after.png`
- `output/molmo-robot-visual-harness/trace.jsonl`
- `output/molmo-robot-visual-harness/run_result.json`
- `output/molmo-robot-visual-harness/report.html`

## Real-Run Evidence

From `output/molmo-robot-visual-harness/run_result.json`:

- `backend=molmospaces_subprocess`
- `planner=public_heuristic`
- `planner_uses_private_manifest=false`
- `primitive_provenance=api_semantic`
- `cleanup_status=success`
- `score.restored_count=5`, `score.total_targets=5`
- `task_prompt=帮我整理这个房间`
- `molmospaces_runtime.runtime.python_version=3.11.14`
- `molmospaces_runtime.runtime.mujoco_version=3.4.0`
- `robot.robot_name=rby1m`
- `robot.robot_control_provenance=semantic_robot_base_and_head_qpos`
- `robot.robot_view_provenance.fpv=rby1m_head_camera_target_framed`
- `view_variant=molmospaces-rby1m-fpv-map-chase-verify`

## Focused-Step Evidence

All focused `goto` and `place` robot-view steps record:

- `theta_source=target_facing_base_yaw`
- `head_pitch_source=target_framing_head_pitch`
- `same_room_as_target=true`
- positive FPV receptacle pixels
- verification visibility metadata from public MuJoCo state

Representative final run values:

| Step | Target | Room | FPV target px | FPV object px | Verify target px | Verify object px |
|------|--------|------|---------------|---------------|------------------|------------------|
| `0003_goto_1` | Fridge | `room_6 -> room_6` | 97176 | 0 | 1413 | 0 |
| `0004_place_1` | Apple/Fridge | `room_6 -> room_6` | 96566 | 4014 | 25304 | 365 |
| `0005_goto_2` | ShelvingUnit | `room_2 -> room_2` | 55961 | 0 | 2863 | 0 |
| `0006_place_2` | Book/ShelvingUnit | `room_2 -> room_2` | 52848 | 4842 | 12459 | 1319 |
| `0007_goto_3` | Sink | `room_5 -> room_5` | 55861 | 0 | 6128 | 0 |
| `0008_place_3` | Bowl/Sink | `room_5 -> room_5` | 54269 | 1592 | 27300 | 949 |
| `0009_goto_4` | Bed | `room_7 -> room_7` | 125446 | 0 | 29004 | 0 |
| `0010_place_4` | Pillow/Bed | `room_7 -> room_7` | 122743 | 7916 | 89940 | 5209 |
| `0011_goto_5` | TVStand | `room_3 -> room_3` | 87576 | 0 | 6031 | 0 |
| `0012_place_5` | RemoteControl/TVStand | `room_3 -> room_3` | 87576 | 0 | 29340 | 0 |

## Visual Inspection

Inspected generated frames from the final harness:

- `robot_views/0004_place_1.fpv.png` shows the apple next to the refrigerator.
- `robot_views/0005_goto_2.fpv.png` shows the shelving unit in FPV.
- `robot_views/0007_goto_3.fpv.png` shows the sink in FPV.
- `robot_views/0007_goto_3.map.png` shows the sink target and robot pose in the same room outline.

## Scope Boundary

Primitive provenance remains `api_semantic` because this phase mutates real
MolmoSpaces/MuJoCo state through semantic tool commands. It does not claim
planner-backed RBY1M/Franka pick/place. Reserve `primitive_provenance=real` for
the future phase that proves planner-backed robot manipulation.
